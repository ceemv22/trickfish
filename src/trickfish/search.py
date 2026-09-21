from dataclasses import dataclass

from .evaluation import MATE_SCORE, evaluate_for_side_to_move
from .move import Move
from .position import Position

INFINITY = MATE_SCORE + 1


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
    if depth == 0 or not legal_moves:
        return evaluate_for_side_to_move(position), 1, tuple()

    best_score = -INFINITY
    best_line: tuple[Move, ...] = tuple()
    nodes = 1
    for move in legal_moves:
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
