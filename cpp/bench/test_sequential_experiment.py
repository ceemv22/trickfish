import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sequential_experiment as sequential
from test_run_experiment import prepare
from test_uci_matches import FakeEngine
import uci_matches as matches


PARAMETERS = {"p0": "0.5", "p1": "0.55", "alpha": "0.05", "beta": "0.05", "max_pairs": 2}


class SequentialExperimentTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.choice = None
        FakeEngine.closed = []

    def player(self, *args, **kwargs):
        return matches.play_game(*args, **kwargs, engine_factory=FakeEngine)

    def test_unfinished_pair_blocks_and_completed_resume_never_launches_engines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = sequential.initialize(root / "experiment", *prepare(root), PARAMETERS)
            receipt = sequential.execute(target, self.player)
            self.assertEqual(receipt["decision"], "blocked_unfinished")
            state = sequential.read_json(target / "checkpoint.json")
            self.assertEqual(len(state["games"]), 2)
            self.assertEqual(sequential.verify(target), receipt)
            player = Mock(side_effect=AssertionError("completed resume launched an engine"))
            self.assertEqual(sequential.execute(target, player), receipt)
            player.assert_not_called()
            (root / "candidate").unlink()
            (root / "baseline").unlink()
            self.assertEqual(sequential.verify(target), receipt)

    def test_partial_pair_failure_restarts_only_the_uncommitted_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = sequential.initialize(root / "experiment", *prepare(root, terminal=True), PARAMETERS)
            def mate_choice(engine, fen, moves, go):
                return ("g6g7" if fen.split()[1] == "w" else "g3g2"), "info depth 1", 1.0
            calls = []
            def failing(*args, **kwargs):
                calls.append(args[2])
                if len(calls) == 4: raise RuntimeError("injected second-pair failure")
                return self.player(*args, **kwargs)
            with patch.object(FakeEngine, "choose", autospec=True, side_effect=mate_choice):
                with self.assertRaises(RuntimeError): sequential.execute(target, failing)
                self.assertEqual(len(sequential.read_json(target / "checkpoint.json")["games"]), 2)
                self.assertFalse((target / "receipt.json").exists())
                resumed = Mock(side_effect=self.player)
                receipt = sequential.execute(target, resumed)
                self.assertEqual(resumed.call_count, 2)
            self.assertEqual(receipt["decision"], "inconclusive_horizon")
            self.assertEqual(sequential.verify(target), receipt)

    def test_rehashed_fabricated_assessment_is_rejected_by_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            target = sequential.initialize(root / "experiment", *prepare(root), PARAMETERS)
            sequential.execute(target, self.player)
            assessment = sequential.read_json(target / "assessment.json")
            assessment["wins"] = 900
            (target / "assessment.json").write_bytes(sequential.encoded(assessment))
            receipt = sequential.read_json(target / "receipt.json")
            receipt["artifacts"]["assessment.json"] = sequential.digest(target / "assessment.json")
            (target / "receipt.json").write_bytes(sequential.encoded(receipt))
            with self.assertRaisesRegex(ValueError, "fabricated"): sequential.verify(target)

    def test_changed_binary_control_snapshot_and_opening_history_abort(self):
        for change in ("binary", "snapshot", "history"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                target = sequential.initialize(root / "experiment", *prepare(root), PARAMETERS)
                sequential.execute(target, self.player)
                if change == "binary":
                    (target / "receipt.json").unlink()
                    (root / "candidate").write_bytes(b"changed")
                    with self.assertRaisesRegex(ValueError, "binary changed"): sequential.execute(target, self.player)
                elif change == "snapshot":
                    (target / "openings.json").write_text("{}")
                    with self.assertRaisesRegex(ValueError, "snapshot changed"): sequential.verify(target)
                else:
                    checkpoint = sequential.read_json(target / "checkpoint.json")
                    checkpoint["games"][0]["moves"][0] = "a2a4"
                    (target / "checkpoint.json").write_bytes(sequential.encoded(checkpoint))
                    with self.assertRaises(ValueError): sequential.execute(target, self.player)

    def test_horizon_conflicts_rejected_before_creating_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            inputs = prepare(root)
            with self.assertRaises(ValueError):
                sequential.initialize(root / "experiment", *inputs, {**PARAMETERS, "max_pairs": 1})
            self.assertFalse((root / "experiment").exists())


if __name__ == "__main__":
    unittest.main()
