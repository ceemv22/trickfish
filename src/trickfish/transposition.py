from dataclasses import dataclass

from .move import Move

EXACT = "exact"
LOWER_BOUND = "lower"
UPPER_BOUND = "upper"


@dataclass(frozen=True)
class TranspositionEntry:
    depth: int
    score: int
    bound: str
    best_move: Move | None


class TranspositionTable:
    def __init__(self) -> None:
        self._entries: dict[int, TranspositionEntry] = {}
        self.hits = 0

    def probe(self, key: int) -> TranspositionEntry | None:
        entry = self._entries.get(key)
        if entry is not None:
            self.hits += 1
        return entry

    def store(self, key: int, entry: TranspositionEntry) -> None:
        current = self._entries.get(key)
        if current is None or entry.depth >= current.depth:
            self._entries[key] = entry

    def __len__(self) -> int:
        return len(self._entries)
