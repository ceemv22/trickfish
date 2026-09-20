from __future__ import annotations

from dataclasses import dataclass

from .move import Move

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
PIECES = frozenset("prnbqkPRNBQK")
FILES = "abcdefgh"
RANKS = "12345678"


class FenError(ValueError):
    pass


@dataclass(frozen=True)
class Position:
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

    def pseudo_legal_knight_moves(self) -> tuple[Move, ...]:
        knight = "N" if self.side_to_move == "w" else "n"
        offsets = ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
                   (1, -2), (1, 2), (2, -1), (2, 1))
        moves: list[Move] = []
        for source, piece in enumerate(self.board):
            if piece != knight:
                continue
            rank, file = divmod(source, 8)
            for rank_offset, file_offset in offsets:
                target_rank = rank + rank_offset
                target_file = file + file_offset
                if not (0 <= target_rank < 8 and 0 <= target_file < 8):
                    continue
                target = target_rank * 8 + target_file
                occupant = self.board[target]
                if occupant is not None and (
                    occupant.isupper() == knight.isupper() or occupant.lower() == "k"
                ):
                    continue
                moves.append(Move(source, target))
        return tuple(moves)

    def pseudo_legal_bishop_moves(self) -> tuple[Move, ...]:
        bishop = "B" if self.side_to_move == "w" else "b"
        return self._pseudo_legal_sliding_moves(
            bishop, ((-1, -1), (-1, 1), (1, -1), (1, 1))
        )

    def _pseudo_legal_sliding_moves(
        self, piece: str, directions: tuple[tuple[int, int], ...]
    ) -> tuple[Move, ...]:
        moves: list[Move] = []
        for source, occupant in enumerate(self.board):
            if occupant != piece:
                continue
            rank, file = divmod(source, 8)
            for rank_step, file_step in directions:
                target_rank = rank + rank_step
                target_file = file + file_step
                while 0 <= target_rank < 8 and 0 <= target_file < 8:
                    target = target_rank * 8 + target_file
                    target_occupant = self.board[target]
                    if target_occupant is not None:
                        if (
                            target_occupant.isupper() != piece.isupper()
                            and target_occupant.lower() != "k"
                        ):
                            moves.append(Move(source, target))
                        break
                    moves.append(Move(source, target))
                    target_rank += rank_step
                    target_file += file_step
        return tuple(moves)

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
