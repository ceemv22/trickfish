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


def evaluate(position: Position) -> int:
    status = position.game_status()
    if status == "checkmate":
        return -MATE_SCORE if position.side_to_move == "w" else MATE_SCORE
    if status == "stalemate" or position.is_insufficient_material():
        return 0
    score = 0
    for piece in position.board:
        if piece is not None:
            value = PIECE_VALUES[piece.lower()]
            score += value if piece.isupper() else -value
    return score


def evaluate_for_side_to_move(position: Position) -> int:
    score = evaluate(position)
    return score if position.side_to_move == "w" else -score
