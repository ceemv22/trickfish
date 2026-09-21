import unittest

from trickfish import Move
from trickfish.position import FenError, Position, STARTING_FEN


class PositionTest(unittest.TestCase):
    def test_starting_position_round_trips(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        self.assertEqual(position.to_fen(), STARTING_FEN)
        self.assertEqual(position.board[0], "r")
        self.assertEqual(position.board[63], "R")

    def test_position_with_en_passant_round_trips(self) -> None:
        fen = "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 2"
        self.assertEqual(Position.from_fen(fen).to_fen(), fen)

    def test_rejects_malformed_board(self) -> None:
        with self.assertRaises(FenError):
            Position.from_fen("8/8/8/8/8/8/8/9 w - - 0 1")

    def test_rejects_missing_king(self) -> None:
        with self.assertRaises(FenError):
            Position.from_fen("8/8/8/8/8/8/8/4K3 w - - 0 1")

    def test_pawn_double_step_sets_en_passant_and_preserves_original(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        next_position = position.make_move(Move(52, 36))
        self.assertEqual(position.to_fen(), STARTING_FEN)
        self.assertEqual(
            next_position.to_fen(),
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        )

    def test_black_move_increments_fullmove_number(self) -> None:
        position = Position.from_fen(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        )
        next_position = position.make_move(Move(12, 28))
        self.assertEqual(
            next_position.to_fen(),
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
        )

    def test_capture_and_promotion(self) -> None:
        capture_position = Position.from_fen("7k/8/8/3p4/4P3/8/8/K7 w - - 4 1")
        captured = capture_position.make_move(Move(36, 27))
        self.assertEqual(captured.to_fen(), "7k/8/8/3P4/8/8/8/K7 b - - 0 1")

        promotion_position = Position.from_fen("7k/3P4/8/8/8/8/8/K7 w - - 0 1")
        promoted = promotion_position.make_move(Move(11, 3, "q"))
        self.assertEqual(promoted.to_fen(), "3Q3k/8/8/8/8/8/8/K7 b - - 0 1")

    def test_en_passant_and_castling(self) -> None:
        en_passant_position = Position.from_fen("7k/8/8/3pP3/8/8/8/K7 w - d6 0 1")
        captured = en_passant_position.make_move(Move(28, 19, en_passant=True))
        self.assertEqual(captured.to_fen(), "7k/8/3P4/8/8/8/8/K7 b - - 0 1")

        castling_position = Position.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
        castled = castling_position.make_move(Move(60, 62, castling=True))
        self.assertEqual(castled.to_fen(), "4k3/8/8/8/8/8/8/R4RK1 b - - 1 1")

    def test_rook_move_and_rook_capture_update_castling_rights(self) -> None:
        position = Position.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
        moved_rook = position.make_move(Move(63, 55))
        self.assertEqual(moved_rook.castling, "Q")

        capture_position = Position.from_fen("4k2r/8/8/8/8/8/8/4K2R b KQkq - 0 1")
        captured_rook = capture_position.make_move(Move(7, 63))
        self.assertEqual(captured_rook.castling, "Qq")

    def test_make_move_rejects_invalid_source_and_king_capture(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        with self.assertRaises(ValueError):
            position.make_move(Move(16, 24))

        king_position = Position.from_fen("7k/8/8/8/4Q3/8/8/K7 w - - 0 1")
        with self.assertRaises(ValueError):
            king_position.make_move(Move(36, 7))


if __name__ == "__main__":
    unittest.main()
