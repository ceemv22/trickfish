import unittest

from trickfish.objective_score import ObjectiveScore
from trickfish.position import Position, STARTING_FEN
from trickfish.practical_analysis import analyze_practical_moves


class TypedPracticalTests(unittest.TestCase):
    def setUp(self):
        self.position = Position.from_fen(STARTING_FEN)
        self.children = {move.to_uci(): self.position.make_move(move) for move in self.position.legal_moves()}
        self.scores = {child.to_fen(): ObjectiveScore(cp=-100) for child in self.children.values()}
        self.scores[self.children["e2e4"].to_fen()] = ObjectiveScore(cp=10)
        self.scores[self.children["d2d4"].to_fen()] = ObjectiveScore(cp=0)

    def evaluate(self, position, perspective):
        self.assertEqual(perspective, "w")
        return self.scores.get(position.to_fen(), ObjectiveScore(cp=20))

    def model(self, position, rating):
        return {move.to_uci(): float(index == 0) for index, move in enumerate(position.legal_moves())}

    def test_losing_mate_root_is_excluded_without_breaking_cp_comparison(self):
        self.scores[self.children["f2f3"].to_fen()] = ObjectiveScore(mate_moves=2, winning=False)
        result = analyze_practical_moves(self.position, self.evaluate, self.model, 1500)
        self.assertEqual(result["selection_basis"], "expected_cp")
        self.assertEqual(result["selection"], "e2e4")
        self.assertNotIn("f2f3", [item["move"] for item in result["candidates"]])
        self.assertEqual(len(result["root_evaluations"]), 20)

    def test_forced_win_prefers_shortest_mate_and_does_not_query_human_model(self):
        self.scores[self.children["e2e4"].to_fen()] = ObjectiveScore(mate_moves=3, winning=True)
        self.scores[self.children["d2d4"].to_fen()] = ObjectiveScore(mate_moves=1, winning=True)

        def forbidden(*args):
            self.fail("objective mate selection must not call the reply model")

        result = analyze_practical_moves(self.position, self.evaluate, forbidden, 1500)
        self.assertEqual(result["selection"], "d2d4")
        self.assertEqual(result["selection_basis"], "objective_mate_win")
        self.assertIsNone(result["candidates"][0]["expected_cp"])

    def test_all_losing_mates_choose_longest_reported_distance(self):
        for index, child in enumerate(self.children.values()):
            self.scores[child.to_fen()] = ObjectiveScore(mate_moves=index + 1, winning=False)
        result = analyze_practical_moves(self.position, self.evaluate, self.model, 1500)
        self.assertEqual(result["selection"], list(self.children)[-1])
        self.assertEqual(result["selection_basis"], "objective_mate_loss_delay")

    def test_mixed_reply_outcomes_have_no_fake_cp_expectation(self):
        child = self.children["d2d4"]
        moves = child.legal_moves()
        self.scores[child.make_move(moves[0]).to_fen()] = ObjectiveScore(mate_moves=2, winning=True)
        self.scores[child.make_move(moves[1]).to_fen()] = ObjectiveScore(cp=60)

        def half(position, rating):
            return {move.to_uci(): 0.5 if index < 2 else 0 for index, move in enumerate(position.legal_moves())}

        result = analyze_practical_moves(self.position, self.evaluate, half, 1500)
        self.assertEqual(result["selection_basis"], "objective_fallback_mixed_scores")
        self.assertEqual(result["selection"], "e2e4")
        mixed = next(item for item in result["candidates"] if item["move"] == "d2d4")
        self.assertIsNone(mixed["expected_cp"])
        self.assertIsNone(mixed["trap_cp"])
        self.assertEqual((mixed["cp_component"], mixed["mate_win_probability"], mixed["mate_loss_probability"]), (30, 0.5, 0))

    def test_zero_probability_mate_does_not_contaminate_cp_expectation(self):
        child = self.children["d2d4"]
        self.scores[child.make_move(child.legal_moves()[1]).to_fen()] = ObjectiveScore(mate_moves=1, winning=False)
        result = analyze_practical_moves(self.position, self.evaluate, self.model, 1500)
        self.assertEqual(result["selection_basis"], "expected_cp")

    def test_terminal_mate_zero_and_invalid_score_types(self):
        terminal = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        result = analyze_practical_moves(terminal, lambda p, side: ObjectiveScore(mate_moves=0, winning=False), self.model, 1500)
        self.assertIsNone(result["selection"])
        self.assertFalse(result["terminal_score"]["winning"])
        self.assertTrue(ObjectiveScore(mate_moves=0, winning=False).inverted().winning)
        with self.assertRaises(ValueError):
            analyze_practical_moves(self.position, lambda p, side: 0, self.model, 1500)
        for values in ({}, {"cp": float("nan")}, {"cp": 3, "mate_moves": 1}, {"mate_moves": -1, "winning": True}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ObjectiveScore(**values)


if __name__ == "__main__":
    unittest.main()
