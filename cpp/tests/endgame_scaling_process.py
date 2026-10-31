import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))

from search_benchmark import load_suite
from evaluation_parity import Position, expected_fields


def output_fields(binary, mode, fen):
    result = subprocess.run([str(binary), mode, fen], capture_output=True, text=True, timeout=10, check=True)
    fields = {}
    for line in result.stdout.splitlines():
        name, value = line.split()
        if name in fields:
            raise AssertionError(f"duplicate diagnostic field: {name}")
        fields[name] = value
    return fields


def main():
    binary = pathlib.Path(sys.argv[1]).resolve(strict=True)
    suite = load_suite(pathlib.Path(__file__).resolve().parents[1] / "bench" / "pawnless_suite.json")
    factors = {"normal": 256, "two_knights_bare_king": 32, "rook_minor": 64, "rook_minor_rook": 64}
    for case in suite["positions"]:
        expected = case["expect_scale"]
        if set(expected) != {"factor", "reason"} or type(expected["factor"]) is not int or factors.get(expected["reason"]) != expected["factor"]:
            raise AssertionError(f"invalid expected scaling metadata: {case['id']}")
        reference = expected_fields(Position.from_fen(case["fen"]))
        raw = reference["static_total"]
        scaled = (abs(raw) * expected["factor"] // 256) * (-1 if raw < 0 else 1)
        actual = output_fields(binary, "--eval-scale", case["fen"])
        wanted = {"factor": str(expected["factor"]), "reason": expected["reason"],
            "static_total": str(raw), "scaled_static": str(scaled), "reference_evaluation": str(reference["evaluation"])}
        if actual != wanted:
            raise AssertionError(f"scaling diagnostic mismatch: {case['id']}: {actual} != {wanted}")
        public = output_fields(binary, "--eval-detail", case["fen"])
        if public != {name: str(value) for name, value in reference.items()}:
            raise AssertionError(f"public evaluator changed: {case['id']}")
    print(f"Scaling reasons, factors and public reference isolation passed for {len(suite['positions'])} positions")


if __name__ == "__main__":
    main()
