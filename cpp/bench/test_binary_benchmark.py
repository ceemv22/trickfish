import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import search_benchmark as benchmark

FEN = "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"
OUTPUT = "bestmove a1a2\nscore 500\npv a1a2\ndepth 1\nstopped false\nnodes 23\n"


class BinaryBenchmarkTests(unittest.TestCase):
    def files(self, root):
        candidate, reference, suite = root / "candidate", root / "reference", root / "suite.json"
        candidate.write_bytes(b"candidate binary")
        reference.write_bytes(b"reference binary")
        suite.write_text(json.dumps({"version": 1, "positions": [{"id": "capture", "fen": FEN}]}))
        return candidate, reference, suite

    def arguments(self, candidate, reference, suite):
        return ["benchmark", str(candidate), "--reference-binary", str(reference), "--suite", str(suite),
            "--depth", "1", "--repeats", "2"]

    def sample(self, binary, case, depth, timeout, mode):
        return {"score": 500, "depth": depth, "nodes": 23, "bestmove": "a1a2", "pv": ["a1a2"]}, 10 if mode == "default" else 20

    def run_report(self, arguments, sample=None):
        output = io.StringIO()
        with patch.object(benchmark.sys, "argv", arguments), patch.object(benchmark.sys, "stdout", output):
            with patch.object(benchmark, "run_sample", side_effect=sample or self.sample), patch.object(benchmark, "revision", return_value=None):
                benchmark.main()
        return json.loads(output.getvalue())

    def test_two_executables_alternate_in_paired_rounds(self):
        candidate, reference = pathlib.Path("candidate"), pathlib.Path("reference")
        with patch.object(benchmark, "run_sample", side_effect=self.sample) as run:
            measured, order = benchmark.run_modes(candidate, {"id": "capture", "fen": FEN}, 1, 2, 10,
                ["default", "reference_binary"], reference_binary=reference)
        self.assertEqual([(call.args[0], call.args[4]) for call in run.call_args_list],
            [(candidate, "default"), (reference, "reference_binary"), (reference, "reference_binary"), (candidate, "default")])
        self.assertEqual(order, [["default", "reference_binary"], ["reference_binary", "default"]])
        self.assertEqual(benchmark.paired_wall_ratio(measured["default"], measured["reference_binary"]), 0.5)

    def test_reference_uses_compatible_default_search_cli(self):
        with patch.object(benchmark.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, OUTPUT)) as run:
            result, _ = benchmark.run_sample(pathlib.Path("reference"), {"id": "capture", "fen": FEN}, 1, 10, "reference_binary")
            self.assertEqual(run.call_args.args[0], ["reference", "--search", "1", FEN])
            self.assertEqual(result["score"], 500)

    def test_both_binary_hashes_ratio_and_optional_same_bytes_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, reference, suite = self.files(pathlib.Path(directory))
            for baseline in (reference, candidate):
                report = self.run_report(self.arguments(candidate, baseline, suite) + ["--reference-trace"])
                metadata = report["reference_binary"]
                self.assertEqual(metadata["sha256"], benchmark.digest(baseline))
                self.assertEqual(metadata["path"], str(baseline.resolve()))
                self.assertEqual(metadata["same_bytes_as_candidate"], baseline == candidate)
                comparison = report["results"][0]["binary_comparison"]
                self.assertEqual(comparison["median_paired_wall_ratio"], 0.5)
                self.assertTrue(all(comparison["trace_equal"].values()))
                self.assertEqual(comparison["node_delta_per_repeat"], 0)
                self.assertTrue(report["search"]["reference_trace_required"])

    def test_score_and_depth_drift_are_always_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments = self.arguments(*self.files(pathlib.Path(directory)))
            for field, value in (("score", 499), ("depth", 2)):
                def sample(binary, case, depth, timeout, mode):
                    result, elapsed = self.sample(binary, case, depth, timeout, mode)
                    if mode == "reference_binary": result[field] = value
                    return result, elapsed
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "binary score/depth mismatch"):
                    self.run_report(arguments, sample)

    def test_trace_differences_are_recorded_or_rejected_when_required(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments = self.arguments(*self.files(pathlib.Path(directory)))
            def sample(binary, case, depth, timeout, mode):
                result, elapsed = self.sample(binary, case, depth, timeout, mode)
                if mode == "reference_binary": result.update(nodes=24, bestmove="a1b1", pv=["a1b1"])
                return result, elapsed
            report = self.run_report(arguments, sample)
            self.assertEqual(report["results"][0]["binary_comparison"]["trace_equal"], {"nodes": False, "bestmove": False, "pv": False})
            with self.assertRaisesRegex(ValueError, "binary search trace mismatch"):
                self.run_report(arguments + ["--reference-trace"], sample)

    def test_reference_path_is_required_for_reference_controls(self):
        with self.assertRaises(ValueError):
            benchmark.run_modes(pathlib.Path("candidate"), {"id": "capture", "fen": FEN}, 1, 2, 10,
                ["default", "reference_binary"])
        with patch.object(benchmark.sys, "argv", ["benchmark", "missing", "--reference-trace"]):
            with patch.object(benchmark.sys, "stderr", io.StringIO()), self.assertRaises(SystemExit): benchmark.main()

    def test_reference_changes_and_output_alias_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, reference, suite = self.files(pathlib.Path(directory))
            arguments = self.arguments(candidate, reference, suite)
            original = reference.read_bytes()
            with patch.object(benchmark.sys, "argv", arguments + ["--output", str(reference)]):
                with patch.object(benchmark.sys, "stderr", io.StringIO()), patch.object(benchmark, "run_modes") as run:
                    with self.assertRaises(SystemExit): benchmark.main()
                    run.assert_not_called()
            self.assertEqual(reference.read_bytes(), original)
            def sample(binary, case, depth, timeout, mode):
                if mode == "reference_binary": reference.write_bytes(b"changed baseline")
                return self.sample(binary, case, depth, timeout, mode)
            with self.assertRaisesRegex(ValueError, "binary or suite changed"):
                self.run_report(arguments, sample)


if __name__ == "__main__":
    unittest.main()
