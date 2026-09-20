"""Command-line entry point for position inspection."""

from __future__ import annotations

import argparse

from .position import FenError, Position, STARTING_FEN


def main() -> int:
    parser = argparse.ArgumentParser(prog="trickfish")
    parser.add_argument(
        "fen",
        nargs="?",
        default=STARTING_FEN,
        help="FEN position to inspect; defaults to the initial chess position",
    )
    arguments = parser.parse_args()

    try:
        position = Position.from_fen(arguments.fen)
    except FenError as error:
        parser.error(str(error))

    print(position.render())
    print()
    print(f"side to move: {'white' if position.side_to_move == 'w' else 'black'}")
    print(f"FEN: {position.to_fen()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
