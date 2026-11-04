import unittest

from trickfish.practical_report import render_report


class PracticalReportTests(unittest.TestCase):
    def test_objective_and_practical_picks_and_root_orientation_stay_distinct(self):
        report = {"fen": "fixture", "perspective": "b", "objective": {"identity": ["test engine"]},
                  "reply_model": {"source": "synthetic policy"}, "candidates": [
                      {"move": "d7d5", "objective_cp": 0, "objective_loss_cp": 20,
                       "expected_cp": 100, "trap_cp": 100,
                       "reply_details": [{"move": "e2e4", "probability": 0.75, "cp_original_mover": 120}]},
                      {"move": "e7e5", "objective_cp": 20, "objective_loss_cp": 0,
                       "expected_cp": 30, "trap_cp": 10, "reply_details": []}]}
        text = render_report(report)
        self.assertIn("Objective best among evaluated legal moves: **e7e5**", text)
        self.assertIn("Practical selection under the supplied model: **d7d5**", text)
        self.assertIn("75.0000%", text)
        self.assertIn("original mover's perspective (b)", text)
        self.assertIn("not a measured win probability", text)


if __name__ == "__main__":
    unittest.main()
