import copy
import unittest

from trickfish.objective_score import ObjectiveScore
from trickfish.position import Position, STARTING_FEN
from trickfish.practical_stability import compare_depths, render_stability


class PracticalStabilityTests(unittest.TestCase):
    def report(self, depth=4):
        score = ObjectiveScore(cp=0).as_dict()
        return {"schema": "trickfish.practical-analysis.v2", "fen": STARTING_FEN, "perspective": "w",
                "margin_cp": 30, "opponent_rating": 1500, "selection": "e2e4", "selection_basis": "expected_cp",
                "objective": {"depth": depth, "executable_sha256": "fixture-binary", "identity": ["engine"], "options": "defaults"},
                "reply_model": {"source": "fixture", "sha256": "fixture-policy", "rating": 1500, "positions": {}},
                "root_evaluations": [{"move": move.to_uci(), "score": copy.deepcopy(score)}
                                     for move in Position.from_fen(STARTING_FEN).legal_moves()],
                "candidates": [{"move": move, "objective": copy.deepcopy(score), "expected_cp": 10}
                               for move in ("e2e4", "d2d4")]}

    def test_selection_and_candidate_changes_are_reported_without_quality_claim(self):
        shallow, deep = self.report(), self.report(6)
        deep["selection"] = "d2d4"
        deep["candidates"] = deep["candidates"][1:]
        result = compare_depths([deep, shallow])
        transition = result["transitions"][0]
        self.assertTrue(transition["selection_changed"])
        self.assertEqual(transition["removed_candidates"], ["e2e4"])
        self.assertFalse(transition["previous_selection_retained"])
        self.assertIn("not evidence of improvement", render_stability(result))
        self.assertEqual(len(result["snapshots"][0]["analysis_sha256"]), 64)

    def test_unchanged_selection_does_not_hide_changed_candidate_set(self):
        shallow, deep = self.report(), self.report(6)
        deep["candidates"] = deep["candidates"][:1]
        transition = compare_depths([shallow, deep])["transitions"][0]
        self.assertFalse(transition["selection_changed"])
        self.assertEqual(transition["removed_candidates"], ["d2d4"])

    def test_mate_transition_never_has_numeric_cp_delta(self):
        shallow, deep = self.report(), self.report(6)
        root = next(item for item in deep["root_evaluations"] if item["move"] == "f2f3")
        root["score"] = ObjectiveScore(mate_moves=3, winning=False).as_dict()
        change = compare_depths([shallow, deep])["transitions"][0]["root_score_changes"][0]
        self.assertEqual(change["after"]["kind"], "mate")
        self.assertIsNone(change["cp_delta"])

    def test_rejects_different_context_instead_of_attributing_it_to_depth(self):
        for field, replacement in (("opponent_rating", 1600), ("margin_cp", 40), ("perspective", "b")):
            deep = self.report(6)
            deep[field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                compare_depths([self.report(), deep])
        for group, field in (("objective", "executable_sha256"), ("reply_model", "sha256")):
            deep = self.report(6)
            deep[group][field] = "different"
            with self.subTest(group=group), self.assertRaises(ValueError):
                compare_depths([self.report(), deep])

    def test_duplicate_depth_incomplete_root_and_illegal_selection_fail(self):
        with self.assertRaises(ValueError):
            compare_depths([self.report(), self.report()])
        for mutate in (lambda d: d["root_evaluations"].pop(),
                       lambda d: d.update(selection="e1e8"),
                       lambda d: d["candidates"].append(copy.deepcopy(d["candidates"][0]))):
            deep = self.report(6)
            mutate(deep)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                compare_depths([self.report(), deep])

    def test_changed_predictions_are_rejected_even_with_same_model_label(self):
        shallow, deep = self.report(), self.report(6)
        shallow["reply_model"]["positions"] = {"shared position": {"e2e4": 0.5, "d2d4": 0.5}}
        deep["reply_model"]["positions"] = {"shared position": {"e2e4": 0.9, "d2d4": 0.1}}
        with self.assertRaises(ValueError):
            compare_depths([shallow, deep])


if __name__ == "__main__":
    unittest.main()
