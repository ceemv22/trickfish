import unittest

from trickfish.position import Position, STARTING_FEN
from trickfish.variation import replay_uci_line


class VariationTests(unittest.TestCase):
    def test_opening_line_and_root_restoration(self):
        root = Position.from_fen(STARTING_FEN)
        final = replay_uci_line(root, ["e2e4", "e7e5", "g1f3"])
        self.assertEqual(final.to_fen(), "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2")
        self.assertEqual(root.to_fen(), STARTING_FEN)

    def test_special_move_flags_survive_uci_resolution(self):
        cases = [
            ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", ["e5d6"], "4k3/8/3P4/8/8/8/8/4K3 b - - 0 1"),
            ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", ["e1g1", "e8c8"], "2kr3r/8/8/8/8/8/8/R4RK1 w - - 2 2"),
            ("7k/P7/8/8/8/8/8/7K w - - 0 1", ["a7a8n"], "N6k/8/8/8/8/8/8/7K b - - 0 1"),
        ]
        for fen, moves, expected in cases:
            with self.subTest(moves=moves):
                root = Position.from_fen(fen)
                self.assertEqual(replay_uci_line(root, moves).to_fen(), expected)
                self.assertEqual(root.to_fen(), fen)

    def test_illegal_tail_and_move_after_terminal_position_fail(self):
        with self.assertRaises(ValueError):
            replay_uci_line(Position.from_fen(STARTING_FEN), ["e2e4", "e2e5"])
        mate = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        with self.assertRaises(ValueError):
            replay_uci_line(mate, ["h8h7"])


if __name__ == "__main__":
    unittest.main()
