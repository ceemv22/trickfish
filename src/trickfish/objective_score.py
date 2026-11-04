from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ObjectiveScore:
    cp: float | None = None
    mate_moves: int | None = None
    winning: bool | None = None

    def __post_init__(self):
        if self.cp is not None:
            if type(self.cp) not in (int, float) or not isfinite(self.cp) or self.mate_moves is not None or self.winning is not None:
                raise ValueError("invalid centipawn score")
        elif type(self.mate_moves) is not int or self.mate_moves < 0 or type(self.winning) is not bool:
            raise ValueError("mate requires nonnegative distance and an explicit winner")

    def inverted(self):
        if self.cp is not None:
            return ObjectiveScore(cp=-self.cp)
        return ObjectiveScore(mate_moves=self.mate_moves, winning=not self.winning)

    def as_dict(self):
        return {"kind": "cp" if self.cp is not None else "mate", "cp": self.cp,
                "mate_moves": self.mate_moves, "winning": self.winning}
