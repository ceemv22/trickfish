import unittest

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


if __name__ == "__main__":
    unittest.main()
