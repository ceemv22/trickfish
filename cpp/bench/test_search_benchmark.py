import importlib.util
import io
import json
import pathlib
import subprocess
import unittest
from unittest.mock import Mock, patch

SOURCE = pathlib.Path(__file__).with_name("search_benchmark.py")
spec = importlib.util.spec_from_file_location("search_benchmark", SOURCE)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)

FEN = "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"
OUTPUT = "bestmove a1a2\nscore 500\npv a1a2\ndepth 1\nstopped false\nnodes 23\n"


class BenchmarkTest(unittest.TestCase):
    def test_valid_pv_and_terminal_root(self):
        result = benchmark.parse_result(OUTPUT, FEN, 1)
        self.assertEqual(result["bestmove"], "a1a2")
        terminal = "bestmove 0000\nscore 0\npv\ndepth 1\nstopped false\nnodes 1\n"
        benchmark.parse_result(terminal, "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 3)
        with self.assertRaises(ValueError):
            benchmark.parse_result(terminal, FEN, 1)

    def test_rejects_malformed_or_incomplete_output(self):
        for output in [OUTPUT + "score 500\n", OUTPUT.replace("score 500\n", ""),
            OUTPUT.replace("nodes 23", "nodes 0"), OUTPUT.replace("stopped false", "stopped true"),
            OUTPUT.replace("depth 1", "depth 0"), OUTPUT.replace("score 500", "score 500 extra")]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                benchmark.parse_result(output, FEN, 1)

    def test_rejects_illegal_or_inconsistent_pv(self):
        for output in [OUTPUT.replace("a1a2", "a1h8"), OUTPUT.replace("pv a1a2", "pv a1b1"),
            OUTPUT.replace("pv a1a2", "pv a1a2 e8e7"), OUTPUT.replace("pv a1a2", "pv")]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                benchmark.parse_result(output, FEN, 1)

    def test_repeat_drift_is_rejected(self):
        processes = [subprocess.CompletedProcess([], 0, OUTPUT),
            subprocess.CompletedProcess([], 0, OUTPUT.replace("nodes 23", "nodes 24"))]
        with patch.object(benchmark.subprocess, "run", side_effect=processes):
            with self.assertRaisesRegex(ValueError, "nondeterministic"):
                benchmark.run_case(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 2, 10)

    def test_failed_and_timed_out_processes_propagate(self):
        for error in [subprocess.TimeoutExpired("engine", 1), subprocess.CalledProcessError(1, "engine")]:
            with patch.object(benchmark.subprocess, "run", side_effect=error), self.assertRaises(type(error)):
                benchmark.run_case(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 2, 10)

    def test_reference_comparison_allows_ties_but_rejects_score_drift(self):
        candidate = {"id": "tie", "score": 0, "depth": 2, "nodes": 50, "bestmove": "a1b1"}
        reference = dict(candidate, nodes=70, bestmove="a1c1")
        comparison = benchmark.compare_reference(candidate, reference)
        self.assertEqual(comparison["node_delta_per_repeat"], -20)
        for drift in [dict(reference, score=1), dict(reference, depth=1)]:
            with self.assertRaisesRegex(ValueError, "PVS/full-window mismatch"):
                benchmark.compare_reference(candidate, drift)

    def test_reference_runner_selects_full_window_cli(self):
        process = subprocess.CompletedProcess([], 0, OUTPUT)
        with patch.object(benchmark.subprocess, "run", return_value=process) as execute:
            benchmark.run_case(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 2, 10, False)
            self.assertEqual(execute.call_args.args[0][1], "--search-ab")

    def test_tactical_move_objective_rejects_legal_wrong_move(self):
        case = {"id": "capture", "fen": FEN, "expect": {"bestmoves": ["a1a2"]}}
        benchmark.validate_objective(case, {"bestmove": "a1a2", "score": 500})
        with self.assertRaisesRegex(ValueError, "tactical move objective failed"):
            benchmark.validate_objective(case, {"bestmove": "a1b1", "score": 500})

    def test_mate_objective_requires_actual_mate_and_score_distance(self):
        case = {"id": "mate", "fen": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "expect": {"mate_in_one": True}}
        benchmark.validate_objective(case, {"bestmove": "g6g7", "score": 99999})
        for result in [{"bestmove": "g6g5", "score": 99999}, {"bestmove": "g6g7", "score": 99998}]:
            with self.assertRaisesRegex(ValueError, "mate-in-one objective failed"):
                benchmark.validate_objective(case, result)

    def test_invalid_objectives_are_rejected_before_search(self):
        for expect in [{}, {"unknown": True}, {"bestmoves": []}, {"bestmoves": ["a1a8"]},
            {"bestmoves": ["a1a2", "a1a2"]}, {"mate_in_one": False}, {"mate_in_one": True}]:
            with self.subTest(expect=expect), self.assertRaises(ValueError):
                benchmark.validate_objective({"id": "invalid", "fen": FEN, "expect": expect})

    def test_exchange_runner_selects_opt_in_cli(self):
        process = subprocess.CompletedProcess([], 0, OUTPUT)
        with patch.object(benchmark.subprocess, "run", return_value=process) as execute:
            benchmark.run_case(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 2, 10, use_exchange=True)
            self.assertEqual(execute.call_args.args[0][1], "--search-see")

    def test_null_runner_selects_opt_in_cli(self):
        process = subprocess.CompletedProcess([], 0, OUTPUT)
        with patch.object(benchmark.subprocess, "run", return_value=process) as execute:
            benchmark.run_case(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, 2, 10, use_null=True)
            self.assertEqual(execute.call_args.args[0][1], "--search-null")

    def test_paired_modes_alternate_and_keep_results_separate(self):
        normal = subprocess.CompletedProcess([], 0, OUTPUT)
        alternate = subprocess.CompletedProcess([], 0, OUTPUT.replace("nodes 23", "nodes 30"))
        ticks = [0, 10000000, 20000000, 40000000, 50000000, 80000000, 90000000, 110000000]
        with patch.object(benchmark.subprocess, "run", side_effect=[normal, alternate, alternate, normal]) as execute:
            with patch.object(benchmark.time, "perf_counter_ns", side_effect=ticks):
                results, order = benchmark.run_modes(pathlib.Path("engine"), {"id": "capture", "fen": FEN},
                    1, 2, 10, ["default", "alphabeta"])
        self.assertEqual(order, [["default", "alphabeta"], ["alphabeta", "default"]])
        self.assertEqual([call.args[0][1] for call in execute.call_args_list],
            ["--search", "--search-ab", "--search-ab", "--search"])
        self.assertEqual(results["default"]["nodes"], 23)
        self.assertEqual(results["alphabeta"]["nodes"], 30)
        self.assertEqual(results["default"]["process_wall_ms"], [10, 20])
        self.assertEqual(results["alphabeta"]["process_wall_ms"], [20, 30])
        self.assertEqual(results["default"]["median_process_wall_ms"], 15)

    def test_interleaved_drift_is_detected_within_its_mode(self):
        outputs = [OUTPUT, OUTPUT.replace("nodes 23", "nodes 30"), OUTPUT.replace("nodes 23", "nodes 31")]
        processes = [subprocess.CompletedProcess([], 0, text) for text in outputs]
        with patch.object(benchmark.subprocess, "run", side_effect=processes):
            with self.assertRaisesRegex(ValueError, "nondeterministic.*alphabeta"):
                benchmark.run_modes(pathlib.Path("engine"), {"id": "capture", "fen": FEN},
                    1, 2, 10, ["default", "alphabeta"])

    def test_paired_ratios_and_undefined_timing(self):
        self.assertEqual(benchmark.paired_wall_ratio({"process_wall_ms": [20, 30]},
            {"process_wall_ms": [10, 20]}), 1.75)
        self.assertIsNone(benchmark.paired_wall_ratio({"process_wall_ms": [20, 30]},
            {"process_wall_ms": [0, 20]}))
        with self.assertRaises(ValueError):
            benchmark.paired_wall_ratio({"process_wall_ms": [20]}, {"process_wall_ms": [10, 20]})

    def test_invalid_mode_schedules_are_rejected(self):
        for repeats, modes in [(1, ["default"]), (2, []), (2, ["default", "default"]), (2, ["unknown"])]:
            with self.assertRaises(ValueError):
                benchmark.run_modes(pathlib.Path("engine"), {"id": "capture", "fen": FEN}, 1, repeats, 10, modes)

    def test_report_composes_paired_mode_ratios_and_schedule(self):
        nodes = {"default": 23, "alphabeta": 30, "exchange": 20, "null": 40}
        elapsed = {"default": 10, "alphabeta": 20, "exchange": 5, "null": 30}
        def sample(binary, case, depth, timeout, mode):
            return {"score": 500, "depth": depth, "nodes": nodes[mode], "bestmove": "a1a2", "pv": ["a1a2"]}, elapsed[mode]
        output = io.StringIO()
        arguments = [str(SOURCE), str(SOURCE), "--suite", str(SOURCE.with_name("search_suite.json")),
            "--repeats", "2", "--compare-alphabeta", "--compare-exchange", "--compare-null"]
        with patch.object(benchmark.sys, "argv", arguments), patch.object(benchmark.sys, "stdout", output):
            with patch.object(benchmark, "run_sample", side_effect=sample), patch.object(benchmark, "revision", return_value=None):
                benchmark.main()
        report = json.loads(output.getvalue())
        self.assertEqual(report["schema_version"], 3)
        modes = ["default", "alphabeta", "exchange", "null"]
        self.assertEqual(report["search"]["mode_order"], modes)
        for result in report["results"]:
            self.assertEqual(result["execution_order"], [modes, list(reversed(modes))])
            self.assertEqual(result["alphabeta_comparison"]["median_paired_wall_ratio"], 0.5)
            self.assertEqual(result["exchange_comparison"]["median_paired_wall_ratio"], 0.5)
            self.assertEqual(result["null_comparison"]["median_paired_wall_ratio"], 3)
            self.assertEqual(result["exchange_comparison"]["node_delta_per_repeat"], -3)
            self.assertEqual(result["null_comparison"]["node_delta_per_repeat"], 17)

    def test_selective_score_drift_is_reported_without_claiming_parity(self):
        output = io.StringIO()
        arguments = [str(SOURCE), str(SOURCE), "--suite", str(SOURCE.with_name("search_suite.json")),
            "--repeats", "2", "--compare-lmr", "--compare-futility", "--compare-razor"]
        def sample(binary, case, depth, timeout, mode):
            return {"score": 1 if mode in {"lmr", "futility", "razor"} else 0, "depth": depth, "nodes": 10,
                "bestmove": "a1a2", "pv": ["a1a2"]}, 10
        with patch.object(benchmark.sys, "argv", arguments), patch.object(benchmark.sys, "stdout", output):
            with patch.object(benchmark, "run_sample", side_effect=sample), patch.object(benchmark, "revision", return_value=None):
                benchmark.main()
        report = json.loads(output.getvalue())
        for result in report["results"]:
            for mode in ("lmr", "futility", "razor"):
                self.assertFalse(result[mode + "_comparison"]["score_equal"])
                self.assertEqual(result[mode + "_comparison"]["score_delta"], 1)
        self.assertEqual(benchmark.MODES["lmr"], "--search-lmr")
        self.assertEqual(benchmark.MODES["futility"], "--search-futility")
        self.assertEqual(benchmark.MODES["razor"], "--search-razor")

    def test_suite_rejects_duplicates_and_checked_nonmoving_king(self):
        path = Mock()
        case = {"id": "capture", "fen": FEN}
        for cases in [[case, case], [{"id": "illegal", "fen": "4k3/8/8/8/8/8/8/K3R3 w - - 0 1"}]]:
            path.read_text.return_value = json.dumps({"version": 1, "positions": cases})
            with self.assertRaises(ValueError):
                benchmark.load_suite(path)


if __name__ == "__main__":
    unittest.main()
