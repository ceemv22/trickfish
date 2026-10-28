import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from trickfish.position import Position
from trickfish.evaluation import _material, _bishop_pair, _rook_files, _game_phase, _pawn_structure

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
)

def expected_fields(position):
    phase = _game_phase(position)
    fields = {
        "phase": phase,
        "material": _material(position),
        "pawn_structure": _pawn_structure(position, True, phase) - _pawn_structure(position, False, phase),
        "bishop_pair": _bishop_pair(position),
        "rook_files": _rook_files(position),
    }
    fields["static_total"] = sum(value for key, value in fields.items() if key != "phase")
    status = position.game_status()
    if status == "checkmate":
        fields["evaluation"] = -100000 if position.side_to_move == "w" else 100000
    elif status == "stalemate" or position.is_insufficient_material():
        fields["evaluation"] = 0
    else:
        fields["evaluation"] = fields["static_total"]
    return fields

def mirrored(position):
    board = tuple(piece.swapcase() if piece is not None else None for piece in reversed(position.board))
    return Position(board, "b" if position.side_to_move == "w" else "w", "-", None,
        position.halfmove_clock, position.fullmove_number)

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
        for field in ["material", "pawn_structure", "bishop_pair", "rook_files", "static_total"]:
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
    print(f"C++/Python implemented-term parity passed for {len(positions)} positions")

if __name__ == "__main__":
    main()
