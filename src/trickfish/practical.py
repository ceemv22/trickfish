from dataclasses import dataclass
from math import fsum, isclose, isfinite
from typing import Mapping, Protocol

from .move import Move
from .position import Position


class ObjectiveEvaluator(Protocol):
    def __call__(self, position: Position, perspective: str) -> float: ...


class ReplyModel(Protocol):
    def __call__(self, position: Position, opponent_rating: int) -> Mapping[str, float]: ...


@dataclass(frozen=True)
class PracticalCandidate:
    move: Move
    objective_cp: float
    expected_cp: float
    trap_cp: float
    objective_loss_cp: float
    replies: int


def _score(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("evaluation must be finite centipawns, without mate encodings")
    return float(value)


def rank_practical_moves(
    position: Position,
    evaluator: ObjectiveEvaluator,
    reply_model: ReplyModel,
    opponent_rating: int,
    margin_cp: float = 30.0,
) -> tuple[PracticalCandidate, ...]:
    margin_cp = _score(margin_cp)
    if margin_cp < 0:
        raise ValueError("margin must be nonnegative")
    if type(opponent_rating) is not int or opponent_rating <= 0:
        raise ValueError("opponent rating must be a positive integer")
    perspective = position.side_to_move
    evaluated = []
    for move in position.legal_moves():
        successor = position.make_move(move)
        evaluated.append((move, successor, _score(evaluator(successor, perspective))))
    if not evaluated:
        return ()
    best = max(score for _, _, score in evaluated)
    candidates = []
    for move, successor, objective in evaluated:
        loss = best - objective
        if loss > margin_cp:
            continue
        replies = {reply.to_uci(): reply for reply in successor.legal_moves()}
        if replies:
            probabilities = dict(reply_model(successor, opponent_rating))
            if probabilities.keys() != replies.keys():
                raise ValueError("reply probabilities must cover exactly all legal replies")
            probabilities = {key: _score(value) for key, value in probabilities.items()}
            if any(value < 0 or value > 1 for value in probabilities.values()):
                raise ValueError("reply probabilities must be between zero and one")
            if not isclose(fsum(probabilities.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("reply probabilities must sum to one")
            expected = _score(fsum(
                probability * _score(evaluator(successor.make_move(replies[key]), perspective))
                for key, probability in probabilities.items() if probability > 0
            ))
        else:
            expected = objective
        candidates.append(PracticalCandidate(move, objective, expected, expected - objective, loss, len(replies)))
    return tuple(sorted(candidates, key=lambda item: (-item.expected_cp, -item.objective_cp, item.move.to_uci())))
