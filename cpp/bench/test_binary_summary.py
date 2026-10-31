import copy
import io
import json
import pathlib
import statistics
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import summarize_binary_benchmark as summary
import search_benchmark as benchmark

FEN = "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"


def fixture(name, candidate_times, reference_times):
    def run(times):
        return {"id": name, "fen": FEN, "score": 500, "depth": 1, "nodes": 23,
            "bestmove": "a1a2", "pv": ["a1a2"], "process_wall_ms": times,
            "min_process_wall_ms": min(times), "max_process_wall_ms": max(times),
            "median_process_wall_ms": statistics.median(times)}
    candidate, reference = run(candidate_times), run(reference_times)
    candidate["execution_order"] = [["default", "reference_binary"], ["reference_binary", "default"]]
    candidate["binary_comparison"] = {"reference": reference, "score_equal": True,
        "trace_equal": {"nodes": True, "bestmove": True, "pv": True}, "node_delta_per_repeat": 0,
        "median_paired_wall_ratio": statistics.median([a / b for a, b in zip(candidate_times, reference_times)])}
    return candidate


def report():
    return {"schema_version": 3, "binary": "candidate", "binary_sha256": "a" * 64,
        "reference_binary": {"path": "reference", "sha256": "b" * 64, "mode": "--search", "same_bytes_as_candidate": False},
        "suite": "suite.json", "suite_sha256": "c" * 64, "environment": {"platform": "test"},
        "search": {"requested_depth": 1, "repeats": 2, "mode_order": ["default", "reference_binary"],
            "reference_trace_required": True, "timing": "process-inclusive wall time"},
        "results": [fixture("first", [10, 20], [20, 40]), fixture("second", [30, 60], [10, 20])],
        "total_nodes_per_repeat": 46}


class BinarySummaryTests(unittest.TestCase):
    def test_suite_aggregation_sums_raw_times_before_ratios(self):
        source = report()
        original = copy.deepcopy(source)
        result = summary.summarize_report(source)
        self.assertEqual(source, original)
        self.assertEqual(result["totals"]["candidate_suite_wall_ms"], [40, 80])
        self.assertEqual(result["totals"]["reference_suite_wall_ms"], [30, 60])
        self.assertAlmostEqual(result["totals"]["median_suite_wall_ratio"], 4 / 3)
        self.assertEqual([item["median_paired_wall_ratio"] for item in result["fixtures"]], [0.5, 3])
        self.assertEqual(result["totals"]["candidate_nodes_per_repeat"], 46)
        self.assertEqual(result["method"]["inference"], "none")

    def test_current_benchmark_producer_output_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            candidate, reference, suite = root / "candidate", root / "reference", root / "suite.json"
            candidate.write_bytes(b"candidate")
            reference.write_bytes(b"reference")
            suite.write_text(json.dumps({"version": 1, "positions": [{"id": "capture", "fen": FEN}]}))
            arguments = ["benchmark", str(candidate), "--reference-binary", str(reference), "--reference-trace",
                "--suite", str(suite), "--depth", "1", "--repeats", "2"]
            def sample(binary, case, depth, timeout, mode):
                return {"score": 500, "depth": depth, "nodes": 23, "bestmove": "a1a2", "pv": ["a1a2"]}, 10 if mode == "default" else 20
            output = io.StringIO()
            with patch.object(benchmark.sys, "argv", arguments), patch.object(benchmark.sys, "stdout", output):
                with patch.object(benchmark, "run_sample", side_effect=sample), patch.object(benchmark, "revision", return_value=None):
                    benchmark.main()
            result = summary.summarize_report(json.loads(output.getvalue()))
            self.assertEqual(result["totals"]["median_suite_wall_ratio"], 0.5)
            self.assertEqual(result["comparison_kind"], "distinct-binaries")
            self.assertEqual(result["candidate"]["sha256"], benchmark.digest(candidate))

    def test_same_binary_control_is_explicit(self):
        source = report()
        source["reference_binary"].update(sha256=source["binary_sha256"], same_bytes_as_candidate=True)
        result = summary.summarize_report(source)
        self.assertEqual(result["comparison_kind"], "same-binary-control")
        self.assertFalse(result["method"]["same_binary_control_is_optimization_evidence"])

    def test_invalid_raw_timings_are_rejected(self):
        for value in (0, -1, True, "10", float("nan"), float("inf")):
            source = report()
            source["results"][0]["process_wall_ms"][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError): summary.summarize_report(source)

    def test_stale_statistics_counts_trace_and_provenance_are_rejected(self):
        for field in ("median", "ratio", "count", "order", "identity", "nodes", "trace", "total", "duplicate", "hash", "path"):
            source = report()
            case = source["results"][0]
            comparison = case["binary_comparison"]
            if field == "median": case["median_process_wall_ms"] = 16
            elif field == "ratio": comparison["median_paired_wall_ratio"] = 1
            elif field == "count": source["search"]["repeats"] = 3
            elif field == "order": case["execution_order"].reverse()
            elif field == "identity": source["reference_binary"]["same_bytes_as_candidate"] = True
            elif field == "nodes": comparison["node_delta_per_repeat"] = 1
            elif field == "trace": comparison["trace_equal"]["pv"] = False
            elif field == "total": source["total_nodes_per_repeat"] = 47
            elif field == "duplicate": source["results"][1]["id"] = "first"
            elif field == "hash": source["reference_binary"]["sha256"] = "bad"
            else: source["reference_binary"]["path"] = None
            with self.subTest(field=field), self.assertRaises(ValueError): summary.summarize_report(source)

    def test_reference_pv_and_score_are_independently_checked(self):
        for field, value in (("score", 499), ("pv", ["a1a8"]), ("nodes", True)):
            source = report()
            source["results"][0]["binary_comparison"]["reference"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): summary.summarize_report(source)

    def test_trace_policy_allows_reported_work_changes_only_when_optional(self):
        source = report()
        comparison = source["results"][0]["binary_comparison"]
        comparison["reference"]["nodes"] = 24
        comparison["trace_equal"]["nodes"] = False
        comparison["node_delta_per_repeat"] = -1
        with self.assertRaises(ValueError): summary.summarize_report(source)
        source["search"]["reference_trace_required"] = False
        result = summary.summarize_report(source)
        self.assertEqual(result["totals"]["trace_changed_fixtures"], 1)
        self.assertEqual(result["totals"]["reference_nodes_per_repeat"], 47)

    def test_cli_provenance_and_input_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "benchmark.json"
            output = source.with_name("summary.json")
            source.write_text(json.dumps(report()))
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(pathlib.Path(summary.__file__).resolve()), str(source),
                "--output", str(output)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text())
            self.assertEqual(data["source_report"]["sha256"], summary.digest(source))
            with patch.object(summary.sys, "argv", ["summary", str(source), "--output", str(source)]):
                with patch.object(summary.sys, "stderr", io.StringIO()), patch.object(summary, "summarize_report") as summarize:
                    with self.assertRaises(SystemExit): summary.main()
                    summarize.assert_not_called()
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
