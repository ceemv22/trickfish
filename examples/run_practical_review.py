import argparse
import json
import pathlib
import subprocess
import sys

from trickfish.position import Position, STARTING_FEN


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--maia-cache", required=True)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument("--depth", type=int, default=6)
    parser.add_argument("--rating", type=int, default=1500)
    parser.add_argument("--player-rating", type=int, default=1500)
    parser.add_argument("--case")
    args = parser.parse_args()
    manifest = json.loads(pathlib.Path(__file__).with_name("practical-positions.json").read_text())
    cases = [case for case in manifest["positions"] if not args.case or case["name"] == args.case]
    if not cases:
        parser.error("unknown review case")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    summary = []
    for case in cases:
        position = Position.from_fen(STARTING_FEN)
        for uci in case["moves"]:
            legal = {move.to_uci(): move for move in position.legal_moves()}
            position = position.make_move(legal[uci])
        output = args.output_dir / (case["name"] + ".json")
        report = output.with_suffix(".md")
        command = [sys.executable, "-m", "trickfish.practical_cli", "--engine", args.engine,
                   "--fen", position.to_fen(), "--maia", "rapid", "--maia-cache", args.maia_cache,
                   "--rating", str(args.rating), "--player-rating", str(args.player_rating),
                   "--depth", str(args.depth), "--output", str(output), "--report", str(report)]
        completed = subprocess.run(command, capture_output=True, text=True)
        summary.append({"case": case["name"], "fen": position.to_fen(), "returncode": completed.returncode,
                        "stdout": completed.stdout, "stderr": completed.stderr})
        print(case["name"], "completed" if completed.returncode == 0 else "rejected", flush=True)
        (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return int(any(item["returncode"] for item in summary))


if __name__ == "__main__":
    raise SystemExit(main())
