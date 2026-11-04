import unittest

from trickfish.position import Position, STARTING_FEN
from trickfish.practical import rank_practical_moves


class PracticalTests(unittest.TestCase):
    def setUp(self):
        self.position = Position.from_fen(STARTING_FEN)
        self.children = {move.to_uci(): self.position.make_move(move) for move in self.position.legal_moves()}
        self.root_scores = {child.to_fen(): -100 for child in self.children.values()}
        self.root_scores[self.children["e2e4"].to_fen()] = 20
        self.root_scores[self.children["d2d4"].to_fen()] = 0

    def evaluate(self, position, perspective):
        self.assertEqual(perspective, self.position.side_to_move)
        if position.to_fen() in self.root_scores:
            return self.root_scores[position.to_fen()]
        return 20 if position.board[36] == "P" else 100

    def uniform(self, position, rating):
        self.assertEqual(rating, 1500)
        moves = position.legal_moves()
        return {move.to_uci(): 1 / len(moves) for move in moves}

    def test_expected_value_can_choose_second_best_within_margin(self):
        ranked = rank_practical_moves(self.position, self.evaluate, self.uniform, 1500, 20)
        self.assertEqual([item.move.to_uci() for item in ranked], ["d2d4", "e2e4"])
        self.assertEqual((ranked[0].expected_cp, ranked[0].trap_cp, ranked[0].objective_loss_cp), (100, 100, 20))
        strict = rank_practical_moves(self.position, self.evaluate, self.uniform, 1500, 19)
        self.assertEqual([item.move.to_uci() for item in strict], ["e2e4"])
        self.assertEqual(self.position.to_fen(), STARTING_FEN)

    def test_obvious_defense_removes_speculative_gain(self):
        def defense(position, rating):
            return {move.to_uci(): float(index == 0) for index, move in enumerate(position.legal_moves())}

        def evaluate(position, perspective):
            if position.to_fen() in self.root_scores:
                return self.evaluate(position, perspective)
            return 20 if position.board[36] == "P" else 0

        ranked = rank_practical_moves(self.position, evaluate, defense, 1500)
        self.assertEqual(ranked[0].move.to_uci(), "e2e4")
        self.assertEqual(ranked[1].trap_cp, 0)

    def test_rejects_missing_illegal_and_invalid_probability_mass(self):
        for model in (
            lambda position, rating: {},
            lambda position, rating: {"e1e8": 1},
            lambda position, rating: {move.to_uci(): 0 for move in position.legal_moves()},
            lambda position, rating: {move.to_uci(): float("nan") for move in position.legal_moves()},
            lambda position, rating: {move.to_uci(): -1 for move in position.legal_moves()},
        ):
            with self.subTest(model=model), self.assertRaises(ValueError):
                rank_practical_moves(self.position, self.evaluate, model, 1500)

    def test_black_root_perspective_is_preserved(self):
        self.position = Position.from_fen(STARTING_FEN.replace(" w ", " b "))
        calls = []

        def evaluator(position, perspective):
            calls.append(perspective)
            return 0

        ranked = rank_practical_moves(self.position, evaluator, self.uniform, 1500)
        self.assertEqual(len(ranked), 20)
        self.assertEqual(set(calls), {"b"})

    def test_terminal_root_and_nonfinite_evaluation(self):
        terminal = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        self.assertEqual(rank_practical_moves(terminal, self.evaluate, self.uniform, 1500), ())
        with self.assertRaises(ValueError):
            rank_practical_moves(self.position, lambda position, perspective: float("inf"), self.uniform, 1500)

    def test_no_reply_candidate_does_not_call_model(self):
        position = Position.from_fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")

        def evaluate(position, perspective):
            return 100 if position.game_status() == "checkmate" else -100

        def forbidden(position, rating):
            self.fail("mate candidates must not query the reply model")

        ranked = rank_practical_moves(position, evaluate, forbidden, 1500, 0)
        self.assertTrue(ranked)
        self.assertTrue(all(item.expected_cp == 100 and item.replies == 0 for item in ranked))


if __name__ == "__main__":
    unittest.main()
