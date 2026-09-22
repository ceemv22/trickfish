from dataclasses import dataclass
from time import perf_counter

from .evaluation import MATE_SCORE, PIECE_VALUES, evaluate_for_side_to_move
from .move import Move
from .position import Position
from .transposition import (
    EXACT,
    LOWER_BOUND,
    UPPER_BOUND,
    TranspositionEntry,
    TranspositionTable,
)

INFINITY = MATE_SCORE + 1
MAX_QUIESCENCE_DEPTH = 8


@dataclass(frozen=True)
class SearchResult:
    best_move: Move | None
    score: int
    nodes: int
    principal_variation: tuple[Move, ...]
    transposition_hits: int
    completed_depth: int
    elapsed_ms: int


class SearchTimeout(Exception):
    pass


@dataclass
class SearchContext:
    table: TranspositionTable
    deadline: float | None
    nodes: int = 0

    def visit(self) -> None:
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise SearchTimeout
        self.nodes += 1


def search(
    position: Position,
    depth: int,
    time_limit_ms: int | None = None,
) -> SearchResult:
    if depth < 0:
        raise ValueError("search depth must not be negative")
    if time_limit_ms is not None and time_limit_ms < 0:
        raise ValueError("search time limit must not be negative")
    started = perf_counter()
    legal_moves = position.legal_moves()
    if not legal_moves:
        return SearchResult(
            None,
            evaluate_for_side_to_move(position),
            1,
            tuple(),
            0,
            depth,
            int((perf_counter() - started) * 1000),
        )
    table = TranspositionTable()
    deadline = None if time_limit_ms is None else started + time_limit_ms / 1000
    context = SearchContext(table, deadline)
    score = evaluate_for_side_to_move(position)
    principal_variation = (_ordered_moves(position, legal_moves)[0],)
    completed_depth = 0
    depths = (0,) if depth == 0 else range(1, depth + 1)
    for current_depth in depths:
        try:
            score, _, iteration_line = _negamax(
                position, current_depth, -INFINITY, INFINITY, context
            )
        except SearchTimeout:
            break
        principal_variation = iteration_line
        completed_depth = current_depth
    best_move = principal_variation[0] if principal_variation else None
    return SearchResult(
        best_move,
        score,
        context.nodes,
        principal_variation,
        table.hits,
        completed_depth,
        int((perf_counter() - started) * 1000),
    )


def _negamax(
    position: Position,
    depth: int,
    alpha: int,
    beta: int,
    context: SearchContext,
) -> tuple[int, int, tuple[Move, ...]]:
    context.visit()
    original_alpha = alpha
    original_beta = beta
    key = position.zobrist_key
    entry = context.table.probe(key)
    preferred_move = entry.best_move if entry is not None else None
    if entry is not None and entry.depth >= depth:
        if entry.bound == EXACT:
            line = (entry.best_move,) if entry.best_move is not None else tuple()
            return entry.score, 1, line
        if entry.bound == LOWER_BOUND:
            alpha = max(alpha, entry.score)
        elif entry.bound == UPPER_BOUND:
            beta = min(beta, entry.score)
        if alpha >= beta:
            line = (entry.best_move,) if entry.best_move is not None else tuple()
            return entry.score, 1, line

    legal_moves = position.legal_moves()
    if not legal_moves:
        score = evaluate_for_side_to_move(position)
        context.table.store(key, TranspositionEntry(depth, score, EXACT, None))
        return score, 1, tuple()
    if depth == 0:
        return _quiescence(position, -INFINITY, INFINITY, 0, context)

    best_score = -INFINITY
    best_line: tuple[Move, ...] = tuple()
    nodes = 1
    for move in _ordered_moves(position, legal_moves, preferred_move):
        child_score, child_nodes, child_line = _negamax(
            position.make_move(move), depth - 1, -beta, -alpha, context
        )
        score = -child_score
        nodes += child_nodes
        if score > best_score:
            best_score = score
            best_line = (move,) + child_line
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    if best_score <= original_alpha:
        bound = UPPER_BOUND
    elif best_score >= original_beta:
        bound = LOWER_BOUND
    else:
        bound = EXACT
    context.table.store(key, TranspositionEntry(depth, best_score, bound, best_line[0]))
    return best_score, nodes, best_line


def _quiescence(
    position: Position,
    alpha: int,
    beta: int,
    depth: int,
    context: SearchContext,
) -> tuple[int, int, tuple[Move, ...]]:
    context.visit()
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
            position.make_move(move), -beta, -alpha, depth + 1, context
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


def _ordered_moves(
    position: Position,
    moves: tuple[Move, ...],
    preferred_move: Move | None = None,
) -> tuple[Move, ...]:
    return tuple(
        sorted(
            moves,
            key=lambda move: (
                move == preferred_move,
                _move_order_score(position, move),
            ),
            reverse=True,
        )
    )


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
