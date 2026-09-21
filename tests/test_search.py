import unittest

from trickfish.search import MATE_SCORE, search
from trickfish.position import Position


class SearchTest(unittest.TestCase):
    def test_search_captures_hanging_rook(self) -> None:
        position = Position.from_fen("6k1/8/8/8/8/8/3r4/K2Q4 w - - 0 1")
        result = search(position, 1)
        self.assertEqual(result.best_move.to_uci(), "d1d2")
        self.assertEqual(result.score, 900)
        self.assertEqual(result.principal_variation[0], result.best_move)

    def test_search_reports_checkmate(self) -> None:
        position = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        result = search(position, 2)
        self.assertIsNone(result.best_move)
        self.assertEqual(result.score, -MATE_SCORE)
        self.assertEqual(result.nodes, 1)

    def test_search_rejects_negative_depth(self) -> None:
        position = Position.from_fen("7k/8/8/8/8/8/8/K7 w - - 0 1")
        with self.assertRaises(ValueError):
            search(position, -1)

    def test_quiescence_rejects_a_defended_capture(self) -> None:
        position = Position.from_fen("3q2k1/8/8/8/8/8/3r4/K2Q4 w - - 0 1")
        result = search(position, 1)
        self.assertNotEqual(result.best_move.to_uci(), "d1d2")
        self.assertEqual(result.score, -500)


if __name__ == "__main__":
    unittest.main()
