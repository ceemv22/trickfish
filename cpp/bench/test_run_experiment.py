import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_experiment as experiment
import uci_matches as matches
from test_uci_matches import FakeEngine, INITIAL


def prepare(root, terminal=False, profiles=False):
    root = root.resolve(strict=True)
    candidate, baseline = root / "candidate", root / "baseline"
    candidate.write_bytes(b"candidate")
    baseline.write_bytes(b"baseline")
    openings = [{"id": "e4", "fen": INITIAL, "moves": ["e2e4", "e7e5"]},
        {"id": "d4", "fen": INITIAL, "moves": ["d2d4", "d7d5"]}]
    if terminal:
        openings = [{"id": "white-mates", "fen": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"},
            {"id": "black-mates", "fen": "8/8/8/8/8/5kq1/8/7K b - - 0 1"}]
    opening_path = root / "source-openings.json"
    opening_path.write_bytes(experiment.encoded({"version": 1, "openings": openings}))
    profile_path = root / "source-profiles.json"
    if profiles: profile_path.write_bytes(experiment.encoded({"version": 1, "engines": {"a": {"Hash": 16}, "b": {}}}))
    campaign = root / "source-campaign.json"
    data = {"version": 1, "name": "synthetic experiment validation", "openings": opening_path.name,
        "openings_sha256": experiment.digest(opening_path), "opening_ids": [item["id"] for item in openings],
        "profiles": profile_path.name if profiles else None, "profiles_sha256": experiment.digest(profile_path) if profiles else None,
        "search_budget": {"kind": "nodes", "value": 64}, "rounds": 1, "seed": 42, "max_plies": 2, "timeout": 10}
    campaign.write_bytes(experiment.encoded(data))
    return candidate, baseline, campaign


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.closed = []
        FakeEngine.choice = None
        self.play = matches.play_game

    def fake_play(self, *args, **kwargs):
        return self.play(*args, **kwargs, engine_factory=FakeEngine)

    def runner(self, command):
        with patch.object(matches.sys, "argv", command[1:]), patch.object(matches, "play_game", side_effect=self.fake_play):
            matches.main()

    def test_complete_snapshot_receipt_and_idempotent_completed_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            candidate, baseline, campaign = prepare(root, profiles=True)
            provenance = root / "provenance.json"
            provenance.write_text('{"configuration":"Release","reported_only":true}')
            target = experiment.initialize(root / "experiment", candidate, baseline, campaign, provenance=provenance)
            plan_before = (target / "sign-plan.json").read_bytes()
            campaign.unlink()
            (root / "source-openings.json").unlink()
            (root / "source-profiles.json").unlink()
            receipt = experiment.execute(target, self.runner)
            self.assertEqual(receipt["status"], "inconclusive")
            self.assertIsNone(receipt["statistical_decision"])
            assessment = experiment.read_json(target / "assessment.json")
            self.assertEqual(assessment["blockers"], ["unfinished_pairs"])
            self.assertEqual(assessment["campaign_audit"]["analysis"]["overall"]["games"], 4)
            self.assertEqual((target / "sign-plan.json").read_bytes(), plan_before)
            self.assertIn("Blocked by: unfinished_pairs", (target / "summary.md").read_text())
            self.assertEqual(experiment.verify(target), receipt)
            runner = Mock(side_effect=AssertionError("completed resume launched engines"))
            self.assertEqual(experiment.execute(target, runner), receipt)
            runner.assert_not_called()
            candidate.unlink()
            baseline.unlink()
            self.assertEqual(experiment.verify(target), receipt)

    def test_terminal_games_are_evaluated_and_tied_pairs_do_not_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = experiment.initialize(root / "experiment", *prepare(root, terminal=True))
            def mate_choice(engine, fen, moves, go):
                return ("g6g7" if fen.split()[1] == "w" else "g3g2"), "info depth 1", 1.0
            with patch.object(FakeEngine, "choose", autospec=True, side_effect=mate_choice):
                receipt = experiment.execute(target, self.runner)
            self.assertEqual(receipt["status"], "evaluated")
            self.assertEqual(receipt["statistical_decision"], "not_rejected")
            statistic = experiment.read_json(target / "assessment.json")["statistic"]
            self.assertEqual((statistic["wins"], statistic["losses"], statistic["ties"]), (0, 0, 2))
            self.assertEqual(statistic["p_value_decimal"], "1")
            self.assertIn("sign test", (target / "summary.md").read_text().lower())

    def test_interruption_resumes_only_remaining_color_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = experiment.initialize(root / "experiment", *prepare(root))
            calls = []
            def interrupted(*args, **kwargs):
                calls.append(args[2])
                if len(calls) == 3: raise RuntimeError("synthetic engine failure")
                return self.fake_play(*args, **kwargs)
            def failed_runner(command):
                with patch.object(matches.sys, "argv", command[1:]), patch.object(matches, "play_game", side_effect=interrupted):
                    matches.main()
            with self.assertRaisesRegex(RuntimeError, "engine failure"): experiment.execute(target, failed_runner)
            self.assertFalse((target / "receipt.json").exists())
            self.assertFalse((target / "matches.json").exists())
            self.assertEqual(len(experiment.read_json(target / "checkpoint.json")["games"]), 2)
            before = (target / "checkpoint.json").read_bytes()
            resumed = []
            def resume_runner(command):
                self.assertIn("--resume", command)
                with patch.object(matches.sys, "argv", command[1:]), patch.object(matches, "play_game", side_effect=lambda *a, **k:
                    (resumed.append(a[2]), self.fake_play(*a, **k))[1]):
                    matches.main()
            receipt = experiment.execute(target, resume_runner)
            self.assertEqual(len(resumed), 2)
            self.assertNotEqual((target / "checkpoint.json").read_bytes(), before)
            self.assertEqual(experiment.verify(target), receipt)

    def test_changed_binary_snapshot_method_and_plan_block_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            candidate, baseline, campaign = prepare(root)
            target = experiment.initialize(root / "experiment", candidate, baseline, campaign)
            runner = Mock()
            candidate.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "engine bytes"): experiment.execute(target, runner)
            runner.assert_not_called()
            candidate.write_bytes(b"candidate")
            for name in ("openings.json", "campaign.json", "source-campaign.json", "sign-plan.json"):
                original = (target / name).read_bytes()
                (target / name).write_bytes(original + b"\n")
                with self.subTest(name=name), self.assertRaises(ValueError): experiment.execute(target, runner)
                (target / name).write_bytes(original)
            with patch.object(experiment, "method_hashes", return_value={}):
                with self.assertRaisesRegex(ValueError, "method sources"): experiment.execute(target, runner)
            runner.assert_not_called()

    def test_artifact_and_receipt_corruption_and_rehashed_summary_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = experiment.initialize(root / "experiment", *prepare(root))
            experiment.execute(target, self.runner)
            for name in experiment.ARTIFACTS:
                original = (target / name).read_bytes()
                (target / name).write_bytes(original + b"\n")
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "artifact changed"): experiment.verify(target)
                (target / name).write_bytes(original)
            original = (target / "receipt.json").read_bytes()
            receipt = json.loads(original)
            receipt["status"] = "evaluated"
            (target / "receipt.json").write_bytes(experiment.encoded(receipt))
            with self.assertRaisesRegex(ValueError, "decision differs"): experiment.verify(target)
            receipt = json.loads(original)
            (target / "summary.md").write_text("fabricated strength claim")
            receipt["artifacts"]["summary.md"] = experiment.digest(target / "summary.md")
            (target / "receipt.json").write_bytes(experiment.encoded(receipt))
            with self.assertRaisesRegex(ValueError, "derived experiment artifact"): experiment.verify(target)

    def test_failed_finalization_resumes_without_replaying_completed_games(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = experiment.initialize(root / "experiment", *prepare(root))
            writer = experiment.atomic_write
            def fail(path, content):
                if path.name == "assessment.json": raise OSError("synthetic write failure")
                writer(path, content)
            with patch.object(experiment, "atomic_write", side_effect=fail):
                with self.assertRaisesRegex(OSError, "write failure"): experiment.execute(target, self.runner)
            self.assertTrue((target / "matches.json").exists())
            self.assertFalse((target / "receipt.json").exists())
            runner = Mock(side_effect=AssertionError("replayed completed games"))
            receipt = experiment.execute(target, runner)
            runner.assert_not_called()
            self.assertEqual(experiment.verify(target), receipt)

    def test_midrun_binary_change_and_finalization_report_change_leave_no_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            candidate, baseline, campaign = prepare(root)
            target = experiment.initialize(root / "experiment", candidate, baseline, campaign)
            def changed(command):
                self.runner(command)
                candidate.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "engine bytes"): experiment.execute(target, changed)
            self.assertFalse((target / "receipt.json").exists())
            candidate.write_bytes(b"candidate")
            derive = experiment.derive_outputs
            def changed_report(*args):
                result = derive(*args)
                path = target / "matches.json"
                path.write_bytes(path.read_bytes() + b"\n")
                return result
            with patch.object(experiment, "derive_outputs", side_effect=changed_report):
                with self.assertRaisesRegex(ValueError, "changed during finalization"): experiment.execute(target)
            self.assertFalse((target / "receipt.json").exists())

    def test_new_directory_invalid_alpha_and_cli_completed_resume_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            candidate, baseline, campaign = prepare(root)
            original = campaign.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                experiment.initialize(root, candidate, baseline, campaign)
            self.assertEqual(campaign.read_bytes(), original)
            with self.assertRaises(ValueError): experiment.initialize(root / "invalid", candidate, baseline, campaign, "0.5")
            self.assertFalse((root / "invalid").exists())
            target = experiment.initialize(root / "experiment", candidate, baseline, campaign)
            receipt = experiment.execute(target, self.runner)
            for command in ("verify", "resume"):
                result = subprocess.run([sys.executable, str(pathlib.Path(experiment.__file__).resolve()), command, str(target)],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), receipt)
            result = subprocess.run([sys.executable, str(pathlib.Path(experiment.__file__).resolve()), "resume", str(target), "--alpha", "0.1"],
                capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(experiment.verify(target), receipt)

    def test_archived_copy_verifies_without_original_inputs_and_cannot_restart_play(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            candidate, baseline, campaign = prepare(root, profiles=True)
            target = experiment.initialize(root / "experiment", candidate, baseline, campaign)
            receipt = experiment.execute(target, self.runner)
            archive = root / "archive"
            shutil.copytree(target, archive)
            for name in ("campaign.json", "openings.json", "profiles.json", "sign-plan.json"):
                (target / name).write_text("original directory unavailable")
            candidate.unlink()
            baseline.unlink()
            self.assertEqual(experiment.verify(archive), receipt)
            runner = Mock(side_effect=AssertionError("archived copy launched engines"))
            self.assertEqual(experiment.execute(archive, runner), receipt)
            (archive / "receipt.json").unlink()
            with self.assertRaisesRegex(ValueError, "verification only"): experiment.execute(archive, runner)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
