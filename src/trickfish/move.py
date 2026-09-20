from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    from_square: int
    to_square: int
    promotion: str | None = None
    en_passant: bool = False
    castling: bool = False

    def __post_init__(self) -> None:
        if not (0 <= self.from_square < 64 and 0 <= self.to_square < 64):
            raise ValueError("squares must be between 0 and 63")
        if self.from_square == self.to_square:
            raise ValueError("source and destination must differ")
        if self.promotion is not None and self.promotion not in {"q", "r", "b", "n"}:
            raise ValueError("promotion must be q, r, b, or n")

    def to_uci(self) -> str:
        coordinates = "".join(
            f"{'abcdefgh'[square % 8]}{8 - square // 8}"
            for square in (self.from_square, self.to_square)
        )
        return coordinates + (self.promotion or "")
