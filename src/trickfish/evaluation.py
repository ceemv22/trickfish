from dataclasses import dataclass

from .position import Position

MATE_SCORE = 100_000
PIECE_VALUES = {
    "p": 100,
    "n": 320,
    "b": 330,
    "r": 500,
    "q": 900,
    "k": 0,
}
PHASE_WEIGHTS = {
    "n": 1,
    "b": 1,
    "r": 2,
    "q": 4,
}
MAX_PHASE = 24


@dataclass(frozen=True)
class EvaluationBreakdown:
    phase: int
    material: int
    piece_activity: int
    pawn_structure: int
    bishop_pair: int
    rook_files: int
    king_safety: int
    king_activity: int

    @property
    def total(self) -> int:
        return (
            self.material
            + self.piece_activity
            + self.pawn_structure
            + self.bishop_pair
            + self.rook_files
            + self.king_safety
            + self.king_activity
        )


def evaluate(position: Position) -> int:
    status = position.game_status()
    if status == "checkmate":
        return -MATE_SCORE if position.side_to_move == "w" else MATE_SCORE
    if status == "stalemate" or position.is_insufficient_material():
        return 0
    return evaluate_breakdown(position).total


def evaluate_breakdown(position: Position) -> EvaluationBreakdown:
    phase = _game_phase(position)
    return EvaluationBreakdown(
        phase,
        _material(position),
        _piece_activity(position),
        _pawn_structure(position, True, phase) - _pawn_structure(position, False, phase),
        _bishop_pair(position),
        _rook_files(position),
        _king_safety(position, phase),
        _king_activity(position, phase),
    )


def evaluate_for_side_to_move(position: Position) -> int:
    score = evaluate(position)
    return score if position.side_to_move == "w" else -score


def _material(position: Position) -> int:
    score = 0
    for piece in position.board:
        if piece is not None:
            score += _signed(piece, PIECE_VALUES[piece.lower()])
    return score


def _piece_activity(position: Position) -> int:
    score = 0
    for square, piece in enumerate(position.board):
        if piece is None:
            continue
        rank, file = divmod(square, 8)
        distance = abs(2 * file - 7) + abs(2 * rank - 7)
        kind = piece.lower()
        if kind == "p":
            advance = 6 - rank if piece.isupper() else rank - 1
            bonus = 5 * advance + (6 if file in {3, 4} else 0)
        elif kind == "n":
            bonus = max(0, 28 - 2 * distance)
        elif kind == "b":
            bonus = max(0, 16 - distance)
        elif kind == "r":
            enemy_pawn = "p" if piece.isupper() else "P"
            on_seventh = (piece.isupper() and rank == 1) or (piece.islower() and rank == 6)
            bonus = 20 if on_seventh and enemy_pawn in position.board else 0
        elif kind == "q":
            bonus = 0
        else:
            bonus = 0
        score += _signed(piece, bonus)
    return score


def _pawn_structure(position: Position, white: bool, phase: int) -> int:
    pawn = "P" if white else "p"
    enemy = "p" if white else "P"
    pawns = [square for square, piece in enumerate(position.board) if piece == pawn]
    enemy_pawns = [square for square, piece in enumerate(position.board) if piece == enemy]
    files = [square % 8 for square in pawns]
    score = 0
    for file in range(8):
        count = files.count(file)
        if count > 1:
            score -= 15 * (count - 1)
    for square in pawns:
        rank, file = divmod(square, 8)
        if not any(adjacent in files for adjacent in (file - 1, file + 1)):
            score -= 12
        passed = True
        for enemy_square in enemy_pawns:
            enemy_rank, enemy_file = divmod(enemy_square, 8)
            ahead = enemy_rank < rank if white else enemy_rank > rank
            if ahead and abs(enemy_file - file) <= 1:
                passed = False
                break
        if passed:
            advance = 6 - rank if white else rank - 1
            endgame_bonus = (MAX_PHASE - phase) * 2 * advance // MAX_PHASE
            score += 8 + 8 * advance + endgame_bonus
    return score


def _bishop_pair(position: Position) -> int:
    white_bonus = 30 if position.board.count("B") >= 2 else 0
    black_bonus = 30 if position.board.count("b") >= 2 else 0
    return white_bonus - black_bonus


def _rook_files(position: Position) -> int:
    if "P" not in position.board and "p" not in position.board:
        return 0
    score = 0
    for square, piece in enumerate(position.board):
        if piece not in {"R", "r"}:
            continue
        file = square % 8
        friendly_pawn = "P" if piece == "R" else "p"
        enemy_pawn = "p" if piece == "R" else "P"
        file_pieces = position.board[file::8]
        bonus = 10 if friendly_pawn not in file_pieces else 0
        if enemy_pawn not in file_pieces:
            bonus += 10
        score += _signed(piece, bonus)
    return score


def _king_safety(position: Position, phase: int) -> int:
    score = 0
    for square, piece in enumerate(position.board):
        if piece not in {"K", "k"}:
            continue
        _, file = divmod(square, 8)
        home_rank = 7 if piece == "K" else 0
        pawn_rank = home_rank - 1 if piece == "K" else home_rank + 1
        pawn = "P" if piece == "K" else "p"
        bonus = 20 if square in ({58, 62} if piece == "K" else {2, 6}) else 0
        for shield_file in (file - 1, file, file + 1):
            if 0 <= shield_file < 8 and position.board[pawn_rank * 8 + shield_file] == pawn:
                bonus += 8
        score += _signed(piece, bonus * phase // MAX_PHASE)
    return score


def _king_activity(position: Position, phase: int) -> int:
    if any(piece in position.board for piece in "QqRr"):
        return 0
    score = 0
    endgame_weight = MAX_PHASE - phase
    for square, piece in enumerate(position.board):
        if piece not in {"K", "k"}:
            continue
        rank, file = divmod(square, 8)
        distance = abs(2 * file - 7) + abs(2 * rank - 7)
        bonus = max(0, 14 - distance) * endgame_weight // MAX_PHASE
        score += _signed(piece, bonus)
    return score


def _game_phase(position: Position) -> int:
    phase = sum(
        PHASE_WEIGHTS.get(piece.lower(), 0)
        for piece in position.board
        if piece is not None
    )
    return min(MAX_PHASE, phase)


def _signed(piece: str, value: int) -> int:
    return value if piece.isupper() else -value
