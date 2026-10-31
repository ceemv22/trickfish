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
COMPACT = OUTPUT + "q_ordering_calls 1\nq_ordered_moves 2\nq_filtered_quiet_moves 4\n"
REFERENCE = OUTPUT + "q_ordering_calls 2\nq_ordered_moves 6\nq_filtered_quiet_moves 0\n"


class QuiescenceBenchmarkTests(unittest.TestCase):
    def test_work_fields_are_complete_ascii_nonnegative_and_optional_for_old_modes(self):
        self.assertNotIn("q_ordering_calls", benchmark.parse_result(OUTPUT, FEN, 1))
        self.assertEqual(benchmark.parse_result(COMPACT, FEN, 1)["q_filtered_quiet_moves"], 4)
        for output in (COMPACT.replace("q_ordered_moves 2", "q_ordered_moves -1"),
                COMPACT.replace("q_ordered_moves 2", "q_ordered_moves 2.0"),
                COMPACT.replace("q_ordered_moves 2", "q_ordered_moves ٢"),
                COMPACT.replace("q_filtered_quiet_moves 4\n", ""),
                COMPACT + "pawn_cache_hits 0\npawn_cache_misses 0\n"):
            with self.assertRaises(ValueError): benchmark.parse_result(output, FEN, 1)

    def test_diagnostic_modes_require_consistent_work_and_select_their_cli(self):
        for mode, output in (("quiescence_compact", COMPACT), ("quiescence_reference", REFERENCE)):
            process = subprocess.CompletedProcess([], 0, output)
            with patch.object(benchmark.subprocess, "run", return_value=process) as run:
                benchmark.run_sample(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 10, mode)
                self.assertEqual(run.call_args.args[0][1], benchmark.MODES[mode])
        for mode, output in (("quiescence_compact", OUTPUT),
                ("quiescence_compact", COMPACT.replace("q_ordered_moves 2", "q_ordered_moves 1")),
                ("quiescence_reference", REFERENCE.replace("q_filtered_quiet_moves 0", "q_filtered_quiet_moves 1"))):
            with patch.object(benchmark.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output)):
                with self.assertRaises(ValueError):
                    benchmark.run_sample(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 10, mode)

    def run_report(self, root, drift=None):
        binary, suite = root / "engine", root / "suite.json"
        binary.write_bytes(b"engine")
        suite.write_text(json.dumps({"version": 1, "positions": [{"id": "capture", "fen": FEN}]}))
        output = io.StringIO()
        def sample(binary, case, depth, timeout, mode):
            text = COMPACT if mode == "quiescence_compact" else REFERENCE if mode == "quiescence_reference" else OUTPUT
            result = benchmark.parse_result(text, case["fen"], depth)
            if mode == "quiescence_compact" and drift == "trace": result["nodes"] += 1
            if mode == "quiescence_compact" and drift == "work":
                result.update(q_ordering_calls=3, q_ordered_moves=7)
            return result, 10 if mode == "quiescence_compact" else 12
        args = ["benchmark", str(binary), "--suite", str(suite), "--depth", "1", "--repeats", "2", "--compare-quiescence"]
        with patch.object(benchmark.sys, "argv", args), patch.object(benchmark.sys, "stdout", output):
            with patch.object(benchmark, "run_sample", side_effect=sample), patch.object(benchmark, "revision", return_value=None):
                benchmark.main()
        return json.loads(output.getvalue())

    def test_report_requires_exact_three_way_trace_and_records_work_reduction(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.run_report(pathlib.Path(directory))
            comparison = report["results"][0]["quiescence_comparison"]
            self.assertTrue(comparison["trace_equal"])
            self.assertEqual(comparison["ordering_call_delta"], -1)
            self.assertEqual(comparison["ordered_move_delta"], -4)
            self.assertAlmostEqual(comparison["median_paired_wall_ratio"], 10 / 12)
            self.assertEqual(report["search"]["mode_order"], ["default", "quiescence_compact", "quiescence_reference"])
            for drift in ("trace", "work"):
                with self.assertRaises(ValueError): self.run_report(pathlib.Path(directory), drift)


if __name__ == "__main__":
    unittest.main()
