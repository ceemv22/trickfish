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

    def pseudo_legal_rook_moves(self) -> tuple[Move, ...]:
        rook = "R" if self.side_to_move == "w" else "r"
        return self._pseudo_legal_sliding_moves(
            rook, ((-1, 0), (0, -1), (0, 1), (1, 0))
        )

    def pseudo_legal_queen_moves(self) -> tuple[Move, ...]:
        queen = "Q" if self.side_to_move == "w" else "q"
        return self._pseudo_legal_sliding_moves(
            queen,
            (
                (-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1),
            ),
        )

    def pseudo_legal_king_moves(self) -> tuple[Move, ...]:
        king = "K" if self.side_to_move == "w" else "k"
        moves: list[Move] = []
        for source, piece in enumerate(self.board):
            if piece != king:
                continue
            rank, file = divmod(source, 8)
            for rank_offset, file_offset in (
                (-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1),
            ):
                target_rank = rank + rank_offset
                target_file = file + file_offset
                if not (0 <= target_rank < 8 and 0 <= target_file < 8):
                    continue
                target = target_rank * 8 + target_file
                occupant = self.board[target]
                if occupant is not None and (
                    occupant.isupper() == king.isupper() or occupant.lower() == "k"
                ):
                    continue
                moves.append(Move(source, target))
        return tuple(moves) + self.pseudo_legal_castling_moves()

    def pseudo_legal_castling_moves(self) -> tuple[Move, ...]:
        if self.side_to_move == "w":
            return self._pseudo_legal_castling_moves_for_white()
        return self._pseudo_legal_castling_moves_for_black()

    def is_square_attacked(self, square: int, by_side: str) -> bool:
        if not 0 <= square < 64:
            raise ValueError("square must be between 0 and 63")
        if by_side not in {"w", "b"}:
            raise ValueError("side must be 'w' or 'b'")

        rank, file = divmod(square, 8)
        pawn = "P" if by_side == "w" else "p"
        pawn_rank = rank + 1 if by_side == "w" else rank - 1
        if 0 <= pawn_rank < 8:
            for pawn_file in (file - 1, file + 1):
                if 0 <= pawn_file < 8 and self.board[pawn_rank * 8 + pawn_file] == pawn:
                    return True

        knight = "N" if by_side == "w" else "n"
        for rank_offset, file_offset in (
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1),
        ):
            source_rank = rank + rank_offset
            source_file = file + file_offset
            if (
                0 <= source_rank < 8
                and 0 <= source_file < 8
                and self.board[source_rank * 8 + source_file] == knight
            ):
                return True

        king = "K" if by_side == "w" else "k"
        for rank_offset, file_offset in (
            (-1, -1), (-1, 0), (-1, 1), (0, -1),
            (0, 1), (1, -1), (1, 0), (1, 1),
        ):
            source_rank = rank + rank_offset
            source_file = file + file_offset
            if (
                0 <= source_rank < 8
                and 0 <= source_file < 8
                and self.board[source_rank * 8 + source_file] == king
            ):
                return True

        bishop_or_queen = "BQ" if by_side == "w" else "bq"
        if self._is_attacked_by_slider(
            rank,
            file,
            ((-1, -1), (-1, 1), (1, -1), (1, 1)),
            bishop_or_queen,
        ):
            return True

        rook_or_queen = "RQ" if by_side == "w" else "rq"
        return self._is_attacked_by_slider(
            rank,
            file,
            ((-1, 0), (0, -1), (0, 1), (1, 0)),
            rook_or_queen,
        )

    def _is_attacked_by_slider(
        self,
        rank: int,
        file: int,
        directions: tuple[tuple[int, int], ...],
        attackers: str,
    ) -> bool:
        for rank_step, file_step in directions:
            source_rank = rank + rank_step
            source_file = file + file_step
            while 0 <= source_rank < 8 and 0 <= source_file < 8:
                occupant = self.board[source_rank * 8 + source_file]
                if occupant is not None:
                    if occupant in attackers:
                        return True
                    break
                source_rank += rank_step
                source_file += file_step
        return False

    def _pseudo_legal_castling_moves_for_white(self) -> tuple[Move, ...]:
        moves: list[Move] = []
        if self.board[60] != "K":
            return tuple(moves)
        if (
            "K" in self.castling
            and self.board[63] == "R"
            and self.board[61] is None
            and self.board[62] is None
        ):
            moves.append(Move(60, 62, castling=True))
        if (
            "Q" in self.castling
            and self.board[56] == "R"
            and self.board[57] is None
            and self.board[58] is None
            and self.board[59] is None
        ):
            moves.append(Move(60, 58, castling=True))
        return tuple(moves)

    def _pseudo_legal_castling_moves_for_black(self) -> tuple[Move, ...]:
        moves: list[Move] = []
        if self.board[4] != "k":
            return tuple(moves)
        if (
            "k" in self.castling
            and self.board[7] == "r"
            and self.board[5] is None
            and self.board[6] is None
        ):
            moves.append(Move(4, 6, castling=True))
        if (
            "q" in self.castling
            and self.board[0] == "r"
            and self.board[1] is None
            and self.board[2] is None
            and self.board[3] is None
        ):
            moves.append(Move(4, 2, castling=True))
        return tuple(moves)

    def pseudo_legal_pawn_moves(self) -> tuple[Move, ...]:
        pawn = "P" if self.side_to_move == "w" else "p"
        rank_step = -1 if self.side_to_move == "w" else 1
        starting_rank = 6 if self.side_to_move == "w" else 1
        en_passant_target = (
            self._square_index(self.en_passant) if self.en_passant is not None else None
        )
        moves: list[Move] = []
        for source, piece in enumerate(self.board):
            if piece != pawn:
                continue
            rank, file = divmod(source, 8)
            target_rank = rank + rank_step
            if not 0 <= target_rank < 8:
                continue
            forward = target_rank * 8 + file
            if self.board[forward] is None:
                self._append_pawn_move(moves, source, forward)
                if rank == starting_rank:
                    double_target_rank = rank + 2 * rank_step
                    double_target = double_target_rank * 8 + file
                    if self.board[double_target] is None:
                        moves.append(Move(source, double_target))
            for file_offset in (-1, 1):
                target_file = file + file_offset
                if not 0 <= target_file < 8:
                    continue
                target = target_rank * 8 + target_file
                occupant = self.board[target]
                if (
                    occupant is not None
                    and occupant.isupper() != pawn.isupper()
                    and occupant.lower() != "k"
                ):
                    self._append_pawn_move(moves, source, target)
                elif target == en_passant_target and occupant is None:
                    captured_square = rank * 8 + target_file
                    captured_pawn = "p" if pawn == "P" else "P"
                    if self.board[captured_square] == captured_pawn:
                        moves.append(Move(source, target, en_passant=True))
        return tuple(moves)

    def _append_pawn_move(self, moves: list[Move], source: int, target: int) -> None:
        if target // 8 in {0, 7}:
            moves.extend(Move(source, target, promotion) for promotion in "qrbn")
        else:
            moves.append(Move(source, target))

    def _square_index(self, square: str) -> int:
        return (8 - int(square[1])) * 8 + FILES.index(square[0])

    def pseudo_legal_moves(self) -> tuple[Move, ...]:
        return (
            self.pseudo_legal_knight_moves()
            + self.pseudo_legal_bishop_moves()
            + self.pseudo_legal_rook_moves()
            + self.pseudo_legal_queen_moves()
            + self.pseudo_legal_king_moves()
            + self.pseudo_legal_pawn_moves()
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
