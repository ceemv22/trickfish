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
    return suite


def parse_result(output, fen, requested_depth):
    fields = {}
    for line in output.splitlines():
        parts = line.split()
        if not parts or parts[0] in fields:
            raise ValueError("empty or duplicate search output field")
        fields[parts[0]] = parts[1:]
    if set(fields) != {"bestmove", "score", "pv", "depth", "stopped", "nodes"}:
        raise ValueError("unexpected search output fields")
    for key in ("bestmove", "score", "depth", "stopped", "nodes"):
        if len(fields[key]) != 1:
            raise ValueError(f"expected one value for {key}")
    result = {key: int(fields[key][0]) for key in ("score", "depth", "nodes")}
    result.update(bestmove=fields["bestmove"][0], pv=fields["pv"])
    if fields["stopped"] != ["false"] or result["nodes"] <= 0:
        raise ValueError("benchmark search stopped or visited no nodes")
    position = Position.from_fen(fen)
    legal = position.legal_moves()
    if result["bestmove"] == "0000":
        if result["pv"] or result["depth"] != 1 or (legal and position.halfmove_clock < 150):
            raise ValueError("unexpected empty root move")
    elif result["depth"] != requested_depth:
        raise ValueError("search did not complete requested depth")
    if len(result["pv"]) > result["depth"]:
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


def run_case(binary, case, depth, repeats, timeout, use_pvs=True):
    samples = []
    expected = None
    for _ in range(repeats):
        started = time.perf_counter_ns()
        process = subprocess.run(
            [str(binary), "--search" if use_pvs else "--search-ab", str(depth), case["fen"]],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        result = parse_result(process.stdout, case["fen"], depth)
        if expected is not None and result != expected:
            raise ValueError(f"nondeterministic search output: {case['id']}")
        expected = result
        samples.append(elapsed)
    return dict(case, **expected, process_wall_ms=samples,
        median_process_wall_ms=statistics.median(samples))


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
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--compare-alphabeta", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if not 1 <= args.depth <= 64 or args.repeats < 2 or not 0 < args.timeout < float("inf"):
        parser.error("depth must be 1..64, repeats at least 2, timeout finite and positive")
    binary = args.binary.resolve(strict=True)
    suite_path = args.suite.resolve(strict=True)
    suite_hash = digest(suite_path)
    suite = load_suite(suite_path)
    binary_hash = digest(binary)
    results = [run_case(binary, case, args.depth, args.repeats, args.timeout) for case in suite["positions"]]
    if args.compare_alphabeta:
        for case, candidate in zip(suite["positions"], results):
            reference = run_case(binary, case, args.depth, args.repeats, args.timeout, False)
            candidate["alphabeta_comparison"] = compare_reference(candidate, reference)
    if digest(binary) != binary_hash or digest(suite_path) != suite_hash:
        raise ValueError("binary or suite changed during benchmark")
    report = {
        "schema_version": 2,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "binary": str(binary), "binary_sha256": binary_hash,
        "suite": str(suite_path), "suite_sha256": suite_hash,
        "checkout": revision(),
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "python": platform.python_version()},
        "search": {"mode": "diagnostic_iterative", "algorithm": "pvs",
            "compare_alphabeta": args.compare_alphabeta, "requested_depth": args.depth,
            "repeats": args.repeats, "timeout_seconds_per_process": args.timeout,
            "table": "fresh per process", "repetition_history": False,
            "draw_policy": "automatic_only", "timing": "process-inclusive wall time"},
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
