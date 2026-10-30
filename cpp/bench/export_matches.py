import argparse
from datetime import datetime, timezone
import json
import pathlib
import re
import sys
import textwrap

from uci_matches import DRAW_POLICY, adjudicate, repetition_identity, score_games, validate_profile
from search_benchmark import validate_output_path
from collections import Counter
from trickfish.position import Position

INITIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def san_for_move(position, move, legal=None):
    legal = position.legal_moves() if legal is None else legal
    if move not in legal:
        raise ValueError("SAN move is not legal")
    symbol = position.board[move.from_square]
    kind = symbol.upper()
    origin, target = move.to_uci()[:2], move.to_uci()[2:4]
    capture = move.en_passant or position.board[move.to_square] is not None
    if move.castling:
        text = "O-O" if move.to_square > move.from_square else "O-O-O"
    else:
        text = "" if kind == "P" else kind
        if kind == "P":
            if capture: text += origin[0]
        else:
            rivals = [other for other in legal if other.from_square != move.from_square and
                other.to_square == move.to_square and position.board[other.from_square] == symbol]
            if rivals:
                if all(other.from_square % 8 != move.from_square % 8 for other in rivals):
                    text += origin[0]
                elif all(other.from_square // 8 != move.from_square // 8 for other in rivals):
                    text += origin[1]
                else:
                    text += origin
        text += ("x" if capture else "") + target
        if move.promotion is not None: text += "=" + move.promotion.upper()
    child = position.make_move(move)
    status = child.game_status()
    if status == "checkmate": text += "#"
    elif child.is_in_check(): text += "+"
    return text


def tag_value(value):
    text = "".join(character if ord(character) >= 32 and ord(character) != 127 else " " for character in str(value))
    return text.replace("\\", "\\\\").replace('"', '\\"')


def game_date(game):
    if "started_utc" not in game:
        return "????.??.??"
    started = datetime.fromisoformat(game["started_utc"])
    if started.tzinfo is None:
        raise ValueError("game start timestamp must include a timezone")
    return started.astimezone(timezone.utc).strftime("%Y.%m.%d")


def render_game(game, engines, policy):
    if {game["white"], game["black"]} != {"a", "b"}:
        raise ValueError("invalid game engine assignment")
    if game["result"] not in {"1-0", "0-1", "1/2-1/2", "*"}:
        raise ValueError("invalid game result")
    position = Position.from_fen(game["root_fen"])
    opposite = "b" if position.side_to_move == "w" else "w"
    if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
        raise ValueError("nonmoving king is checked in replay root")
    root_fen = position.to_fen()
    counts = Counter([repetition_identity(position)])
    book = game["opening_plies"]
    moves = game["moves"]
    decisions = game["decisions"]
    if type(book) is not int or not 0 <= book <= len(moves) or len(decisions) != len(moves) - book:
        raise ValueError("opening/decision move counts disagree")
    if len(decisions) > policy["searched_ply_limit"]:
        raise ValueError("game exceeds recorded ply cap")
    tokens = []
    for index, text in enumerate(moves):
        if adjudicate(position, counts) is not None:
            raise ValueError("replay continues after game end")
        legal = position.legal_moves()
        by_text = {move.to_uci(): move for move in legal}
        if text not in by_text:
            raise ValueError(f"illegal replay move: {text}")
        if index >= book:
            decision = decisions[index - book]
            label = game["white"] if position.side_to_move == "w" else game["black"]
            if decision["move"] != text or decision["side"] != position.side_to_move or decision["engine"] != label:
                raise ValueError("decision disagrees with replay")
        if position.side_to_move == "w": tokens.append(f"{position.fullmove_number}.")
        elif index == 0: tokens.append(f"{position.fullmove_number}...")
        tokens.append(san_for_move(position, by_text[text], legal))
        position = position.make_move(by_text[text])
        counts[repetition_identity(position)] += 1
    if position.to_fen() != Position.from_fen(game["final_fen"]).to_fen():
        raise ValueError("replay does not match final FEN")
    outcome = adjudicate(position, counts)
    if game["result"] == "*":
        if outcome is not None or game["reason"] != "searched_ply_limit" or len(decisions) != policy["searched_ply_limit"]:
            raise ValueError("unfinished result disagrees with replay/cap")
    elif outcome != (game["result"], game["reason"]):
        raise ValueError("result/reason disagrees with replay adjudication")
    names = game.get("engine_names", {})
    tags = {"Event": "Trickfish UCI match", "Site": "?", "Date": game_date(game),
        "Round": str(game.get("round", "?")), "White": names.get(game["white"], "?"),
        "Black": names.get(game["black"], "?"), "Result": game["result"]}
    if root_fen != INITIAL:
        tags.update(SetUp="1", FEN=root_fen)
    tags.update(Opening=game["opening"], OpeningPlies=str(book), TrickfishReason=game["reason"],
        WhiteSHA256=engines[game["white"]]["sha256"], BlackSHA256=engines[game["black"]]["sha256"])
    if "applied_options" in game:
        for side, label in [("White", game["white"]), ("Black", game["black"])]:
            profile = validate_profile(game["applied_options"].get(label, {}))
            tags[side + "UCIProfile"] = json.dumps(profile, sort_keys=True, separators=(",", ":"))
    header = "\n".join(f'[{name} "{tag_value(value)}"]' for name, value in tags.items())
    tokens.append(game["result"])
    return header + "\n\n" + textwrap.fill(" ".join(tokens), width=79,
        break_long_words=False, break_on_hyphens=False) + "\n\n"


def validate_profile_provenance(report):
    def normalized(profile):
        return {name.casefold(): (type(value).__name__, value) for name, value in validate_profile(profile).items()}
    requested = report.get("profiles")
    if requested is not None:
        if not isinstance(requested, dict) or set(requested) != {"a", "b"}:
            raise ValueError("report profiles require exactly engine keys a/b")
        requested = {label: normalized(profile) for label, profile in requested.items()}
    elif "profiles" in report:
        raise ValueError("report profiles must be an object")
    for game in report["games"]:
        if "applied_options" not in game:
            if requested is not None:
                raise ValueError("profiled report is missing game applied options")
            continue
        applied = game["applied_options"]
        if not isinstance(applied, dict) or set(applied) != {"a", "b"}:
            raise ValueError("game applied options require exactly engine keys a/b")
        applied = {label: normalized(profile) for label, profile in applied.items()}
        if requested is not None and applied != requested:
            raise ValueError("requested and applied UCI profiles disagree")


def export_report(report):
    if report.get("schema_version") != 1 or not report.get("games"):
        raise ValueError("expected a nonempty schema-1 match report")
    validate_profile_provenance(report)
    policy = report["policy"]
    if policy["draws"] != DRAW_POLICY or type(policy["searched_ply_limit"]) is not int or policy["searched_ply_limit"] < 1:
        raise ValueError("unsupported match adjudication/ply-cap policy")
    engines = report["engines"]
    for label in ("a", "b"):
        if re.fullmatch(r"[0-9a-f]{64}", engines[label]["sha256"]) is None:
            raise ValueError("invalid engine hash provenance")
    if report["scores"] != score_games(report["games"]):
        raise ValueError("match summary disagrees with game results")
    return "".join(render_game(game, engines, policy) for game in report["games"])


def main():
    parser = argparse.ArgumentParser(description="Replay-validate and export UCI match JSON to UTF-8 PGN mainlines")
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate_output_path(args.output, [args.report])
    except ValueError as error:
        parser.error(str(error))
    pgn = export_report(json.loads(args.report.read_text(encoding="utf-8")))
    if args.output is None: sys.stdout.write(pgn)
    else: args.output.write_text(pgn, encoding="utf-8")


if __name__ == "__main__":
    main()
