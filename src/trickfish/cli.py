from __future__ import annotations

import argparse

from .position import FenError, Position, STARTING_FEN


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trickfish")
    parser.add_argument(
        "command_or_fen",
        nargs="?",
        help="position, moves, or a FEN position",
    )
    parser.add_argument("fen", nargs="?", help="FEN position")
    arguments = parser.parse_args(argv)

    if arguments.command_or_fen in {"position", "moves"}:
        command = arguments.command_or_fen
        fen = arguments.fen or STARTING_FEN
    elif arguments.fen is not None:
        parser.error("a FEN must be quoted as one argument")
    else:
        command = "position"
        fen = arguments.command_or_fen or STARTING_FEN

    try:
        position = Position.from_fen(fen)
    except FenError as error:
        parser.error(str(error))

    if command == "moves":
        for move in position.pseudo_legal_moves():
            print(move.to_uci())
        return 0

    print(position.render())
    print()
    print(f"side to move: {'white' if position.side_to_move == 'w' else 'black'}")
    print(f"FEN: {position.to_fen()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
