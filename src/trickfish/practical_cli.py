import argparse
import hashlib
import json
import pathlib

from .objective_uci import UciObjective
from .position import Position
from .practical_analysis import analyze_practical_moves
from .practical_report import render_report


class RecordedReplyModel:
    def __init__(self, path, rating):
        self.raw = pathlib.Path(path).read_bytes()
        self.data = json.loads(self.raw)
        if not isinstance(self.data, dict):
            raise ValueError("reply-distribution document must be an object")
        if self.data.get("schema") != "trickfish.reply-distributions.v1":
            raise ValueError("unsupported reply-distribution schema")
        if type(self.data.get("rating")) is not int or self.data["rating"] != rating:
            raise ValueError("reply-distribution rating mismatch")
        if not isinstance(self.data.get("source"), str) or not self.data["source"].strip():
            raise ValueError("reply distributions require a source description")
        if not isinstance(self.data.get("positions"), dict):
            raise ValueError("reply distributions require a position mapping")
        self.used = {}

    def __call__(self, position, rating):
        if rating != self.data["rating"]:
            raise ValueError("reply-distribution rating mismatch")
        fen = position.to_fen()
        probabilities = self.data["positions"].get(fen)
        if not isinstance(probabilities, dict):
            raise ValueError("missing reply distribution for " + fen)
        self.used[fen] = dict(probabilities)
        return probabilities

    def provenance(self):
        return {"source": self.data["source"], "sha256": hashlib.sha256(self.raw).hexdigest(),
                "rating": self.data["rating"], "positions": self.used,
                "calibration": "supplied externally; not verified by Trickfish"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trickfish-practical")
    parser.add_argument("--engine", required=True, type=pathlib.Path)
    parser.add_argument("--engine-arg", action="append", default=[])
    parser.add_argument("--fen", required=True)
    providers = parser.add_mutually_exclusive_group(required=True)
    providers.add_argument("--replies", type=pathlib.Path)
    providers.add_argument("--maia", choices=("rapid", "blitz"))
    parser.add_argument("--maia-cache", type=pathlib.Path)
    parser.add_argument("--player-rating", type=int)
    parser.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    parser.add_argument("--rating", required=True, type=int)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--margin-cp", type=float, default=30)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("output already exists")
        if args.report and (args.report.exists() or args.report.resolve() == args.output.resolve()):
            raise ValueError("report must be a separate new file")
        position = Position.from_fen(args.fen)
        if args.maia:
            if args.maia_cache is None or args.player_rating is None:
                raise ValueError("Maia requires --maia-cache and --player-rating")
            from .maia_reply import MaiaReplyModel

            model = MaiaReplyModel(args.maia, args.maia_cache, args.player_rating, args.device)
        else:
            model = RecordedReplyModel(args.replies, args.rating)
        command = [str(args.engine.resolve(strict=True)), *args.engine_arg]
        with UciObjective(command, args.depth, args.timeout) as objective:
            analysis = analyze_practical_moves(position, objective.evaluate, model, args.rating, args.margin_cp)
            report = {"schema": "trickfish.practical-analysis.v2", "fen": position.to_fen(),
                      "perspective": position.side_to_move, "margin_cp": args.margin_cp,
                      "opponent_rating": args.rating,
                      **analysis, "objective": objective.provenance(),
                      "reply_model": model.provenance(),
                      "limitations": ["one-reply centipawn expectation, not win probability",
                                      "no repetition history or calibrated human-model claim",
                                      "mixed mate/cp replies disable expected-cp comparison and use objective fallback"]}
        rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
        if args.report:
            with args.report.open("x", encoding="utf-8") as stream:
                stream.write(render_report(report))
    except (OSError, ValueError, RuntimeError, TimeoutError, IndexError, ImportError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
