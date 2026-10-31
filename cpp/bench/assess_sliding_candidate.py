import argparse
import json
import pathlib
import re
import sys

from search_benchmark import digest, load_suite, validate_output_path
from summarize_binary_benchmark import summarize_report
from summarize_sliding_profile import summarize_profile


def assess_candidate(report, profile, suite_path, baseline_kernel="reference"):
    if baseline_kernel not in ("reference", "ray"):
        raise ValueError("baseline kernel must be reference or ray")
    binary = summarize_report(report)
    kernel = summarize_profile(profile)
    suite = load_suite(suite_path)
    expected = [(case["id"], case["fen"], case.get("expect")) for case in suite["positions"]]
    actual = [(case["id"], case["fen"], case.get("expect")) for case in report["results"]]
    provenance = binary.get("reported_build_provenance") or {}
    environment = binary.get("environment") or {}
    valid_revisions = all(isinstance(provenance.get(key), str) and re.fullmatch(r"[0-9a-f]{40}", provenance[key])
        for key in ("candidate_revision", "baseline_revision"))
    checks = {
        "declared_suite_matches": report["suite_sha256"] == digest(suite_path) and expected == actual and len(expected) == 9,
        "distinct_binary_bytes": binary["comparison_kind"] == "distinct-binaries",
        "release_same_runner_reported": provenance.get("configuration") == "Release" and provenance.get("same_runner") is True,
        "git_revisions_reported": bool(valid_revisions),
        "environment_reported": all(isinstance(environment.get(key), str) and bool(environment[key])
            for key in ("platform", "machine", "python")),
        "kernel_pair_reported": provenance.get("candidate_kernel") == "ray" and provenance.get("baseline_kernel_requested") == baseline_kernel,
        "required_trace_unchanged": binary["method"]["trace_required"] and binary["totals"]["trace_changed_fixtures"] == 0,
        "depth_at_least_six": binary["depth"] >= 6,
        "balanced_six_or_more_pairs": binary["repeats"] >= 6 and binary["repeats"] % 2 == 0,
        "at_least_two_warmup_rounds": binary["method"]["warmups_per_mode_per_fixture"] >= 2,
        "full_direct_profile": kernel["iterations"] >= 512 and kernel["selected_engine_kernel"] == "ray" and kernel["checksum_verified"],
    }
    if baseline_kernel == "reference":
        checks["search_median_at_most_one"] = binary["totals"]["median_suite_wall_ratio"] <= 1
        checks["kernel_median_below_one"] = kernel["median_ray_reference_ratio"] < 1
    else:
        checks["search_median_below_one"] = binary["totals"]["median_suite_wall_ratio"] < 1
    return {"sliding_assessment_schema_version": 2, "timing_ready": all(checks.values()), "checks": checks,
        "comparison_policy": "ray_vs_reference" if baseline_kernel == "reference" else "same_ray_search",
        "baseline_kernel_expected": baseline_kernel,
        "search_median_candidate_reference_ratio": binary["totals"]["median_suite_wall_ratio"],
        "kernel_median_ray_reference_ratio": kernel["median_ray_reference_ratio"],
        "reported_build_provenance": provenance, "environment": binary["environment"],
        "suite_sha256": report["suite_sha256"], "candidate_binary_sha256": report["binary_sha256"],
        "scope": "one job and declared workload; Core CI, cross-OS acceptance and statistical significance are not inferred",
        "profile_association": "supplied together; provenance and engine/profile association are not authenticated",
        "playing_strength_inference": "none"}


def main():
    parser = argparse.ArgumentParser(description="Revalidate sliding measurements and report per-job timing readiness")
    parser.add_argument("binary_report", type=pathlib.Path)
    parser.add_argument("sliding_profile", type=pathlib.Path)
    parser.add_argument("--suite", type=pathlib.Path, default=pathlib.Path(__file__).with_name("search_suite.json"))
    parser.add_argument("--baseline-kernel", choices=("reference", "ray"), default="reference")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    sources = [path.resolve(strict=True) for path in (args.binary_report, args.sliding_profile, args.suite)]
    validate_output_path(args.output, sources)
    fingerprints = [digest(path) for path in sources]
    result = assess_candidate(json.loads(sources[0].read_text(encoding="utf-8-sig")),
        json.loads(sources[1].read_text(encoding="utf-8-sig")), sources[2], args.baseline_kernel)
    if [digest(path) for path in sources] != fingerprints:
        raise ValueError("assessment input changed during validation")
    result["source_inputs"] = [{"path": str(path), "sha256": value} for path, value in zip(sources, fingerprints)]
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
