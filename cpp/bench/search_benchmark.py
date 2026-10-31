import argparse
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import platform
import statistics
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from trickfish.position import Position


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_output_path(output, inputs):
    if output is None:
        return
    target = pathlib.Path(output).resolve()
    for path in inputs:
        if path is None:
            continue
        source = pathlib.Path(path).resolve(strict=True)
        if target == source or (target.exists() and target.samefile(source)):
            raise ValueError(f"output must differ from input file: {source}")


def validate_objective(case, result=None):
    objective = case.get("expect")
    if objective is None:
        return
    if not isinstance(objective, dict) or not objective or set(objective) - {"bestmoves", "mate_in_one", "score"}:
        raise ValueError(f"invalid tactical objective: {case['id']}")
    if "score" in objective and type(objective["score"]) is not int:
        raise ValueError("score objective must be an integer")
    position = Position.from_fen(case["fen"])
    legal = {move.to_uci(): move for move in position.legal_moves()}
    accepted = objective.get("bestmoves")
    if accepted is not None:
        if not isinstance(accepted, list) or not accepted or any(not isinstance(m, str) or m not in legal for m in accepted):
            raise ValueError(f"illegal expected move: {case['id']}")
        if len(set(accepted)) != len(accepted):
            raise ValueError(f"duplicate expected move: {case['id']}")
    if "mate_in_one" in objective:
        if objective["mate_in_one"] is not True:
            raise ValueError("mate_in_one objective must be true")
        mates = {text for text, move in legal.items() if position.make_move(move).game_status() == "checkmate"}
        if not mates or (accepted is not None and not set(accepted) <= mates):
            raise ValueError(f"reference mate objective is unsatisfied: {case['id']}")
    if result is not None:
        if "score" in objective and result["score"] != objective["score"]:
            raise ValueError(f"score objective failed: {case['id']}")
        selected = result["bestmove"]
        if accepted is not None and selected not in accepted:
            raise ValueError(f"tactical move objective failed: {case['id']}: {selected}")
        if objective.get("mate_in_one") and (selected not in mates or result["score"] != 99999):
            raise ValueError(f"mate-in-one objective failed: {case['id']}")


def load_suite(path):
    suite = json.loads(path.read_text(encoding="utf-8"))
    if suite.get("version") != 1 or not suite.get("positions"):
        raise ValueError("suite requires version 1 and nonempty positions")
    names = set()
    for case in suite["positions"]:
        name = case["id"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("position IDs must be nonempty and unique")
        names.add(name)
        position = Position.from_fen(case["fen"])
        opposite = "b" if position.side_to_move == "w" else "w"
        if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
            raise ValueError(f"nonmoving king is checked: {name}")
        validate_objective(case)
    return suite


def parse_result(output, fen, requested_depth, pv_extra=0):
    fields = {}
    for line in output.splitlines():
        parts = line.split()
        if not parts or parts[0] in fields:
            raise ValueError("empty or duplicate search output field")
        fields[parts[0]] = parts[1:]
    required = {"bestmove", "score", "pv", "depth", "stopped", "nodes"}
    cache_fields = {"pawn_cache_hits", "pawn_cache_misses"}
    if set(fields) not in (required, required | cache_fields):
        raise ValueError("unexpected search output fields")
    for key in ("bestmove", "score", "depth", "stopped", "nodes"):
        if len(fields[key]) != 1:
            raise ValueError(f"expected one value for {key}")
    result = {key: int(fields[key][0]) for key in ("score", "depth", "nodes")}
    result.update(bestmove=fields["bestmove"][0], pv=fields["pv"])
    if cache_fields <= set(fields):
        for key in cache_fields:
            if len(fields[key]) != 1 or not fields[key][0].isascii() or not fields[key][0].isdecimal():
                raise ValueError("invalid pawn cache work counter")
            result[key] = int(fields[key][0])
    if fields["stopped"] != ["false"] or result["nodes"] <= 0:
        raise ValueError("benchmark search stopped or visited no nodes")
    position = Position.from_fen(fen)
    legal = position.legal_moves()
    if result["bestmove"] == "0000":
        if result["pv"] or result["depth"] != 1 or (legal and position.halfmove_clock < 150):
            raise ValueError("unexpected empty root move")
    elif result["depth"] != requested_depth:
        raise ValueError("search did not complete requested depth")
    if len(result["pv"]) > min(64, result["depth"] + pv_extra):
        raise ValueError("PV exceeds completed depth")
    if result["bestmove"] != "0000" and (
        not result["pv"] or result["pv"][0] != result["bestmove"]
    ):
        raise ValueError("best move and PV disagree")
    for text in result["pv"]:
        moves = {move.to_uci(): move for move in position.legal_moves()}
        if text not in moves:
            raise ValueError(f"illegal PV move {text}")
        position = position.make_move(moves[text])
    return result


MODES = {"default": "--search", "alphabeta": "--search-ab", "exchange": "--search-see", "null": "--search-null", "lmr": "--search-lmr", "futility": "--search-futility", "razor": "--search-razor", "check": "--search-check", "correction": "--search-correction", "scale": "--search-scale", "ordering": "--search-order-reference", "mate_distance": "--search-mdp", "pawn_cache": "--search-pawn-cache", "reference_binary": "--search"}


def run_sample(binary, case, depth, timeout, mode):
    started = time.perf_counter_ns()
    process = subprocess.run([str(binary), MODES[mode], str(depth), case["fen"]],
        capture_output=True, text=True, timeout=timeout, check=True)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    result = parse_result(process.stdout, case["fen"], depth, 1 if mode == "check" else 0)
    if mode == "pawn_cache" and not {"pawn_cache_hits", "pawn_cache_misses"} <= set(result):
        raise ValueError("pawn cache diagnostic omitted work counters")
    validate_objective(case, result)
    return result, elapsed


def run_modes(binary, case, depth, repeats, timeout, modes, reference_binary=None, warmups=0):
    if type(warmups) is not int or not 0 <= warmups <= 20:
        raise ValueError("warmups must be an integer from 0 to 20")
    if repeats < 2 or not modes or len(set(modes)) != len(modes) or any(mode not in MODES for mode in modes):
        raise ValueError("benchmark requires at least two repeats and unique supported modes")
    if "reference_binary" in modes and reference_binary is None:
        raise ValueError("reference binary mode requires a binary path")
    expected = {}
    samples = {mode: [] for mode in modes}
    execution_order = []
    warmup_order = []
    for repeat in range(-warmups, repeats):
        index = repeat + warmups if repeat < 0 else repeat
        order = list(modes if index % 2 == 0 else reversed(modes))
        (warmup_order if repeat < 0 else execution_order).append(order)
        for mode in order:
            selected_binary = reference_binary if mode == "reference_binary" else binary
            result, elapsed = run_sample(selected_binary, case, depth, timeout, mode)
            if mode in expected and result != expected[mode]:
                raise ValueError(f"nondeterministic search output: {case['id']} ({mode})")
            expected[mode] = result
            if repeat >= 0:
                samples[mode].append(elapsed)
    results = {mode: dict(case, **expected[mode], process_wall_ms=samples[mode],
        warmup_execution_order=warmup_order,
        median_process_wall_ms=statistics.median(samples[mode]),
        min_process_wall_ms=min(samples[mode]), max_process_wall_ms=max(samples[mode])) for mode in modes}
    return results, execution_order


def run_case(binary, case, depth, repeats, timeout, use_pvs=True, use_exchange=False, use_null=False):
    mode = "null" if use_null else "exchange" if use_exchange else "default" if use_pvs else "alphabeta"
    results, _ = run_modes(binary, case, depth, repeats, timeout, [mode])
    return results[mode]


def paired_wall_ratio(candidate, baseline):
    if len(candidate["process_wall_ms"]) != len(baseline["process_wall_ms"]):
        raise ValueError("paired timing sample counts differ")
    ratios = [value / base for value, base in zip(candidate["process_wall_ms"], baseline["process_wall_ms"]) if base > 0]
    return statistics.median(ratios) if len(ratios) == len(baseline["process_wall_ms"]) and ratios else None


def compare_reference(candidate, reference):
    if candidate["score"] != reference["score"] or candidate["depth"] != reference["depth"]:
        raise ValueError(f"PVS/full-window mismatch: {candidate['id']}")
    return {"score_equal": True, "reference": reference,
        "node_delta_per_repeat": candidate["nodes"] - reference["nodes"]}


def revision():
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip())
        return {"head": head, "tracked_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Repeat fixed-depth C++ CLI searches with legal PV checks")
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("--suite", type=pathlib.Path, default=pathlib.Path(__file__).with_name("search_suite.json"))
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--warmups", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--compare-alphabeta", action="store_true")
    parser.add_argument("--compare-exchange", action="store_true")
    parser.add_argument("--compare-null", action="store_true")
    parser.add_argument("--compare-lmr", action="store_true")
    parser.add_argument("--compare-futility", action="store_true")
    parser.add_argument("--compare-razor", action="store_true")
    parser.add_argument("--compare-check", action="store_true")
    parser.add_argument("--compare-correction", action="store_true")
    parser.add_argument("--compare-scale", action="store_true")
    parser.add_argument("--compare-ordering", action="store_true")
    parser.add_argument("--compare-mate-distance", action="store_true")
    parser.add_argument("--compare-pawn-cache", action="store_true")
    parser.add_argument("--reference-binary", type=pathlib.Path)
    parser.add_argument("--reference-trace", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if not 0 <= args.warmups <= 20:
        parser.error("warmups must be 0..20")
    if not 1 <= args.depth <= 64 or args.repeats < 2 or not 0 < args.timeout < float("inf"):
        parser.error("depth must be 1..64, repeats at least 2, timeout finite and positive")
    if args.reference_trace and args.reference_binary is None:
        parser.error("--reference-trace requires --reference-binary")
    binary = args.binary.resolve(strict=True)
    reference_binary = args.reference_binary.resolve(strict=True) if args.reference_binary is not None else None
    suite_path = args.suite.resolve(strict=True)
    try:
        validate_output_path(args.output, [binary, suite_path, reference_binary])
    except ValueError as error:
        parser.error(str(error))
    suite_hash = digest(suite_path)
    suite = load_suite(suite_path)
    binary_hash = digest(binary)
    reference_hash = digest(reference_binary) if reference_binary is not None else None
    modes = ["default"]
    if args.compare_alphabeta: modes.append("alphabeta")
    if args.compare_exchange: modes.append("exchange")
    if args.compare_null: modes.append("null")
    if args.compare_lmr: modes.append("lmr")
    if args.compare_futility: modes.append("futility")
    if args.compare_razor: modes.append("razor")
    if args.compare_check: modes.append("check")
    if args.compare_correction: modes.append("correction")
    if args.compare_scale: modes.append("scale")
    if args.compare_ordering: modes.append("ordering")
    if args.compare_mate_distance: modes.append("mate_distance")
    if args.compare_pawn_cache: modes.append("pawn_cache")
    if reference_binary is not None: modes.append("reference_binary")
    results = []
    for case in suite["positions"]:
        measured, order = run_modes(binary, case, args.depth, args.repeats, args.timeout, modes,
            reference_binary=reference_binary, warmups=args.warmups)
        candidate = measured["default"]
        candidate["execution_order"] = order
        if args.compare_alphabeta:
            reference = measured["alphabeta"]
            candidate["alphabeta_comparison"] = compare_reference(candidate, reference)
            candidate["alphabeta_comparison"]["median_paired_wall_ratio"] = paired_wall_ratio(candidate, reference)
        for mode, label in [("exchange", "ordered"), ("null", "verified"), ("lmr", "selective"), ("futility", "selective"), ("razor", "selective"), ("check", "extended"), ("correction", "adjusted"), ("scale", "scaled"), ("ordering", "reference"), ("mate_distance", "bounded"), ("pawn_cache", "cached")]:
            if mode not in measured: continue
            alternative = measured[mode]
            if alternative["depth"] != candidate["depth"] or (mode not in {"lmr", "futility", "razor", "check", "correction", "scale"} and alternative["score"] != candidate["score"]):
                raise ValueError(f"{mode} score/depth mismatch: {case['id']}")
            if mode in {"ordering", "pawn_cache"} and any(alternative[key] != candidate[key] for key in ("nodes", "bestmove", "pv")):
                raise ValueError(f"{mode} changed search trace: {case['id']}")
            candidate[mode + "_comparison"] = {label: alternative, "score_equal": alternative["score"] == candidate["score"],
                "score_delta": alternative["score"] - candidate["score"],
                "node_delta_per_repeat": alternative["nodes"] - candidate["nodes"],
                "median_paired_wall_ratio": paired_wall_ratio(alternative, candidate)}
        if reference_binary is not None:
            reference = measured["reference_binary"]
            if candidate["score"] != reference["score"] or candidate["depth"] != reference["depth"]:
                raise ValueError(f"binary score/depth mismatch: {case['id']}")
            equal = {key: candidate[key] == reference[key] for key in ("nodes", "bestmove", "pv")}
            if args.reference_trace and not all(equal.values()):
                raise ValueError(f"binary search trace mismatch: {case['id']}")
            candidate["binary_comparison"] = {"reference": reference, "score_equal": True,
                "trace_equal": equal, "node_delta_per_repeat": candidate["nodes"] - reference["nodes"],
                "median_paired_wall_ratio": paired_wall_ratio(candidate, reference)}
        results.append(candidate)
    if (digest(binary) != binary_hash or digest(suite_path) != suite_hash or
        (reference_binary is not None and digest(reference_binary) != reference_hash)):
        raise ValueError("binary or suite changed during benchmark")
    report = {
        "schema_version": 3,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "binary": str(binary), "binary_sha256": binary_hash,
        "reference_binary": {"path": str(reference_binary), "sha256": reference_hash, "mode": "--search",
            "same_bytes_as_candidate": reference_hash == binary_hash} if reference_binary is not None else None,
        "suite": str(suite_path), "suite_sha256": suite_hash,
        "checkout": revision(),
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "python": platform.python_version()},
        "search": {"mode": "diagnostic_iterative", "algorithm": "pvs",
            "aspiration_window": 25, "reference_aspiration_window": 0,
            "killer_moves": True, "reference_killer_moves": False,
            "quiet_history": True, "reference_quiet_history": False,
            "continuation_history": True, "reference_continuation_history": False,
            "exchange_ordering": False, "compare_exchange": args.compare_exchange,
            "verified_null": False, "compare_null": args.compare_null,
            "lmr": False, "compare_lmr": args.compare_lmr,
            "futility": False, "futility_margin": 150, "compare_futility": args.compare_futility,
            "razoring": False, "razor_margin": 200, "compare_razor": args.compare_razor,
            "check_extensions": False, "comparison_check_extension_limit": 1,
            "comparison_check_table": False, "compare_check": args.compare_check,
            "correction_history": False, "comparison_correction_table": False,
            "compare_correction": args.compare_correction,
            "pawn_cache": False, "compare_pawn_cache": args.compare_pawn_cache,
            "comparison_pawn_cache": {"capacity": 4096, "phase_key": True, "lifetime": "one iterative search"},
            "mate_distance_pruning": False, "compare_mate_distance": args.compare_mate_distance,
            "cached_ordering": True, "comparison_cached_ordering": False, "compare_ordering": args.compare_ordering,
            "endgame_scaling": False, "compare_scale": args.compare_scale,
            "comparison_scale": {"enabled": args.compare_scale, "normal": 256, "opposite_bishop_pawn_ending": 128, "wrong_bishop_rook_pawn_corner": 0,
                "rounding": "toward zero", "draw_adjudication": False},
            "compare_alphabeta": args.compare_alphabeta, "requested_depth": args.depth,
            "repeats": args.repeats, "warmups_per_mode_per_fixture": args.warmups,
            "warmup_policy": "fresh processes; validated output; excluded from timing samples",
            "timeout_seconds_per_process": args.timeout,
            "table": "fresh per process", "repetition_history": False,
            "draw_policy": "automatic_only", "timing": "process-inclusive wall time",
            "execution_schedule": "forward/reverse alternation per fixture",
            "mode_order": modes, "reference_trace_required": args.reference_trace,
            "binary_comparison_ratio": "candidate/reference process wall time"},
        "results": results,
        "total_nodes_per_repeat": sum(case["nodes"] for case in results),
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None:
        sys.stdout.write(encoded)
    else:
        args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
