import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
from castling_parity import fixtures, expected_divide, parse_divide


class CastlingFixtureTests(unittest.TestCase):
    def test_fixture_domains_and_independent_castling_boundaries(self):
        cases = dict(fixtures())
        self.assertEqual(len(cases), 84)
        self.assertEqual(len({position.to_fen() for position in cases.values()}), 84)
        for position in cases.values():
            defender = "b" if position.side_to_move == "w" else "w"
            self.assertFalse(position.is_square_attacked(position._king_square(defender), position.side_to_move))
        def castles(name):
            return {move.to_uci() for move in cases[name].legal_moves() if move.castling}
        self.assertEqual(castles("base-15-w"), {"e1g1", "e1c1"})
        self.assertEqual(castles("base-15-b"), {"e8g8", "e8c8"})
        self.assertEqual(castles("base-12-w"), set())
        self.assertEqual(castles("blocked-b-w"), {"e1g1"})
        self.assertEqual(castles("blocked-f-w"), {"e1c1"})
        self.assertEqual(castles("attack-b-w"), {"e1g1", "e1c1"})
        self.assertEqual(castles("attack-e-w"), set())
        self.assertEqual(castles("king-away-w"), set())
        self.assertEqual(castles("missing-rook-3-w"), set())
        for name in ("pawn-e2", "knight-e3", "knight-f3"):
            self.assertEqual(castles(name + "-w"), set())
        for name in ("knight-d2", "bishop-c4", "king-g2"):
            self.assertEqual(castles(name + "-w"), {"e1c1"})
            self.assertEqual(castles(name + "-b"), {"e8c8"})
        for name in ("bishop-h5", "king-b2"):
            self.assertEqual(castles(name + "-w"), {"e1g1"})
            self.assertEqual(castles(name + "-b"), {"e8g8"})

    def test_divide_parser_preserves_terminal_branches_and_rejects_corruption(self):
        self.assertEqual(parse_divide("e1g1 0\ne1c1 7\ntotal 7\n"), {"e1g1": 0, "e1c1": 7})
        for output in ("e1g1 1\ne1g1 1\ntotal 2", "e1g1 1\ntotal 0", "total -1", "e1g1 1"):
            with self.assertRaises(ValueError): parse_divide(output)
        start = dict(fixtures())["start-w"]
        self.assertEqual(sum(expected_divide(start).values()), 400)


if __name__ == "__main__":
    unittest.main()
