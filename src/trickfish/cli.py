from __future__ import annotations

import argparse

from .position import FenError, Position, STARTING_FEN
from .evaluation import evaluate, evaluate_breakdown
from .search import search


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trickfish")
    parser.add_argument(
        "command_or_fen",
        nargs="?",
        help="position, moves, pseudo-moves, status, eval, eval-detail, perft, divide, search, search-time, or a FEN position",
    )
    parser.add_argument("argument", nargs="?", help="FEN position or perft depth")
    parser.add_argument("fen", nargs="?", help="FEN position for perft")
    arguments = parser.parse_args(argv)
    time_limit_ms = None

    if arguments.command_or_fen in {
        "position", "moves", "pseudo-moves", "status", "eval", "eval-detail"
    }:
        command = arguments.command_or_fen
        if arguments.fen is not None:
            parser.error("a FEN must be quoted as one argument")
        fen = arguments.argument or STARTING_FEN
        depth = None
    elif arguments.command_or_fen in {"perft", "divide", "search", "search-time"}:
        command = arguments.command_or_fen
        if arguments.argument is None:
            parser.error(f"{command} requires a depth")
        try:
            depth = int(arguments.argument)
        except ValueError:
            parser.error(f"{command} depth must be an integer")
        if command == "search-time":
            time_limit_ms = depth
            depth = 64
        if time_limit_ms is not None and time_limit_ms < 1:
            parser.error("search-time requires at least one millisecond")
        if depth < (1 if command == "divide" else 0):
            parser.error(
                "divide depth must be at least one"
                if command == "divide"
                else f"{command} depth must not be negative"
            )
        fen = arguments.fen or STARTING_FEN
    elif arguments.argument is not None:
        parser.error("a FEN must be quoted as one argument")
    else:
        command = "position"
        fen = arguments.command_or_fen or STARTING_FEN
        depth = None

    try:
        position = Position.from_fen(fen)
    except FenError as error:
        parser.error(str(error))

    if command == "perft":
        print(position.perft(depth))
        return 0

    if command == "divide":
        for move, nodes in position.perft_divide(depth):
            print(f"{move.to_uci()}: {nodes}")
        return 0

    if command == "status":
        print(position.game_status())
        return 0

    if command == "eval":
        print(evaluate(position))
        return 0

    if command == "eval-detail":
        breakdown = evaluate_breakdown(position)
        print(f"phase {breakdown.phase}/{24}")
        print(f"material {breakdown.material}")
        print(f"activity {breakdown.piece_activity}")
        print(f"pawns {breakdown.pawn_structure}")
        print(f"bishop-pair {breakdown.bishop_pair}")
        print(f"rook-files {breakdown.rook_files}")
        print(f"king-safety {breakdown.king_safety}")
        print(f"king-activity {breakdown.king_activity}")
        print(f"total {breakdown.total}")
        return 0

    if command in {"search", "search-time"}:
        result = search(position, depth, time_limit_ms)
        print(f"bestmove {result.best_move.to_uci() if result.best_move else '(none)'}")
        print(f"score {result.score}")
        if command == "search-time":
            print(f"depth {result.completed_depth}")
        print(f"nodes {result.nodes}")
        if command == "search-time":
            print(f"time {result.elapsed_ms}")
            print(f"tthits {result.transposition_hits}")
        print("pv " + " ".join(move.to_uci() for move in result.principal_variation))
        return 0

    if command in {"moves", "pseudo-moves"}:
        moves = position.legal_moves() if command == "moves" else position.pseudo_legal_moves()
        for move in moves:
            print(move.to_uci())
        return 0

    print(position.render())
    print()
    print(f"side to move: {'white' if position.side_to_move == 'w' else 'black'}")
    print(f"FEN: {position.to_fen()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
