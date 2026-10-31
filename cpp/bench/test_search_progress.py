import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import search_progress as reporter
from test_multipv_validation import sample


def progress_data():
    first, second = sample(1), sample(2)
    second["nodes"] = 16
    for line in second["lines"]: line["nodes"] = 3
    return {"progress_schema_version": 1, "iterations": [first, second], "result": copy.deepcopy(second)}


def uci_batch(depth=1, nodes=60, milliseconds=1):
    return [f"info depth {depth} nodes {nodes} time {milliseconds} nps {nodes * 1000 // milliseconds} multipv {rank} score cp {40 - rank * 10} pv {move}"
        for rank, move in enumerate(("e2e4", "d2d4", "b1c3"), 1)]


class SearchProgressTests(unittest.TestCase):
    def test_completed_json_events_and_interrupted_final_work_replay(self):
        data = progress_data()
        original = copy.deepcopy(data)
        result = reporter.validate_progress(data, reporter.STARTING_FEN, 2, 3)
        self.assertEqual(data, original)
        self.assertEqual(result["iterations"], 2)
        data["result"].update(stopped=True, nodes=20)
        result = reporter.validate_progress(data, reporter.STARTING_FEN, 4, 3)
        self.assertTrue(result["stopped"])
        self.assertEqual(result["nodes"], 20)

    def test_corrupt_json_sequences_counters_and_last_pv_are_rejected(self):
        for corruption in ("schema", "skipped", "duplicated", "stopped", "nodes", "horizon", "pv"):
            data = progress_data()
            if corruption == "schema": data["progress_schema_version"] = True
            elif corruption == "skipped": data["iterations"].pop(0)
            elif corruption == "duplicated": data["iterations"][1] = copy.deepcopy(data["iterations"][0])
            elif corruption == "stopped": data["iterations"][0]["stopped"] = True
            elif corruption == "nodes": data["iterations"][1]["nodes"] = 6
            elif corruption == "horizon": data["result"]["completed_depth"] = 1
            else: data["result"]["lines"][0].update(bestmove="b1a3", pv=["b1a3"])
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                reporter.validate_progress(data, reporter.STARTING_FEN, 2, 3)

    def test_fallback_is_not_a_completed_iteration(self):
        fallback = {"schema_version": 1, "completed_depth": 0, "nodes": 0, "stopped": True,
            "lines": [{"rank": 1, "score": 0, "completed_depth": 0, "nodes": 0, "bestmove": "e2e4", "pv": []}]}
        data = {"progress_schema_version": 1, "iterations": [], "result": fallback}
        self.assertEqual(reporter.validate_progress(data, reporter.STARTING_FEN, 3, 3)["iterations"], 0)
        data["iterations"] = [copy.deepcopy(fallback)]
        with self.assertRaises(ValueError): reporter.validate_progress(data, reporter.STARTING_FEN, 3, 3)

    def test_uci_batches_replay_and_timing_is_excluded_from_stable_trace(self):
        lines = uci_batch() + uci_batch(2, 200, 3) + uci_batch(2, 210, 4)
        batches = reporter.validate_uci_batches(lines, reporter.STARTING_FEN, 3)
        self.assertEqual([batch["depth"] for batch in batches], [1, 2, 2])
        self.assertEqual([batch["nodes"] for batch in batches], [60, 200, 210])
        changed = copy.deepcopy(batches)
        for batch in changed: batch.update(time=100, nps=0)
        self.assertEqual(reporter.trace_signature(batches), reporter.trace_signature(changed))
        single = ["info depth 1 nodes 21 time 0 nps 0 score cp 30 pv e2e4"]
        self.assertEqual(len(reporter.validate_uci_batches(single, reporter.STARTING_FEN, 1)), 1)
        self.assertGreater(reporter.score_order({"score_kind": "mate", "score": 1}), reporter.score_order({"score_kind": "cp", "score": 900}))
        self.assertGreater(reporter.score_order({"score_kind": "mate", "score": -3}), reporter.score_order({"score_kind": "mate", "score": -1}))

    def test_partial_mixed_regressing_or_changed_final_uci_batches_are_rejected(self):
        variants = []
        variants.append(uci_batch()[:2])
        variants.append(uci_batch()[1:])
        mixed = uci_batch()
        mixed[1] = mixed[1].replace("nodes 60", "nodes 61")
        variants.append(mixed)
        variants.append(uci_batch() + uci_batch(3, 200, 3))
        variants.append(uci_batch() + uci_batch(2, 60, 3))
        variants.append(uci_batch(milliseconds=5) + uci_batch(2, 200, 3))
        changed = uci_batch(1, 70, 2)
        changed[0] = changed[0].replace("pv e2e4", "pv e2e3")
        variants.append(uci_batch() + changed)
        duplicate = uci_batch()
        duplicate[1] = duplicate[1].replace("pv d2d4", "pv e2e4")
        variants.append(duplicate)
        for index, lines in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError): reporter.validate_uci_batches(lines, reporter.STARTING_FEN, 3)
        for line in ("info depth 1 nodes 1 time 0 nps 1 score cp 0 pv e2e4", "info depth 1 depth 2 nodes 1 time 1 nps 1000 score cp 0 pv e2e4",
                "info depth 0 nodes 0 time 0 nps 0 score cp 0", "info depth 1 nodes 1 time 1 nps 1000 multipv 0 score cp 0"):
            with self.subTest(line=line), self.assertRaises(ValueError): reporter.parse_info(line)

    def test_cli_observer_parity_output_protection_and_mismatch_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / "engine"
            binary.write_bytes(b"synthetic progress engine")
            output = binary.with_name("progress.json")
            data = progress_data()
            def run(command, **kwargs):
                value = data if command[1] == "--multi-pv-progress" else data["result"]
                return subprocess.CompletedProcess(command, 0, json.dumps(value), "")
            argv = ["reporter", str(binary), "--output", str(output)]
            with patch.object(reporter.sys, "argv", argv), patch.object(reporter, "cases", return_value=[("fixture", reporter.STARTING_FEN, 2, 3)]), patch.object(reporter.subprocess, "run", side_effect=run):
                reporter.main()
            report = json.loads(output.read_text())
            self.assertTrue(report["cases"][0]["observer_trace_identical"])
            original = binary.read_bytes()
            with patch.object(reporter.sys, "argv", ["reporter", str(binary), "--output", str(binary)]), patch.object(reporter.subprocess, "run") as runner:
                with self.assertRaises(ValueError): reporter.main()
                runner.assert_not_called()
            self.assertEqual(binary.read_bytes(), original)
            output.unlink()
            responses = [subprocess.CompletedProcess([], 0, json.dumps(data), ""), subprocess.CompletedProcess([], 0, "{}", "")]
            with patch.object(reporter.sys, "argv", argv), patch.object(reporter, "cases", return_value=[("fixture", reporter.STARTING_FEN, 2, 3)]), patch.object(reporter.subprocess, "run", side_effect=responses):
                with self.assertRaises(ValueError): reporter.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
