import copy
import unittest

from trickfish.objective_score import ObjectiveScore
from trickfish.position import Position, STARTING_FEN
from trickfish.practical_pgn import render_practical_pgn


class PracticalPgnTests(unittest.TestCase):
    def report(self, black=False):
        fen = STARTING_FEN.replace(" w ", " b ") if black else STARTING_FEN
        position = Position.from_fen(fen)
        score = ObjectiveScore(cp=0).as_dict()
        move = "e7e5" if black else "e2e4"
        replies = [("e2e4", ["g8f6"]), ("g1f3", ["b8c6"])] if black else [("c7c5", ["g1f3"]), ("e7e5", ["f1c4"])]
        return {"schema": "trickfish.practical-analysis.v2", "fen": fen, "perspective": position.side_to_move,
                "margin_cp": 30, "opponent_rating": 1500, "selection": move, "selection_basis": "expected_cp",
                "objective": {"depth": 4, "executable_sha256": "fixture", "identity": ["fixture engine"], "options": "default"},
                "reply_model": {"source": "synthetic policy", "sha256": "fixture", "rating": 1500, "positions": {}},
                "root_evaluations": [{"move": item.to_uci(), "score": copy.deepcopy(score)} for item in position.legal_moves()],
                "candidates": [{"move": move, "objective": score, "expected_cp": 0,
                                "objective_pv": [replies[0][0], *replies[0][1]],
                                "reply_details": [{"move": reply, "probability": probability, "score": score, "pv": pv}
                                                  for (reply, pv), probability in zip(replies, (0.75, 0.25))]}]}

    def test_analysis_lines_have_fen_san_original_mass_and_unfinished_result(self):
        text = render_practical_pgn(self.report(), max_replies=1)
        self.assertEqual(text.count('[Result "*"]'), 2)
        self.assertIn('[SetUp "1"]', text)
        self.assertIn('1. e4 c5 2. Nf3 *', text)
        self.assertIn('[TrickfishProbability "0.75"]', text)
        self.assertIn('[TrickfishExportedReplyMass "0.75"]', text)
        self.assertNotIn('[TrickfishReply "e7e5"]', text)
        self.assertIn('not an observed game result', text)

    def test_black_root_numbering_and_tag_escaping(self):
        report = self.report(black=True)
        report["reply_model"]["source"] = 'fixture"\n[Result "1-0"]'
        text = render_practical_pgn(report, 0)
        self.assertIn('1... e5 2. e4 Nf6 *', text)
        self.assertEqual(text.count('[Result "*"]'), 1)
        self.assertNotIn('\n[Result "1-0"]', text)
        self.assertIn('[TrickfishPerspective "b"]', text)

    def test_illegal_unexported_tail_is_not_hidden_by_reply_limit(self):
        report = self.report()
        report["candidates"][0]["reply_details"][1]["pv"] = ["e2e3"]
        with self.assertRaises(ValueError):
            render_practical_pgn(report, 1)

    def test_missing_continuations_and_duplicate_replies_fail(self):
        report = self.report()
        del report["candidates"][0]["objective_pv"]
        with self.assertRaises(ValueError):
            render_practical_pgn(report)
        report = self.report()
        report["candidates"][0]["reply_details"].append(copy.deepcopy(report["candidates"][0]["reply_details"][0]))
        with self.assertRaises(ValueError):
            render_practical_pgn(report)

    def test_mate_outcome_remains_typed_and_does_not_claim_a_game_win(self):
        report = self.report()
        report["selection_basis"] = "objective_fallback_mixed_scores"
        report["candidates"][0]["expected_cp"] = None
        report["candidates"][0]["reply_details"][0]["score"] = ObjectiveScore(mate_moves=3, winning=True).as_dict()
        text = render_practical_pgn(report)
        self.assertIn('[TrickfishReplyOutcome "mate-win 3"]', text)
        self.assertIn('[TrickfishExpectedCP "unavailable"]', text)
        self.assertNotIn('[Result "1-0"]', text)

    def test_terminal_diagram_exports_without_inventing_played_moves(self):
        report = self.report()
        report.update(fen="7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", perspective="b", selection=None,
                      selection_basis="terminal", root_evaluations=[], candidates=[],
                      terminal_score=ObjectiveScore(mate_moves=0, winning=False).as_dict())
        text = render_practical_pgn(report)
        self.assertIn('[TrickfishLineType "terminal"]', text)
        self.assertIn('[TrickfishTerminalScore "mate-loss 0"]', text)
        self.assertIn('[Result "*"]', text)


if __name__ == "__main__":
    unittest.main()
