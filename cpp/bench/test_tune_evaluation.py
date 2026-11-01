import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tune_evaluation as tuner
from test_run_experiment import prepare
from test_uci_matches import FakeEngine
import uci_matches as matches


def prepare_tuning(root, terminal=True):
    binary, _, training = prepare(root, terminal=terminal)
    openings = root / "confirmation-openings.json"
    openings.write_bytes(tuner.fixed.encoded({"version": 1, "openings": [
        {"id": "other-white-mate", "fen": "7k/8/6QK/8/8/8/8/8 w - - 0 1"},
        {"id": "other-black-mate", "fen": "8/8/8/8/8/6qk/8/7K b - - 0 1"}]}))
    confirmation = root / "confirmation-campaign.json"
    campaign = tuner.read_json(training)
    campaign.update(name="synthetic confirmation", openings=openings.name, openings_sha256=tuner.digest(openings),
        opening_ids=["other-white-mate", "other-black-mate"])
    confirmation.write_bytes(tuner.fixed.encoded(campaign))
    spec = root / "tuning.json"
    spec.write_bytes(tuner.fixed.encoded({"version": 1, "baseline": {name: 100 for name in tuner.WEIGHTS},
        "grid": {name: [90, 110] if name == "Eval Pawn Weight" else [100] for name in tuner.WEIGHTS},
        "training_campaign": training.name, "confirmation_campaign": confirmation.name,
        "sequential": {"p0": "0.5", "p1": "0.55", "alpha": "0.05", "beta": "0.05"}}))
    return binary, spec


class EvaluationTuningTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.choice = None
        FakeEngine.closed = []
        self.play = matches.play_game

    def player(self, *args, **kwargs):
        return self.play(*args, **kwargs, engine_factory=FakeEngine)

    def runner(self, command):
        with patch.object(matches.sys, "argv", command[1:]), patch.object(matches, "play_game", side_effect=self.player):
            matches.main()

    def mate_choice(self, engine, fen, moves, go):
        return ("g6g7" if fen.split()[1] == "w" else "g3g2"), "info depth 1", 1.0

    def test_full_grid_selection_disjoint_confirmation_and_idempotent_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            binary, spec = prepare_tuning(root)
            target = tuner.initialize(root / "tuning", binary, spec)
            with patch.object(FakeEngine, "choose", autospec=True, side_effect=self.mate_choice):
                receipt = tuner.execute(target, self.runner, self.player)
            self.assertEqual(receipt["confirmation_decision"], "inconclusive_horizon")
            selected = tuner.read_json(target / "selection.json")
            self.assertEqual(selected["winner"]["profile"]["Eval Pawn Weight"], 90)
            self.assertEqual(len(selected["trials"]), 2)
            self.assertTrue(all(trial["complete"] for trial in selected["trials"]))
            self.assertEqual(tuner.verify(target), receipt)
            runner = Mock(side_effect=AssertionError("completed tuning launched engines"))
            self.assertEqual(tuner.execute(target, runner, runner), receipt)
            runner.assert_not_called()
            binary.unlink()
            self.assertEqual(tuner.verify(target), receipt)

    def test_unfinished_training_does_not_select_or_run_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = tuner.initialize(root / "tuning", *prepare_tuning(root, terminal=False))
            player = Mock(side_effect=AssertionError("blocked tuning launched confirmation"))
            receipt = tuner.execute(target, self.runner, player)
            self.assertEqual(receipt["confirmation_decision"], "blocked_training_unfinished")
            self.assertFalse((target / "confirmation-run").exists())
            player.assert_not_called()
            self.assertEqual(tuner.verify(target), receipt)

    def test_interrupted_trial_resumes_without_replaying_completed_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = tuner.initialize(root / "tuning", *prepare_tuning(root))
            calls = []
            def fail_second(command):
                calls.append(command)
                if len(calls) == 2: raise RuntimeError("injected training failure")
                self.runner(command)
            with patch.object(FakeEngine, "choose", autospec=True, side_effect=self.mate_choice):
                with self.assertRaises(RuntimeError): tuner.execute(target, fail_second, self.player)
                self.assertTrue((target / "trial-000/receipt.json").exists())
                self.assertFalse((target / "selection.json").exists())
                runner = Mock(side_effect=self.runner)
                tuner.execute(target, runner, self.player)
                self.assertEqual(runner.call_count, 1)

    def test_rehashed_selection_and_profile_corruption_are_rejected(self):
        for change in ("selection", "profile"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                target = tuner.initialize(root / "tuning", *prepare_tuning(root))
                with patch.object(FakeEngine, "choose", autospec=True, side_effect=self.mate_choice):
                    tuner.execute(target, self.runner, self.player)
                name = "selection.json" if change == "selection" else "selected-profile.json"
                data = tuner.read_json(target / name)
                if change == "selection": data["winner"]["half_points"] = 900
                else: data["Eval Pawn Weight"] = 200
                (target / name).write_bytes(tuner.fixed.encoded(data))
                receipt = tuner.read_json(target / "receipt.json")
                receipt["artifacts"][name] = tuner.digest(target / name)
                (target / "receipt.json").write_bytes(tuner.fixed.encoded(receipt))
                with self.assertRaises(ValueError): tuner.verify(target)

    def test_overlap_duplicate_grid_and_weight_bounds_fail_before_setup(self):
        for change in ("overlap", "duplicate", "weight", "huge", "bool"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                binary, spec = prepare_tuning(root)
                data = tuner.read_json(spec)
                if change == "overlap": data["confirmation_campaign"] = data["training_campaign"]
                elif change == "duplicate": data["grid"]["Eval Pawn Weight"] = [100, 100]
                elif change == "weight": data["baseline"]["Eval Activity Weight"] = 201
                elif change == "bool": data["grid"]["Eval Pawn Weight"] = [True]
                else: data["grid"] = {name: list(range(5)) for name in tuner.WEIGHTS}
                spec.write_bytes(tuner.fixed.encoded(data))
                with self.assertRaises(ValueError): tuner.initialize(root / "tuning", binary, spec)
                self.assertFalse((root / "tuning").exists())


if __name__ == "__main__":
    unittest.main()
