from dataclasses import dataclass

from .evaluation import MATE_SCORE, PIECE_VALUES, evaluate_for_side_to_move
from .move import Move
from .position import Position

INFINITY = MATE_SCORE + 1
MAX_QUIESCENCE_DEPTH = 8


@dataclass(frozen=True)
class SearchResult:
    best_move: Move | None
    score: int
    nodes: int
    principal_variation: tuple[Move, ...]


def search(position: Position, depth: int) -> SearchResult:
    if depth < 0:
        raise ValueError("search depth must not be negative")
    score, nodes, principal_variation = _negamax(position, depth, -INFINITY, INFINITY)
    best_move = principal_variation[0] if principal_variation else None
    return SearchResult(best_move, score, nodes, principal_variation)


def _negamax(
    position: Position,
    depth: int,
    alpha: int,
    beta: int,
) -> tuple[int, int, tuple[Move, ...]]:
    legal_moves = position.legal_moves()
    if not legal_moves:
        return evaluate_for_side_to_move(position), 1, tuple()
    if depth == 0:
        return _quiescence(position, -INFINITY, INFINITY, 0)

    best_score = -INFINITY
    best_line: tuple[Move, ...] = tuple()
    nodes = 1
    for move in _ordered_moves(position, legal_moves):
        child_score, child_nodes, child_line = _negamax(
            position.make_move(move), depth - 1, -beta, -alpha
        )
        score = -child_score
        nodes += child_nodes
        if score > best_score:
            best_score = score
            best_line = (move,) + child_line
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best_score, nodes, best_line


def _quiescence(
    position: Position,
    alpha: int,
    beta: int,
    depth: int,
) -> tuple[int, int, tuple[Move, ...]]:
    legal_moves = position.legal_moves()
    if not legal_moves or depth == MAX_QUIESCENCE_DEPTH:
        return evaluate_for_side_to_move(position), 1, tuple()

    if position.is_in_check():
        moves = legal_moves
        best_score = -INFINITY
    else:
        best_score = evaluate_for_side_to_move(position)
        if best_score >= beta:
            return best_score, 1, tuple()
        alpha = max(alpha, best_score)
        moves = tuple(move for move in legal_moves if _is_tactical_move(position, move))
        if not moves:
            return best_score, 1, tuple()

    best_line: tuple[Move, ...] = tuple()
    nodes = 1
    for move in _ordered_moves(position, moves):
        child_score, child_nodes, child_line = _quiescence(
            position.make_move(move), -beta, -alpha, depth + 1
        )
        score = -child_score
        nodes += child_nodes
        if score > best_score:
            best_score = score
            best_line = (move,) + child_line
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best_score, nodes, best_line


def _ordered_moves(position: Position, moves: tuple[Move, ...]) -> tuple[Move, ...]:
    return tuple(sorted(moves, key=lambda move: _move_order_score(position, move), reverse=True))


def _is_tactical_move(position: Position, move: Move) -> bool:
    return move.en_passant or move.promotion is not None or position.board[move.to_square] is not None


def _move_order_score(position: Position, move: Move) -> int:
    moving_piece = position.board[move.from_square]
    captured_piece = position.board[move.to_square]
    score = 0
    if captured_piece is not None:
        score += 10 * PIECE_VALUES[captured_piece.lower()]
        score -= PIECE_VALUES[moving_piece.lower()]
    elif move.en_passant:
        score += 10 * PIECE_VALUES["p"] - PIECE_VALUES[moving_piece.lower()]
    if move.promotion is not None:
        score += PIECE_VALUES[move.promotion]
    return score
