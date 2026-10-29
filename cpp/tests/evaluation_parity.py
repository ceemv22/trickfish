from dataclasses import asdict
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from trickfish.position import Position
from trickfish.evaluation import evaluate, evaluate_breakdown

ROOT_FENS = (
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    '4k3/8/8/8/8/8/P7/4K3 w - - 0 1',
    '4k3/8/8/P7/8/8/8/4K3 w - - 0 1',
    '4k3/8/8/8/8/8/PP6/4K3 w - - 0 1',
    '4k3/8/8/8/8/P7/P7/4K3 w - - 0 1',
    '4k3/p7/8/8/8/8/P7/4K3 w - - 0 1',
    '4k3/8/1p6/8/P7/8/8/4K3 w - - 0 1',
    '4k3/8/8/P7/8/1p6/8/4K3 w - - 0 1',
    '4k3/8/8/P7/8/8/8/1Q2K3 w - - 0 1',
    '3qk3/8/8/P7/8/8/8/3QK3 w - - 0 1',
    'rnbqkbnr/pppppppp/8/8/8/8/QQPPPPPP/RNBQKBNR w KQkq - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    '4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1',
    '4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1',
    '4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1',
    '4k3/8/8/8/8/8/8/2B1K3 w - - 0 1',
    '7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',
    '8/8/8/8/8/6k1/6q1/7K w - - 0 1',
    '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1',
    '4k3/P7/8/8/8/8/8/4K3 w - - 0 1',
    'n6k/8/8/8/3N4/8/8/4K3 w - - 0 1',
    'k6b/8/8/8/3B4/8/P7/4K3 w - - 0 1',
    'k7/8/8/8/3K4/8/P7/8 w - - 0 1',
    'k7/8/8/8/3K4/8/P7/1Q6 w - - 0 1',
    '1q2k3/8/8/8/8/8/5PPP/1Q4K1 w - - 0 1',
    '1q2k3/8/8/8/8/8/PPP5/1QK5 w - - 0 1',
    '1q2k3/8/8/8/8/8/3PPP2/1Q2K3 w - - 0 1',
    '4k3/R6p/8/8/8/8/8/4K3 w - - 0 1',
    '4k3/R7/8/8/8/8/8/4K3 w - - 0 1',
    '4k3/8/8/8/8/8/5PPP/6KN w - - 0 1',
)

def expected_fields(position):
    detail = evaluate_breakdown(position)
    return dict(asdict(detail), static_total=detail.total, evaluation=evaluate(position))


def mirrored(position):
    board = tuple(piece.swapcase() if piece is not None else None for rank in range(7, -1, -1) for piece in position.board[rank * 8:rank * 8 + 8])
    return Position(board, "b" if position.side_to_move == "w" else "w", "-", None,
        position.halfmove_clock, position.fullmove_number)

def activity_square_positions():
    for symbol in "PNBRQpnbrq":
        for square in range(64):
            if symbol.lower() == "p" and square // 8 in (0, 7):
                continue
            variants = (False, True) if symbol.lower() == "r" else (False,)
            for enemy_pawn in variants:
                board = [None] * 64
                board[7 if square == 0 else 0] = "k"
                board[56 if square == 63 else 63] = "K"
                board[square] = symbol
                if enemy_pawn:
                    board[28 if square == 27 else 27] = "p" if symbol.isupper() else "P"
                position = Position(tuple(board), "b" if symbol.isupper() else "w", "-", None, 0, 1)
                opposite = "w" if position.side_to_move == "b" else "b"
                if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
                    raise AssertionError("invalid activity-square fixture")
                yield position


def positions_for_checks():
    positions = {}
    for fen in ROOT_FENS:
        position = Position.from_fen(fen)
        opposite = "b" if position.side_to_move == "w" else "w"
        if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
            raise AssertionError(f"invalid reference fixture: {fen}")
        positions[position.to_fen()] = position
        mirror = mirrored(position)
        original = expected_fields(position)
        reflected = expected_fields(mirror)
        for field in ["material", "piece_activity", "pawn_structure", "bishop_pair", "rook_files", "king_safety", "king_activity", "static_total", "evaluation"]:
            if reflected[field] != -original[field]:
                raise AssertionError(f"reference color symmetry failed for {field}: {fen}")
        if reflected["phase"] != original["phase"]:
            raise AssertionError(f"reference phase symmetry failed: {fen}")
        positions[mirror.to_fen()] = mirror
        legal = position.legal_moves()
        selected = list(legal[:2]) + [move for move in legal if move.promotion is not None or move.en_passant]
        for move in selected:
            child = position.make_move(move)
            positions[child.to_fen()] = child
    for position in activity_square_positions():
        positions[position.to_fen()] = position
    return positions

def main():
    binary = str(pathlib.Path(sys.argv[1]).resolve())
    positions = positions_for_checks()
    for fen, position in positions.items():
        result = subprocess.run([binary, "--eval-detail", fen], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise RuntimeError(f"C++ evaluation rejected {fen}: {result.stderr}")
        actual = {}
        for line in result.stdout.splitlines():
            name, value = line.split()
            if name in actual:
                raise AssertionError(f"duplicate evaluation field: {name}")
            actual[name] = int(value)
        expected = expected_fields(position)
        if actual != expected:
            raise AssertionError(f"evaluation term mismatch for {fen}: expected {expected}, got {actual}")
    print(f"C++/Python reference-evaluator parity passed for {len(positions)} positions")

if __name__ == "__main__":
    main()
