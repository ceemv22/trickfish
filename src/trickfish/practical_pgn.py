import argparse
import hashlib
import json
import pathlib
import textwrap
from math import fsum

from .objective_score import ObjectiveScore
from .pgn import san_for_move, tag_value
from .position import Position
from .practical import _score
from .practical_stability import validate_analysis
from .variation import replay_uci_line


def _score_text(value):
    score = ObjectiveScore(cp=value.get("cp"), mate_moves=value.get("mate_moves"), winning=value.get("winning"))
    if value.get("kind") != score.as_dict()["kind"]:
        raise ValueError("invalid score kind")
    return (f"cp {score.cp:+g}" if score.cp is not None else
            ("mate-win " if score.winning else "mate-loss ") + str(score.mate_moves))


def _render_line(root, moves, tags):
    tokens = ["{Analysis line; not an observed game result.}"]
    position = root
    for index, uci in enumerate(moves):
        legal = position.legal_moves()
        by_uci = {move.to_uci(): move for move in legal}
        if uci not in by_uci:
            raise ValueError("illegal PGN line move " + str(uci))
        if position.side_to_move == "w":
            tokens.append(str(position.fullmove_number) + ".")
        elif index == 0:
            tokens.append(str(position.fullmove_number) + "...")
        move = by_uci[uci]
        tokens.append(san_for_move(position, move, legal))
        position = position.make_move(move)
    tags = {**tags, "TrickfishFinalFEN": position.to_fen()}
    header = "\n".join(f'[{name} "{tag_value(value)}"]' for name, value in tags.items())
    return header + "\n\n" + textwrap.fill(" ".join([*tokens, "*"]), width=79,
                                           break_long_words=False, break_on_hyphens=False) + "\n\n"


def render_practical_pgn(report, max_replies=5):
    validate_analysis(report)
    if type(max_replies) is not int or max_replies < 0:
        raise ValueError("max replies must be a nonnegative integer")
    root = Position.from_fen(report["fen"])
    digest = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    base = {"Event": "Trickfish practical analysis", "Site": "?", "Date": "????.??.??", "Round": "?",
            "White": "?", "Black": "?", "Result": "*", "SetUp": "1", "FEN": root.to_fen(),
            "TrickfishPerspective": report["perspective"], "TrickfishSelectionBasis": report["selection_basis"],
            "TrickfishDepth": report["objective"]["depth"], "TrickfishSourceSHA256": digest,
            "TrickfishEngine": ", ".join(report["objective"]["identity"]),
            "TrickfishReplySource": report["reply_model"]["source"]}
    games = []
    if not report["candidates"]:
        return _render_line(root, [], {**base, "TrickfishLineType": "terminal",
                                      "TrickfishTerminalScore": _score_text(report["terminal_score"])})
    for index, candidate in enumerate(report["candidates"], 1):
        if "objective_pv" not in candidate:
            raise ValueError("PGN export requires recorded objective continuations")
        tags = {**base, "Event": "Trickfish " + candidate["move"] + " objective analysis",
                "Round": str(index) + ".0", "TrickfishCandidate": candidate["move"],
                "TrickfishObjective": _score_text(candidate["objective"]), "TrickfishLineType": "objective",
                "TrickfishSelected": str(candidate["move"] == report["selection"]).lower(),
                "TrickfishExpectedCP": "unavailable" if candidate["expected_cp"] is None else str(_score(candidate["expected_cp"]))}
        games.append(_render_line(root, [candidate["move"], *candidate["objective_pv"]], tags))
        details = candidate["reply_details"]
        child = replay_uci_line(root, [candidate["move"]])
        if candidate["objective"]["kind"] == "cp" and child.legal_moves() and not details:
            raise ValueError("nonterminal cp candidates require complete reply evidence")
        if len({reply["move"] for reply in details}) != len(details):
            raise ValueError("duplicate reply scenarios")
        for reply in details:
            probability = _score(reply["probability"])
            if not 0 < probability <= 1:
                raise ValueError("exported reply probability must be positive and at most one")
            if "pv" not in reply:
                raise ValueError("PGN export requires recorded reply continuations")
            _score_text(reply["score"])
            replay_uci_line(root, [candidate["move"], reply["move"], *reply["pv"]])
        if details and abs(fsum(item["probability"] for item in details) - 1) > 1e-9:
            raise ValueError("complete source reply probabilities must sum to one")
        replies = sorted(details, key=lambda item: (-item["probability"], item["move"]))[:max_replies]
        mass = fsum(reply["probability"] for reply in replies)
        for number, reply in enumerate(replies, 1):
            if "pv" not in reply:
                raise ValueError("PGN export requires recorded reply continuations")
            reply_tags = {**tags, "Event": "Trickfish " + candidate["move"] + " reply " + reply["move"],
                          "Round": f"{index}.{number}", "TrickfishLineType": "model-reply",
                          "TrickfishReply": reply["move"], "TrickfishProbability": repr(reply["probability"]),
                          "TrickfishExportedReplyMass": repr(mass), "TrickfishReplyLimit": str(max_replies),
                          "TrickfishReplyOutcome": _score_text(reply["score"])}
            games.append(_render_line(root, [candidate["move"], reply["move"], *reply["pv"]], reply_tags))
    return "".join(games)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trickfish-practical-pgn")
    parser.add_argument("analysis", type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--max-replies", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("output already exists")
        report = json.loads(args.analysis.read_text(encoding="utf-8"))
        rendered = render_practical_pgn(report, args.max_replies)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
