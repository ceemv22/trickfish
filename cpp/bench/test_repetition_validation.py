import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import repetition_validation as validator
from uci_matches import opening_position


class RepetitionValidationTests(unittest.TestCase):
    def test_fixture_histories_distinguish_current_and_child_repetition(self):
        fixtures = {case["id"]: case for case in validator.cases()}
        self.assertEqual(len(fixtures), 10)
        for case in fixtures.values(): opening_position(case)
        for name, count in (("fresh", 1), ("twofold", 2), ("root-threefold", 3), ("pawn-after-cycle", 1)):
            root, counts = opening_position(fixtures[name])
            from uci_matches import repetition_identity
            self.assertEqual(counts[repetition_identity(root)], count)
        root, counts = opening_position(fixtures["third-at-child"])
        child = root.make_move(next(move for move in root.legal_moves() if move.to_uci() == "f6g8"))
        self.assertEqual(counts[repetition_identity(child)] + 1, 3)

    def test_replay_rejects_illegal_moves_and_unmet_history_objectives(self):
        case = {"fen": validator.STARTING_FEN, "moves": [], "depth": 1}
        records = ["info depth 1 nodes 21 time 0 nps 0 score cp 30 pv e2e4", "bestmove e2e4"]
        result = validator.validate_trace(case, records)
        self.assertEqual(result["nodes"], 21)
        for corrupt in (records[:-1] + ["bestmove e2e5"], records + [records[-1]],
                [records[0].replace("pv e2e4", "pv e2e5"), records[-1]],
                records[:-1] + ["bestmove d2d4"], records[:-1] + ["bestmove 0000"],
                records[:-1] + ["bestmove e2e4 ponder e7e5"]):
            with self.subTest(corrupt=corrupt), self.assertRaises((ValueError, RuntimeError)):
                validator.validate_trace(case, corrupt)
        for objective in ({"depth": 2}, {"expected_score": 0}, {"expected_bestmove": "d2d4"}):
            with self.assertRaises(ValueError): validator.validate_trace({**case, **objective}, records)

    def test_comparison_allows_tied_move_and_work_changes_but_not_score_drift(self):
        first = {"depth": 2, "score_kind": "cp", "score": 0, "nodes": 100, "bestmove": "e2e4", "pv": ["e2e4", "e7e5"]}
        second = {**first, "nodes": 80, "bestmove": "d2d4", "pv": ["d2d4", "d7d5"]}
        before = copy.deepcopy((first, second))
        comparison = validator.compare_traces(first, second)
        self.assertEqual(comparison["node_delta"], -20)
        self.assertFalse(comparison["bestmove_equal"])
        self.assertEqual((first, second), before)
        for change in ({"depth": 1}, {"score": 1}, {"score_kind": "mate"}):
            with self.assertRaises(ValueError): validator.compare_traces(first, {**second, **change})

    def test_cli_preserves_binary_and_does_not_publish_failed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / "engine"
            binary.write_bytes(b"synthetic repetition fixture")
            output = binary.with_name("result.json")
            argv = ["validator", str(binary), "--output", str(output)]
            with patch.object(validator.sys, "argv", argv), patch.object(validator, "run_cases", return_value=[]):
                validator.main()
            self.assertEqual(json.loads(output.read_text())["binary_sha256"], validator.digest(binary))
            output.unlink()
            with patch.object(validator.sys, "argv", argv), patch.object(validator, "run_cases", side_effect=ValueError("fixture drift")):
                with self.assertRaises(ValueError): validator.main()
            self.assertFalse(output.exists())
            with patch.object(validator.sys, "argv", ["validator", str(binary), "--output", str(binary)]), patch.object(validator, "run_cases") as run:
                with self.assertRaises(ValueError): validator.main()
                run.assert_not_called()
            self.assertEqual(binary.read_bytes(), b"synthetic repetition fixture")


if __name__ == "__main__":
    unittest.main()
