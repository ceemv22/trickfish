import argparse
from datetime import datetime, timezone
import json
import math
import pathlib
import re
import statistics
import sys

from search_benchmark import MODES, digest, parse_result, validate_objective, validate_output_path
from trickfish.position import Position


def positive_number(value):
    if type(value) not in (int, float): raise ValueError("timing must be numeric")
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid: raise ValueError("timing must be finite and positive")
    return value


def derived_value(saved, expected):
    positive_number(saved)
    if not math.isclose(saved, expected, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("stored timing statistic disagrees with raw samples")


def validate_run(run, depth, repeats):
    for field in ("score", "depth", "nodes"):
        if type(run.get(field)) is not int: raise ValueError("search counters must be integers")
    pattern = r"(?:[a-h][1-8]){2}[qrbn]?"
    best = run.get("bestmove")
    pv = run.get("pv")
    if not isinstance(best, str) or (best != "0000" and re.fullmatch(pattern, best) is None):
        raise ValueError("invalid recorded best move")
    if not isinstance(pv, list) or any(not isinstance(move, str) or re.fullmatch(pattern, move) is None for move in pv):
        raise ValueError("invalid recorded PV")
    text = (f"bestmove {best}\nscore {run['score']}\npv {' '.join(pv)}\ndepth {run['depth']}\n"
        f"stopped false\nnodes {run['nodes']}\n")
    parsed = parse_result(text, run["fen"], depth)
    validate_objective(run, parsed)
    samples = run.get("process_wall_ms")
    if not isinstance(samples, list) or len(samples) != repeats: raise ValueError("timing sample count mismatch")
    for sample in samples: positive_number(sample)
    for field, value in (("min_process_wall_ms", min(samples)), ("max_process_wall_ms", max(samples)),
        ("median_process_wall_ms", statistics.median(samples))):
        derived_value(run.get(field), value)
    return samples


def summarize_report(report):
    if type(report.get("schema_version")) is not int or report["schema_version"] != 3:
        raise ValueError("expected schema-3 binary comparison report")
    reference_metadata = report.get("reference_binary")
    if not isinstance(reference_metadata, dict) or reference_metadata.get("mode") != "--search":
        raise ValueError("report has no compatible reference binary")
    for value in (report.get("binary_sha256"), report.get("suite_sha256"), reference_metadata.get("sha256")):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("invalid benchmark provenance hash")
    if any(not isinstance(value, str) or not value for value in (report.get("binary"), report.get("suite"), reference_metadata.get("path"))):
        raise ValueError("invalid benchmark provenance path")
    same_bytes = report["binary_sha256"] == reference_metadata["sha256"]
    if type(reference_metadata.get("same_bytes_as_candidate")) is not bool or reference_metadata["same_bytes_as_candidate"] != same_bytes:
        raise ValueError("binary identity flag disagrees with hashes")
    search = report["search"]
    depth, repeats = search["requested_depth"], search["repeats"]
    if type(depth) is not int or not 1 <= depth <= 64 or type(repeats) is not int or repeats < 2:
        raise ValueError("invalid benchmark depth/repeats")
    strict = search.get("reference_trace_required")
    modes = search.get("mode_order")
    if (type(strict) is not bool or not isinstance(modes, list) or any(not isinstance(mode, str) or mode not in MODES for mode in modes) or
        len(set(modes)) != len(modes) or not {"default", "reference_binary"} <= set(modes)):
        raise ValueError("invalid benchmark mode/trace policy")
    if search.get("timing") != "process-inclusive wall time": raise ValueError("unsupported timing scope")
    order = [list(modes if index % 2 == 0 else reversed(modes)) for index in range(repeats)]
    cases = report.get("results")
    if not isinstance(cases, list) or not cases: raise ValueError("benchmark requires fixtures")
    candidate_totals, reference_totals = [0.0] * repeats, [0.0] * repeats
    fixtures, names = [], set()
    candidate_nodes = reference_nodes = changed = 0
    for case in cases:
        name = case.get("id")
        if not isinstance(name, str) or not name or name in names: raise ValueError("invalid/duplicate fixture ID")
        names.add(name)
        position = Position.from_fen(case["fen"])
        opposite = "b" if position.side_to_move == "w" else "w"
        if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
            raise ValueError("nonmoving king checked in benchmark fixture")
        comparison = case["binary_comparison"]
        reference = comparison["reference"]
        if (reference.get("id") != name or reference.get("fen") != case["fen"] or reference.get("expect") != case.get("expect") or
            case.get("execution_order") != order):
            raise ValueError("fixture identity or execution order mismatch")
        candidate_times = validate_run(case, depth, repeats)
        reference_times = validate_run(reference, depth, repeats)
        if case["score"] != reference["score"] or case["depth"] != reference["depth"] or comparison.get("score_equal") is not True:
            raise ValueError("binary score/depth parity failed")
        trace = {key: case[key] == reference[key] for key in ("nodes", "bestmove", "pv")}
        saved_trace = comparison.get("trace_equal")
        if not isinstance(saved_trace, dict) or set(saved_trace) != set(trace) or any(type(value) is not bool for value in saved_trace.values()) or saved_trace != trace:
            raise ValueError("stored trace flags disagree with search output")
        if strict and not all(trace.values()): raise ValueError("required trace parity failed")
        delta = case["nodes"] - reference["nodes"]
        if type(comparison.get("node_delta_per_repeat")) is not int or comparison["node_delta_per_repeat"] != delta:
            raise ValueError("stored node delta disagrees with search output")
        ratios = [candidate / baseline for candidate, baseline in zip(candidate_times, reference_times)]
        for ratio in ratios: positive_number(ratio)
        derived_value(comparison.get("median_paired_wall_ratio"), statistics.median(ratios))
        for index in range(repeats):
            candidate_totals[index] += candidate_times[index]
            reference_totals[index] += reference_times[index]
        candidate_nodes += case["nodes"]
        reference_nodes += reference["nodes"]
        changed += not all(trace.values())
        fixtures.append({"id": name, "fen": case["fen"], "score": case["score"], "trace_equal": trace,
            "candidate_nodes": case["nodes"], "reference_nodes": reference["nodes"], "paired_wall_ratios": ratios,
            "median_paired_wall_ratio": statistics.median(ratios)})
    if type(report.get("total_nodes_per_repeat")) is not int or report["total_nodes_per_repeat"] != candidate_nodes:
        raise ValueError("candidate node total disagrees with fixtures")
    suite_ratios = [positive_number(candidate) / positive_number(baseline) for candidate, baseline in zip(candidate_totals, reference_totals)]
    for ratio in suite_ratios: positive_number(ratio)
    return {"summary_schema_version": 1, "comparison_kind": "same-binary-control" if same_bytes else "distinct-binaries",
        "candidate": {"path": report["binary"], "sha256": report["binary_sha256"]}, "reference": reference_metadata,
        "suite": {"path": report["suite"], "sha256": report["suite_sha256"]}, "environment": report.get("environment"),
        "reported_build_provenance": report.get("build_provenance"), "depth": depth, "repeats": repeats,
        "method": {"ratio": "candidate/reference process-inclusive wall time", "inference": "none",
            "suite_aggregation": "sum corresponding repeat-index times across fixtures before taking paired ratios",
            "trace_required": strict, "same_binary_control_is_optimization_evidence": False},
        "totals": {"fixtures": len(fixtures), "trace_changed_fixtures": changed,
            "candidate_nodes_per_repeat": candidate_nodes, "reference_nodes_per_repeat": reference_nodes,
            "candidate_suite_wall_ms": candidate_totals, "reference_suite_wall_ms": reference_totals,
            "paired_suite_wall_ratios": suite_ratios, "median_suite_wall_ratio": statistics.median(suite_ratios)},
        "fixtures": fixtures}


def main():
    parser = argparse.ArgumentParser(description="Validate paired binary benchmark samples and summarize observed timings")
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    source = args.report.resolve(strict=True)
    try:
        validate_output_path(args.output, [source])
    except ValueError as error:
        parser.error(str(error))
    source_hash = digest(source)
    result = summarize_report(json.loads(source.read_text(encoding="utf-8")))
    if digest(source) != source_hash: raise ValueError("benchmark report changed during summary")
    result.update(created_utc=datetime.now(timezone.utc).isoformat(), source_report={"path": str(source), "sha256": source_hash})
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
