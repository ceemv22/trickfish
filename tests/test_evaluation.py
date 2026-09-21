import unittest

from trickfish.evaluation import MATE_SCORE, evaluate, evaluate_for_side_to_move
from trickfish.position import STARTING_FEN, Position


class EvaluationTest(unittest.TestCase):
    def test_starting_position_is_equal(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        self.assertEqual(evaluate(position), 0)
        self.assertEqual(evaluate_for_side_to_move(position), 0)

    def test_material_values_are_from_white_perspective(self) -> None:
        white_queen = Position.from_fen("7k/8/8/8/8/8/8/KQ6 w - - 0 1")
        black_queen = Position.from_fen("q6k/8/8/8/8/8/8/K7 w - - 0 1")
        self.assertEqual(evaluate(white_queen), 900)
        self.assertEqual(evaluate(black_queen), -900)

    def test_side_to_move_view_negates_black_score(self) -> None:
        position = Position.from_fen("7k/8/8/8/8/8/8/KQ6 b - - 0 1")
        self.assertEqual(evaluate(position), 900)
        self.assertEqual(evaluate_for_side_to_move(position), -900)

    def test_terminal_scores(self) -> None:
        checkmate = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        insufficient = Position.from_fen("7k/8/8/8/8/8/8/KB6 w - - 0 1")
        self.assertEqual(evaluate(checkmate), MATE_SCORE)
        self.assertEqual(evaluate(insufficient), 0)


if __name__ == "__main__":
    unittest.main()
