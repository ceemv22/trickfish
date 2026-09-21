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


if __name__ == "__main__":
    unittest.main()
