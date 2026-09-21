from dataclasses import dataclass

from .move import Move
from .position import Position


@dataclass(frozen=True)
class GameHistory:
    positions: tuple[Position, ...]

    @classmethod
    def begin(cls, position: Position) -> "GameHistory":
        return cls((position,))

    @property
    def current(self) -> Position:
        return self.positions[-1]

    def play(self, move: Move) -> "GameHistory":
        return GameHistory(self.positions + (self.current.make_move(move),))

    def repetition_count(self) -> int:
        current_key = self.current.zobrist_key
        return sum(position.zobrist_key == current_key for position in self.positions)

    def can_claim_threefold_repetition(self) -> bool:
        return self.repetition_count() >= 3
