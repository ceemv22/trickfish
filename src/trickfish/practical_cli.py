import argparse
import hashlib
import json
import pathlib
from dataclasses import asdict

from .objective_uci import UciObjective
from .position import Position
from .practical import rank_practical_moves


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
    parser.add_argument("--replies", required=True, type=pathlib.Path)
    parser.add_argument("--rating", required=True, type=int)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--margin-cp", type=float, default=30)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("output already exists")
        position = Position.from_fen(args.fen)
        model = RecordedReplyModel(args.replies, args.rating)
        command = [str(args.engine.resolve(strict=True)), *args.engine_arg]
        with UciObjective(command, args.depth, args.timeout) as objective:
            ranked = rank_practical_moves(position, objective, model, args.rating, args.margin_cp)
            candidates = []
            for item in ranked:
                child = position.make_move(item.move)
                probabilities = model.used.get(child.to_fen(), {})
                details = [{"move": reply.to_uci(), "probability": probabilities[reply.to_uci()],
                            "cp_original_mover": objective(child.make_move(reply), position.side_to_move)}
                           for reply in child.legal_moves() if probabilities.get(reply.to_uci(), 0) > 0]
                candidates.append({**asdict(item), "move": item.move.to_uci(), "reply_details": details})
            report = {"schema": "trickfish.practical-analysis.v1", "fen": position.to_fen(),
                      "perspective": position.side_to_move, "margin_cp": args.margin_cp,
                      "candidates": candidates, "objective": objective.provenance(),
                      "reply_model": model.provenance(),
                      "limitations": ["one-reply centipawn expectation, not win probability",
                                      "no repetition history or calibrated human-model claim",
                                      "mate scores reject the analysis rather than receiving arbitrary cp"]}
        rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    except (OSError, ValueError, RuntimeError, TimeoutError, IndexError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
