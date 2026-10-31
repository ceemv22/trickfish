import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assess_sliding_candidate as assessment
from search_benchmark import digest, load_suite
from summarize_sliding_profile import reference_checksum
from test_sliding_profile import fixture as profile_fixture
from trickfish.position import Position

SUITE = pathlib.Path(__file__).with_name("search_suite.json")


def inputs(depth=6, repeats=6, warmups=2, ratio=0.8, kernel_ratio=0.5):
    modes = ["default", "reference_binary"]
    order = [list(modes if index % 2 == 0 else reversed(modes)) for index in range(repeats)]
    warmup_order = [list(modes if index % 2 == 0 else reversed(modes)) for index in range(warmups)]
    cases = []
    for case in load_suite(SUITE)["positions"]:
        legal = Position.from_fen(case["fen"]).legal_moves()
        move = legal[0].to_uci() if legal else "0000"
        result = dict(case, score=0, depth=depth if legal else 1, nodes=1, bestmove=move,
            pv=[move] if legal else [], warmup_execution_order=warmup_order)
        def timed(value):
            return dict(result, process_wall_ms=[value] * repeats, min_process_wall_ms=value,
                max_process_wall_ms=value, median_process_wall_ms=value)
        candidate, reference = timed(20 * ratio), timed(20)
        candidate["execution_order"] = order
        candidate["binary_comparison"] = {"reference": reference, "score_equal": True,
            "trace_equal": {key: True for key in ("nodes", "bestmove", "pv")}, "node_delta_per_repeat": 0,
            "median_paired_wall_ratio": ratio}
        cases.append(candidate)
    report = {"schema_version": 3, "binary": "candidate", "binary_sha256": "a" * 64,
        "reference_binary": {"path": "reference", "sha256": "b" * 64, "mode": "--search", "same_bytes_as_candidate": False},
        "suite": str(SUITE), "suite_sha256": digest(SUITE), "environment": {"platform": "test", "machine": "test", "python": "test"},
        "build_provenance": {"candidate_revision": "a" * 40, "baseline_revision": "b" * 40, "configuration": "Release",
            "same_runner": True, "candidate_kernel": "ray", "baseline_kernel_requested": "reference"},
        "search": {"requested_depth": depth, "repeats": repeats, "mode_order": modes,
            "reference_trace_required": True, "warmups_per_mode_per_fixture": warmups, "timing": "process-inclusive wall time"},
        "results": cases, "total_nodes_per_repeat": len(cases)}
    profile = profile_fixture()
    profile["iterations"] = 512
    profile["median_ray_reference_ratio"] = kernel_ratio
    for sample in profile["samples"]:
        sample["checksum"] = reference_checksum(512)
        sample["ray_ns"] = sample["reference_ns"] * kernel_ratio
    return report, profile


class SlidingAssessmentTests(unittest.TestCase):
    def test_timing_boundaries_and_scope_are_explicit(self):
        report, profile = inputs(ratio=1)
        result = assessment.assess_candidate(report, profile, SUITE)
        self.assertTrue(result["timing_ready"])
        self.assertEqual(result["playing_strength_inference"], "none")
        self.assertIn("Core CI", result["scope"])
        for ratio, kernel_ratio in ((1.01, 0.5), (0.8, 1)):
            report, profile = inputs(ratio=ratio, kernel_ratio=kernel_ratio)
            self.assertFalse(assessment.assess_candidate(report, profile, SUITE)["timing_ready"])

    def test_insufficient_controls_same_bytes_and_wrong_workload_do_not_pass(self):
        for kwargs in ({"depth": 5}, {"repeats": 4}, {"repeats": 7}, {"warmups": 0}):
            report, profile = inputs(**kwargs)
            self.assertFalse(assessment.assess_candidate(report, profile, SUITE)["timing_ready"])
        report, profile = inputs()
        for change in ("same_bytes", "suite", "runner", "kernel"):
            candidate = copy.deepcopy(report)
            if change == "same_bytes": candidate["reference_binary"].update(sha256=candidate["binary_sha256"], same_bytes_as_candidate=True)
            elif change == "suite": candidate["suite_sha256"] = "c" * 64
            elif change == "runner": candidate["build_provenance"]["same_runner"] = 1
            else: candidate["build_provenance"]["candidate_kernel"] = "reference"
            self.assertFalse(assessment.assess_candidate(candidate, profile, SUITE)["timing_ready"])
        profile["samples"][-1]["checksum"] ^= 1
        with self.assertRaises(ValueError): assessment.assess_candidate(report, profile, SUITE)

    def test_standalone_report_and_input_alias_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            report, profile = inputs()
            binary_path, profile_path = root / "binary.json", root / "profile.json"
            binary_path.write_text(json.dumps(report))
            profile_path.write_text(json.dumps(profile))
            original = binary_path.read_bytes()
            with patch.object(assessment.sys, "argv", ["assessment", str(binary_path), str(profile_path), "--output", str(binary_path)]):
                with self.assertRaises(ValueError): assessment.main()
            self.assertEqual(binary_path.read_bytes(), original)
            result = subprocess.run([sys.executable, str(pathlib.Path(assessment.__file__)), str(binary_path), str(profile_path)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["timing_ready"])
            self.assertEqual(len(data["source_inputs"]), 3)


if __name__ == "__main__":
    unittest.main()
