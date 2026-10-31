import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import search_benchmark as benchmark
from trickfish.position import Position

FEN = "8/8/7Q/8/K7/8/8/k7 w - - 0 1"


class MateObjectiveTests(unittest.TestCase):
    def test_forced_two_requires_all_defender_replies_and_has_no_mate_in_one(self):
        self.assertEqual(benchmark.forced_mate_moves(FEN, 1), ())
        self.assertEqual(benchmark.forced_mate_moves(FEN, 2), ("a4b3",))
        position = Position.from_fen(FEN)
        move = next(move for move in position.legal_moves() if move.to_uci() == "a4b3")
        child = position.make_move(move)
        self.assertGreater(len(child.legal_moves()), 0)
        for reply in child.legal_moves():
            self.assertTrue(benchmark.forced_mate_moves(child.make_move(reply).to_fen(), 1))

    def test_wrong_move_short_claim_even_distance_and_nonmate_scores_are_rejected(self):
        case = {"id": "forced-two", "fen": FEN, "expect": {"mate_in": 2}}
        benchmark.validate_objective(case, {"bestmove": "a4b3", "score": 99997})
        for move, score in (("a4b3", 99999), ("a4b3", 99998), ("a4b3", 99995),
                ("a4b3", 900), ("h6h7", 99997)):
            with self.assertRaises(ValueError):
                benchmark.validate_objective(case, {"bestmove": move, "score": score})

    def test_cooperative_mate_is_rejected_when_another_defense_escapes(self):
        fen = "8/3Q4/8/8/8/8/7k/4K3 w - - 0 1"
        root = Position.from_fen(fen)
        move = next(move for move in root.legal_moves() if move.to_uci() == "e1f1")
        child = root.make_move(move)
        outcomes = {reply.to_uci(): bool(benchmark.forced_mate_moves(child.make_move(reply).to_fen(), 1))
            for reply in child.legal_moves()}
        self.assertEqual(outcomes, {"h2g3": False, "h2h1": True})
        self.assertNotIn("e1f1", benchmark.forced_mate_moves(fen, 2))

    def test_stalemate_dead_material_and_automatic_draw_are_not_mate_proofs(self):
        for fen in ("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "7k/8/8/8/8/8/8/4K3 w - - 0 1",
                FEN.replace(" 0 1", " 150 1")):
            self.assertEqual(benchmark.forced_mate_moves(fen, 2), ())
        mate = "7k/8/5KQ1/8/8/8/8/8 w - - 149 1"
        self.assertIn("g6g7", benchmark.forced_mate_moves(mate, 1))

    def test_invalid_objectives_and_nonwinning_declared_moves_fail_before_execution(self):
        benchmark.forced_mate_moves(FEN, 1)
        for value in (True, 0, -1, 3, 1.5, "2"):
            with self.assertRaises(ValueError):
                benchmark.validate_objective({"id": "invalid", "fen": FEN, "expect": {"mate_in": value}})
        with self.assertRaises(ValueError):
            benchmark.validate_objective({"id": "invalid", "fen": FEN, "expect": {"mate_in": 2, "bestmoves": ["h6h7"]}})
        with self.assertRaises(ValueError):
            benchmark.validate_objective({"id": "invalid", "fen": FEN, "expect": {"mate_in": 2, "mate_in_one": True}})

    def test_extended_suite_objectives_are_proved_in_both_colors(self):
        suite = benchmark.load_suite(pathlib.Path(__file__).with_name("tactical_extended_suite.json"))
        forced = [case for case in suite["positions"] if "mate_in" in case["expect"]]
        self.assertEqual(len(forced), 16)
        self.assertEqual({Position.from_fen(case["fen"]).side_to_move for case in forced}, {"w", "b"})
        for case in forced:
            self.assertFalse(benchmark.forced_mate_moves(case["fen"], 1))


if __name__ == "__main__":
    unittest.main()
