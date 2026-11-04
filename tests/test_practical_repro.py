import copy
import unittest

from trickfish.objective_score import ObjectiveScore
from trickfish.position import Position, STARTING_FEN
from trickfish.practical_repro import compare_controlled_runs
from trickfish.stockfish_profile import ASSETS, OPTIONS, RELEASE


class ControlledComparisonTests(unittest.TestCase):
    def report(self, system):
        score = ObjectiveScore(cp=0).as_dict()
        asset = ASSETS[system]
        return {"schema": "trickfish.practical-analysis.v2", "fen": STARTING_FEN, "perspective": "w",
                "margin_cp": 30, "opponent_rating": 1500, "selection": "e2e4", "selection_basis": "expected_cp",
                "root_evaluations": [{"move": m.to_uci(), "score": copy.deepcopy(score)} for m in Position.from_fen(STARTING_FEN).legal_moves()],
                "candidates": [{"move": "e2e4", "objective": score, "expected_cp": 0}],
                "reply_model": {"source": "fixture", "rating": 1500, "positions": {}},
                "objective": {"depth": 12, "identity": ["id name Stockfish 19"], "options": dict(OPTIONS),
                              "executable_sha256": asset["executable_sha256"],
                              "controlled_profile": {"id": "stockfish19-controlled-v1", "release": RELEASE,
                                                     "system_build": system, **asset}}}

    def test_recognized_platform_builds_can_be_compared_without_equating_their_hashes(self):
        result = compare_controlled_runs(self.report("Windows"), self.report("Linux"))
        self.assertTrue(result["compared_fields_match"])
        self.assertNotEqual(result["first_build"]["executable_sha256"], result["second_build"]["executable_sha256"])

    def test_score_disagreement_is_reported_not_hidden(self):
        a, b = self.report("Windows"), self.report("Linux")
        b["root_evaluations"][0]["score"] = ObjectiveScore(cp=-10).as_dict()
        result = compare_controlled_runs(a, b)
        self.assertFalse(result["compared_fields_match"])
        self.assertEqual(len(result["root_changes"]), 1)

    def test_arbitrary_binary_wrong_options_and_mismatched_depth_fail(self):
        for change in (lambda r: r["objective"].update(executable_sha256="unknown"),
                       lambda r: r["objective"]["options"].update(Threads=2),
                       lambda r: r["objective"]["options"].update(Threads=True),
                       lambda r: r["objective"].update(depth=8)):
            b = self.report("Linux")
            change(b)
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare_controlled_runs(self.report("Windows"), b)


if __name__ == "__main__":
    unittest.main()
