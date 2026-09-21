import unittest

from trickfish import GameHistory, Move
from trickfish.position import STARTING_FEN, Position


class GameHistoryTest(unittest.TestCase):
    def test_history_preserves_each_position(self) -> None:
        initial = Position.from_fen(STARTING_FEN)
        history = GameHistory.begin(initial)
        next_history = history.play(Move(62, 45))
        self.assertEqual(history.current, initial)
        self.assertEqual(history.positions, (initial,))
        self.assertEqual(next_history.current.to_fen(),
                         "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1")

    def test_threefold_repetition_requires_three_occurrences(self) -> None:
        history = GameHistory.begin(Position.from_fen(STARTING_FEN))
        cycle = (Move(62, 45), Move(6, 21), Move(45, 62), Move(21, 6))
        for move in cycle:
            history = history.play(move)
        self.assertEqual(history.repetition_count(), 2)
        self.assertFalse(history.can_claim_threefold_repetition())
        for move in cycle:
            history = history.play(move)
        self.assertEqual(history.repetition_count(), 3)
        self.assertTrue(history.can_claim_threefold_repetition())

    def test_fifty_and_seventy_five_move_thresholds(self) -> None:
        claimable = GameHistory.begin(
            Position.from_fen("7k/8/8/8/8/8/8/K7 w - - 100 51")
        )
        automatic = GameHistory.begin(
            Position.from_fen("7k/8/8/8/8/8/8/K7 w - - 150 76")
        )
        self.assertTrue(claimable.can_claim_fifty_move_draw())
        self.assertFalse(claimable.is_automatic_seventy_five_move_draw())
        self.assertTrue(automatic.can_claim_fifty_move_draw())
        self.assertTrue(automatic.is_automatic_seventy_five_move_draw())

    def test_insufficient_material_draws(self) -> None:
        cases = (
            "7k/8/8/8/8/8/8/K7 w - - 0 1",
            "7k/8/8/8/8/8/8/KB6 w - - 0 1",
            "7k/8/8/8/8/8/8/KN6 w - - 0 1",
            "5b1k/8/8/8/8/8/8/K1B5 w - - 0 1",
        )
        for fen in cases:
            with self.subTest(fen=fen):
                history = GameHistory.begin(Position.from_fen(fen))
                self.assertTrue(history.is_draw_by_insufficient_material())

    def test_sufficient_material_is_not_a_draw(self) -> None:
        cases = (
            "7k/8/8/8/8/8/8/KQ6 w - - 0 1",
            "7k/8/8/8/8/8/8/KBB5 w - - 0 1",
            "7k/8/8/8/8/8/8/KBN5 w - - 0 1",
            "5b1k/8/8/8/8/8/8/K2B4 w - - 0 1",
        )
        for fen in cases:
            with self.subTest(fen=fen):
                history = GameHistory.begin(Position.from_fen(fen))
                self.assertFalse(history.is_draw_by_insufficient_material())


if __name__ == "__main__":
    unittest.main()
