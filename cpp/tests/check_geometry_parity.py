import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from trickfish.position import Position


def segment(king, attacker):
    dr, df = attacker // 8 - king // 8, attacker % 8 - king % 8
    if dr != 0 and df != 0 and abs(dr) != abs(df): return []
    step_r, step_f = (dr > 0) - (dr < 0), (df > 0) - (df < 0)
    rank, file = king // 8 + step_r, king % 8 + step_f
    result = []
    while rank != attacker // 8 or file != attacker % 8:
        result.append(rank * 8 + file)
        rank, file = rank + step_r, file + step_f
    return result


def fixtures():
    positions = {}
    for color in ("w", "b"):
        for king in (0, 27, 36, 63):
            for attacker in (1, 9, 18, 28, 45, 62):
                if king == attacker: continue
                for piece in "pnbrq":
                    if piece == "p" and attacker // 8 in (0, 7): continue
                    line = segment(king, attacker)
                    for blocker in (None, "own", "enemy") if piece in "brq" and line else (None,):
                        board = [None] * 64
                        board[king] = "K" if color == "w" else "k"
                        board[attacker] = piece if color == "w" else piece.upper()
                        if blocker is not None:
                            board[line[0]] = "N" if (color == "w") == (blocker == "own") else "n"
                        other = next(square for square in range(64) if board[square] is None and square not in line and
                            max(abs(square // 8 - king // 8), abs(square % 8 - king % 8)) > 1)
                        board[other] = "k" if color == "w" else "K"
                        position = Position(tuple(board), "w", "-", None, 0, 1)
                        positions[position.to_fen()] = position
    for fen in ("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
            "4k3/8/8/8/8/8/8/4K3 w - - 0 1", "k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1",
            "4k3/8/8/r4pPK/8/8/8/8 w - f6 0 1", "4k3/8/5P2/r6K/8/8/8/8 w - - 0 1",
            "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1"):
        position = Position.from_fen(fen)
        positions[position.to_fen()] = position
    return list(positions.values())


def expected_checks(position):
    return {"white_check": position.is_square_attacked(position._king_square("w"), "b"),
        "black_check": position.is_square_attacked(position._king_square("b"), "w")}


def parse_checks(output):
    fields = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] in fields or parts[1] not in ("true", "false"):
            raise ValueError("invalid check diagnostic field")
        fields[parts[0]] = parts[1] == "true"
    if set(fields) != {"white_check", "black_check"}: raise ValueError("unexpected check diagnostic fields")
    return fields


def main():
    binary = pathlib.Path(sys.argv[1]).resolve(strict=True)
    positions = fixtures()
    for position in positions:
        result = subprocess.run([str(binary), "--check-detail", position.to_fen()], capture_output=True,
            text=True, timeout=15, check=True)
        actual, expected = parse_checks(result.stdout), expected_checks(position)
        if actual != expected:
            raise AssertionError(f"targeted check mismatch: {position.to_fen()}: {actual} != {expected}")
    print(f"Python/C++ static check parity passed for {len(positions)} geometry/blocker/special-move positions")


if __name__ == "__main__":
    main()
