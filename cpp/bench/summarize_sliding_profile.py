import argparse
import json
import math
import pathlib
import statistics
import sys

from search_benchmark import digest, validate_output_path

MASK = (1 << 64) - 1
GENERATOR = "xorshift64-13-7-17/mixed-sparse-dense-empty-v1"
SCOPE = "bishop and rook union; empty, sparse, dense and mixed occupancies; indirect call included; search excluded"


def reference_checksum(iterations):
    state = 0x123456789ABCDEF0
    def next_value():
        nonlocal state
        state ^= (state << 13) & MASK
        state ^= state >> 7
        state ^= (state << 17) & MASK
        return state
    total = 0
    for square in range(64):
        for sample in range(32):
            occupancy = next_value()
            if sample % 4 in (1, 2):
                first, second = next_value(), next_value()
                occupancy = occupancy & first & second if sample % 4 == 1 else occupancy | first | second
            elif sample % 4 == 3:
                occupancy = 0
            attacks = 0
            for dr, df in ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)):
                rank, file = square // 8 + dr, square % 8 + df
                while 0 <= rank < 8 and 0 <= file < 8:
                    bit = 1 << (rank * 8 + file)
                    attacks |= bit
                    if occupancy & bit: break
                    rank, file = rank + dr, file + df
            total += attacks
    return total * iterations & MASK


def positive(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid: raise ValueError("profile timings must be finite and positive")
    return value


def summarize_profile(data):
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("expected sliding profile schema 1")
    iterations = data["iterations"]
    if type(iterations) is not int or not 1 <= iterations <= 4096 or type(data.get("cases")) is not int or data["cases"] != 2048:
        raise ValueError("invalid sliding workload size")
    if data.get("generator") != GENERATOR or data.get("seed") != "123456789abcdef0" or data.get("scope") != SCOPE:
        raise ValueError("unsupported sliding workload provenance")
    if data.get("selected_engine_kernel") not in ("reference", "ray"):
        raise ValueError("unknown selected engine kernel")
    samples = data["samples"]
    if not isinstance(samples, list) or len(samples) != 6: raise ValueError("expected six paired sliding samples")
    checksum = reference_checksum(iterations)
    ratios, reference_per_call, ray_per_call = [], [], []
    for index, sample in enumerate(samples):
        if type(sample.get("reference_first")) is not bool or sample["reference_first"] != (index % 2 == 0):
            raise ValueError("sliding sample order mismatch")
        if type(sample.get("checksum")) is not int or sample["checksum"] != checksum:
            raise ValueError("sliding checksum differs from independent reference")
        old, ray = positive(sample["reference_ns"]), positive(sample["ray_ns"])
        ratios.append(positive(ray / old))
        reference_per_call.append(old / (2048 * iterations))
        ray_per_call.append(ray / (2048 * iterations))
    median = statistics.median(ratios)
    if not math.isclose(positive(data["median_ray_reference_ratio"]), median, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("stored sliding median disagrees with raw samples")
    return {"sliding_summary_schema_version": 1, "selected_engine_kernel": data["selected_engine_kernel"],
        "checksum_verified": True, "cases": 2048, "iterations": iterations, "checksum": checksum,
        "paired_ray_reference_ratios": ratios, "median_ray_reference_ratio": median,
        "median_reference_ns_per_call": statistics.median(reference_per_call),
        "median_ray_ns_per_call": statistics.median(ray_per_call), "scope": SCOPE,
        "inference": "descriptive kernel timings; no search speed or statistical inference"}


def main():
    parser = argparse.ArgumentParser(description="Validate native sliding profiles against an independent checksum")
    parser.add_argument("profile", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    source = args.profile.resolve(strict=True)
    validate_output_path(args.output, [source])
    fingerprint = digest(source)
    result = summarize_profile(json.loads(source.read_text(encoding="utf-8-sig")))
    if digest(source) != fingerprint: raise ValueError("sliding profile changed during validation")
    result["source_profile"] = {"path": str(source), "sha256": fingerprint}
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
