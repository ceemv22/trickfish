"""Chess position representation and Forsyth-Edwards Notation parsing."""

from __future__ import annotations

from dataclasses import dataclass

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
PIECES = frozenset("prnbqkPRNBQK")
FILES = "abcdefgh"
RANKS = "12345678"


class FenError(ValueError):
    """Raised when a FEN string does not describe a valid board state."""


@dataclass(frozen=True)
class Position:
    """An immutable chess position, before move generation is added."""

    board: tuple[str | None, ...]
    side_to_move: str
    castling: str
    en_passant: str | None
    halfmove_clock: int
    fullmove_number: int

    @classmethod
    def from_fen(cls, fen: str) -> "Position":
        fields = fen.split()
        if len(fields) != 6:
            raise FenError("FEN must contain exactly six fields")

        board = _parse_board(fields[0])
        side_to_move = fields[1]
        if side_to_move not in {"w", "b"}:
            raise FenError("active color must be 'w' or 'b'")

        castling = fields[2]
        if castling != "-":
            if not castling or any(right not in "KQkq" for right in castling):
                raise FenError("castling field must use KQkq or '-'")
            if len(set(castling)) != len(castling):
                raise FenError("castling field must not repeat a right")

        en_passant = None if fields[3] == "-" else fields[3]
        if en_passant is not None and (
            len(en_passant) != 2
            or en_passant[0] not in FILES
            or en_passant[1] not in "36"
        ):
            raise FenError("en passant square must be '-' or a square on rank 3 or 6")

        try:
            halfmove_clock = int(fields[4])
            fullmove_number = int(fields[5])
        except ValueError as error:
            raise FenError("move counters must be integers") from error
        if halfmove_clock < 0:
            raise FenError("halfmove clock must not be negative")
        if fullmove_number < 1:
            raise FenError("fullmove number must be at least one")

        return cls(board, side_to_move, castling, en_passant, halfmove_clock, fullmove_number)

    def to_fen(self) -> str:
        rows: list[str] = []
        for rank in range(8):
            empty_squares = 0
            row = ""
            for file in range(8):
                piece = self.board[rank * 8 + file]
                if piece is None:
                    empty_squares += 1
                else:
                    if empty_squares:
                        row += str(empty_squares)
                        empty_squares = 0
                    row += piece
            if empty_squares:
                row += str(empty_squares)
            rows.append(row)
        return " ".join(
            [
                "/".join(rows),
                self.side_to_move,
                self.castling,
                self.en_passant or "-",
                str(self.halfmove_clock),
                str(self.fullmove_number),
            ]
        )

    def render(self) -> str:
        lines = []
        for rank in range(8):
            pieces = [self.board[rank * 8 + file] or "." for file in range(8)]
            lines.append(f"{8 - rank}  {' '.join(pieces)}")
        lines.append("")
        lines.append("   a b c d e f g h")
        return "\n".join(lines)


def _parse_board(field: str) -> tuple[str | None, ...]:
    ranks = field.split("/")
    if len(ranks) != 8:
        raise FenError("piece placement must contain eight ranks")

    board: list[str | None] = []
    for rank in ranks:
        squares: list[str | None] = []
        for symbol in rank:
            if symbol.isdigit():
                if symbol not in "12345678":
                    raise FenError("empty-square count must be between 1 and 8")
                squares.extend([None] * int(symbol))
            elif symbol in PIECES:
                squares.append(symbol)
            else:
                raise FenError(f"invalid piece symbol: {symbol!r}")
        if len(squares) != 8:
            raise FenError("each rank must describe exactly eight squares")
        board.extend(squares)

    if board.count("K") != 1 or board.count("k") != 1:
        raise FenError("position must contain exactly one king of each color")
    return tuple(board)
