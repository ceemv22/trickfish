from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    from_square: int
    to_square: int

    def __post_init__(self) -> None:
        if not (0 <= self.from_square < 64 and 0 <= self.to_square < 64):
            raise ValueError("squares must be between 0 and 63")
        if self.from_square == self.to_square:
            raise ValueError("source and destination must differ")

    def to_uci(self) -> str:
        return "".join(
            f"{'abcdefgh'[square % 8]}{8 - square // 8}"
            for square in (self.from_square, self.to_square)
        )
