import argparse
import json
import pathlib
import subprocess
import sys

from trickfish.repertoire import load_repertoire
from trickfish.practical_stability import compare_depths, render_stability


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--stockfish19", action="store_true")
    parser.add_argument("--maia-cache", required=True)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    depth_group = parser.add_mutually_exclusive_group()
    depth_group.add_argument("--depth", type=int)
    depth_group.add_argument("--depths", type=int, nargs="+")
    parser.add_argument("--rating", type=int, default=1500)
    parser.add_argument("--player-rating", type=int, default=1500)
    parser.add_argument("--case")
    parser.add_argument("--manifest", type=pathlib.Path, default=pathlib.Path(__file__).with_name("practical-positions.json"))
    args = parser.parse_args()
    depths = args.depths or [args.depth if args.depth is not None else 6]
    if min(depths) < 1 or len(set(depths)) != len(depths) or (args.depths is not None and len(depths) < 2):
        parser.error("comparison requires distinct positive depths, at least two with --depths")
    depths = sorted(depths)
    try:
        repertoire = load_repertoire(args.manifest)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    cases = [case for case in repertoire.cases if not args.case or case.name == args.case]
    if not cases:
        parser.error("unknown review case")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "manifest.json").write_bytes(repertoire.raw)
    (args.output_dir / "manifest-selection.json").write_text(json.dumps({"manifest_sha256": repertoire.sha256,
        "cases": [{"name": case.name, "fen": case.position.to_fen()} for case in cases]}, indent=2), encoding="utf-8")
    summary = []
    for case in cases:
        position = case.position
        reports = []
        for depth in depths:
            directory = args.output_dir / ("depth-" + str(depth)) if args.depths else args.output_dir
            directory.mkdir(exist_ok=True)
            output = directory / (case.name + ".json")
            report = output.with_suffix(".md")
            command = [sys.executable, "-m", "trickfish.practical_cli", "--engine", args.engine,
                       "--fen", position.to_fen(), "--maia", "rapid", "--maia-cache", args.maia_cache,
                       "--rating", str(args.rating), "--player-rating", str(args.player_rating),
                       "--depth", str(depth), "--output", str(output), "--report", str(report),
                       "--pgn", str(output.with_suffix(".pgn"))]
            if args.stockfish19:
                command.append("--stockfish19")
            completed = subprocess.run(command, capture_output=True, text=True)
            summary.append({"case": case.name, "depth": depth, "fen": position.to_fen(), "returncode": completed.returncode,
                            "stdout": completed.stdout, "stderr": completed.stderr})
            print(case.name, depth, "completed" if completed.returncode == 0 else "rejected", flush=True)
            if completed.returncode == 0:
                reports.append(json.loads(output.read_text(encoding="utf-8")))
            (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if args.depths and len(reports) == len(depths):
            directory = args.output_dir / "comparison"
            directory.mkdir(exist_ok=True)
            try:
                comparison = compare_depths(reports)
            except (ValueError, KeyError, TypeError) as error:
                print(case.name, "comparison rejected:", error, flush=True)
                summary.append({"case": case.name, "stage": "comparison", "returncode": 1, "stderr": str(error)})
                (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
                continue
            (directory / (case.name + ".json")).write_text(json.dumps(comparison, indent=2, allow_nan=False), encoding="utf-8")
            (directory / (case.name + ".md")).write_text(render_stability(comparison), encoding="utf-8")
    return int(any(item["returncode"] for item in summary))


if __name__ == "__main__":
    raise SystemExit(main())
