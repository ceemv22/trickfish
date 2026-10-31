import copy
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import summarize_sliding_profile as profile


def fixture():
    return {"schema_version": 1, "cases": 2048, "iterations": 2, "generator": profile.GENERATOR,
        "seed": "123456789abcdef0", "scope": profile.SCOPE, "selected_engine_kernel": "ray",
        "samples": [{"reference_first": index % 2 == 0, "reference_ns": 200, "ray_ns": 100,
            "checksum": profile.reference_checksum(2)} for index in range(6)], "median_ray_reference_ratio": 0.5}


class SlidingProfileTests(unittest.TestCase):
    def test_checksum_repetition_and_pair_ratios_are_verified(self):
        data = fixture()
        original = copy.deepcopy(data)
        result = profile.summarize_profile(data)
        self.assertEqual(data, original)
        self.assertTrue(result["checksum_verified"])
        self.assertEqual(result["median_ray_reference_ratio"], 0.5)
        self.assertEqual(result["median_ray_ns_per_call"], 100 / 4096)
        self.assertEqual(profile.reference_checksum(2), profile.reference_checksum(1) * 2 & profile.MASK)

    def test_corrupt_workload_checksum_order_and_timing_are_rejected(self):
        for field, value in (("schema_version", True), ("cases", 2047), ("iterations", 0), ("iterations", True),
                ("generator", "other"), ("seed", "0000000000000000"), ("median_ray_reference_ratio", 0.6)):
            data = fixture()
            data[field] = value
            with self.assertRaises(ValueError): profile.summarize_profile(data)
        for field, value in (("checksum", 0), ("checksum", True), ("reference_first", True),
                ("reference_ns", float("nan")), ("ray_ns", float("inf")), ("ray_ns", 0), ("reference_ns", True)):
            data = fixture()
            data["samples"][-1][field] = value
            with self.assertRaises(ValueError): profile.summarize_profile(data)

    def test_cli_preserves_source_and_records_its_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "profile.json"
            source.write_text(json.dumps(fixture()))
            original = source.read_bytes()
            with patch.object(profile.sys, "argv", ["summary", str(source), "--output", str(source)]):
                with self.assertRaises(ValueError): profile.main()
            self.assertEqual(source.read_bytes(), original)
            output = io.StringIO()
            with patch.object(profile.sys, "argv", ["summary", str(source)]), patch.object(profile.sys, "stdout", output):
                profile.main()
            self.assertEqual(json.loads(output.getvalue())["source_profile"]["sha256"], profile.digest(source))


if __name__ == "__main__":
    unittest.main()
