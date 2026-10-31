import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from trickfish.position import Position


def fixtures():
    base = Position.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    cases = []
    for bits in range(16):
        rights = "".join(symbol for index, symbol in enumerate("KQkq") if bits & (1 << index)) or "-"
        for side in ("w", "b"):
            cases.append((f"base-{bits}-{side}", Position(base.board, side, rights, None, 0, 1)))
    def variant(name, board):
        cases.append((name + "-w", Position(tuple(board), "w", "KQkq", None, 0, 1)))
        reflected = [None] * 64
        for square, piece in enumerate(board):
            reflected[square ^ 56] = piece.swapcase() if piece is not None else None
        cases.append((name + "-b", Position(tuple(reflected), "b", "KQkq", None, 0, 1)))
    for square in (57, 58, 59, 61, 62):
        board = list(base.board)
        board[square] = "N"
        variant("blocked-" + "abcdefgh"[square % 8], board)
    for missing in range(1, 4):
        board = list(base.board)
        if missing & 1: board[56] = None
        if missing & 2: board[63] = None
        variant(f"missing-rook-{missing}", board)
    board = list(base.board)
    board[60], board[52] = None, "K"
    variant("king-away", board)
    for file in range(8):
        board = list(base.board)
        board[32 + file] = "r"
        variant("attack-" + "abcdefgh"[file], board)
    for side in ("w", "b"):
        cases.append(("start-" + side, Position.from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR " + side + " KQkq - 0 1")))
    return cases


def expected_divide(position):
    return {move.to_uci(): len(position.make_move(move).legal_moves()) for move in position.legal_moves()}


def parse_divide(output):
    fields = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] in fields or not parts[1].isascii() or not parts[1].isdecimal():
            raise ValueError("invalid or duplicate divide field")
        fields[parts[0]] = int(parts[1])
    if "total" not in fields: raise ValueError("divide omitted total")
    total = fields.pop("total")
    if sum(fields.values()) != total: raise ValueError("divide total disagrees with branches")
    return fields


def main():
    binary = pathlib.Path(sys.argv[1]).resolve(strict=True)
    cases = fixtures()
    for name, position in cases:
        result = subprocess.run([str(binary), "--divide", "2", position.to_fen()], capture_output=True,
            text=True, timeout=15, check=True)
        actual, expected = parse_divide(result.stdout), expected_divide(position)
        if actual != expected:
            raise AssertionError(f"castling/legal divide mismatch: {name}: {actual} != {expected}")
    print(f"Python/C++ depth-two legal divide parity passed for {len(cases)} castling boundary positions")


if __name__ == "__main__":
    main()
