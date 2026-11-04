import unittest

from trickfish.objective_score import ObjectiveScore
from trickfish.position import Position, STARTING_FEN
from trickfish.practical_pgn import render_nominee_probe
from trickfish.practical_review import assess_review, ReviewPolicy
from trickfish.variation import replay_uci_line


class ExpertReviewTests(unittest.TestCase):
    def report(self, depth):
        root = Position.from_fen(STARTING_FEN)
        scores = {move.to_uci(): -100 for move in root.legal_moves()}
        scores.update(e2e4=10, d2d4=0)
        candidates = []
        for move, expected in (("d2d4", 30), ("e2e4", 20)):
            score = ObjectiveScore(cp=scores[move]).as_dict()
            candidates.append({"move": move, "objective": score, "objective_cp": scores[move],
                               "expected_cp": expected, "trap_cp": expected - scores[move],
                               "objective_pv": ["e7e5", "g1f3"],
                               "reply_details": [{"move": "e7e5", "probability": 1,
                                                  "score": ObjectiveScore(cp=expected).as_dict(), "pv": ["g1f3"]}]})
        receipts = []
        for move in root.legal_moves():
            child = root.make_move(move)
            pv = ["e7e5", "g1f3"] if move.to_uci() in {"d2d4", "e2e4"} else ["e7e5"]
            receipts.append({"fen": child.to_fen(), "score_side_to_move": ObjectiveScore(cp=-scores[move.to_uci()]).as_dict(),
                             "pv": pv, "pv_final_fen": replay_uci_line(child, pv).to_fen()})
        return {"schema": "trickfish.practical-analysis.v2", "fen": STARTING_FEN, "perspective": "w",
                "opponent_rating": 1500, "margin_cp": 30, "selection": "d2d4", "selection_basis": "expected_cp",
                "root_evaluations": [{"move": move, "score": ObjectiveScore(cp=cp).as_dict()} for move, cp in scores.items()],
                "candidates": candidates, "reply_model": {"source": "synthetic", "sha256": "fixture", "rating": 1500, "positions": {}},
                "objective": {"depth": depth, "identity": ["fixture"], "executable_sha256": "fixture",
                              "options": "defaults", "evaluations": receipts}}

    def test_only_sound_unchanged_alternative_with_required_advantage_is_nominated(self):
        result = assess_review(self.report(8), self.report(12))
        self.assertEqual(result["status"], "review_candidate")
        self.assertEqual(result["verified_objective_loss_cp"], 10)
        self.assertEqual(result["modeled_advantage_over_objective_cp"], 10)
        self.assertEqual(result["reasons"], [])

    def test_shallow_unchanged_selection_does_not_qualify(self):
        result = assess_review(self.report(4), self.report(6))
        self.assertEqual(result["status"], "needs_review")
        self.assertIn("insufficient_depth", result["reasons"])

    def test_changed_selection_and_objective_baseline_remain_visible(self):
        screen = self.report(8)
        screen["selection"] = "e2e4"
        screen["candidates"][1]["expected_cp"] = 40
        screen["candidates"][1]["trap_cp"] = 30
        screen["candidates"][1]["reply_details"][0]["score"] = ObjectiveScore(cp=40).as_dict()
        result = assess_review(screen, self.report(12))
        self.assertIn("selection_changed", result["reasons"])
        self.assertIn("objective_baseline", result["reasons"])
        self.assertEqual(result["status"], "needs_review")

    def test_deeper_objective_rejection_preserves_a_replayable_nominee_probe(self):
        verified = self.report(12)
        verified["selection"] = "e2e4"
        verified["candidates"] = verified["candidates"][1:]
        next(row for row in verified["root_evaluations"] if row["move"] == "d2d4")["score"] = ObjectiveScore(cp=-21).as_dict()
        child = replay_uci_line(Position.from_fen(STARTING_FEN), ["d2d4"])
        next(record for record in verified["objective"]["evaluations"] if record["fen"] == child.to_fen())["score_side_to_move"] = ObjectiveScore(cp=21).as_dict()
        result = assess_review(self.report(8), verified)
        self.assertIn("objective_margin_failed", result["reasons"])
        self.assertIn("candidate_not_retained", result["reasons"])
        self.assertIn('1. d4 e5 2. Nf3 *', render_nominee_probe(verified, "d2d4"))

    def test_forged_expectation_or_receipt_is_rejected(self):
        verified = self.report(12)
        verified["candidates"][0]["expected_cp"] = 999
        with self.assertRaises(ValueError):
            assess_review(self.report(8), verified)
        verified = self.report(12)
        for record in verified["objective"]["evaluations"]:
            record["score_side_to_move"]["kind"] = "mate"
        with self.assertRaises(ValueError):
            assess_review(self.report(8), verified)
        verified = self.report(12)
        for record in verified["objective"]["evaluations"]:
            record["pv_final_fen"] = "incorrect"
        with self.assertRaises(ValueError):
            assess_review(self.report(8), verified)

    def test_policy_is_explicit_and_cannot_use_negative_or_reversed_thresholds(self):
        for kwargs in ({"minimum_screen_depth": 12}, {"maximum_objective_loss_cp": -1},
                       {"minimum_modeled_advantage_cp": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ReviewPolicy(**kwargs)


if __name__ == "__main__":
    unittest.main()
