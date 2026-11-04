import argparse
import hashlib
import json
import pathlib

from .practical_stability import validate_analysis
from .stockfish_profile import ASSETS, OPTIONS, RELEASE


def _controlled(report):
    depth, context, roots, candidates, policies = validate_analysis(report)
    objective = report["objective"]
    profile = objective.get("controlled_profile")
    if not isinstance(profile, dict) or profile.get("id") != "stockfish19-controlled-v1" or profile.get("release") != RELEASE:
        raise ValueError("controlled Stockfish 19 profile required")
    asset = ASSETS.get(profile.get("system_build"))
    if asset is None or any(profile.get(key) != asset[key] for key in ("archive", "archive_sha256", "executable_sha256")):
        raise ValueError("unrecognized controlled release asset")
    options = objective["options"]
    if (objective["executable_sha256"] != asset["executable_sha256"] or not isinstance(options, dict) or
            options.keys() != OPTIONS.keys() or any(type(options[name]) is not type(value) or options[name] != value
                                                     for name, value in OPTIONS.items())):
        raise ValueError("controlled binary/options mismatch")
    if "id name Stockfish 19" not in objective["identity"]:
        raise ValueError("controlled identity mismatch")
    return depth, {key: value for key, value in context.items() if key != "engine"}, roots, candidates, policies


def compare_controlled_runs(first, second):
    a, b = _controlled(first), _controlled(second)
    if a[:2] != b[:2]:
        raise ValueError("same depth, position, model, rating and margin contexts required")
    root_changes = [{"move": move, "first": a[2][move], "second": b[2][move]}
                    for move in sorted(a[2]) if a[2][move] != b[2][move]]
    candidate_changes = [{"move": move, "first": a[3].get(move), "second": b[3].get(move)}
                         for move in sorted(set(a[3]) | set(b[3])) if a[3].get(move) != b[3].get(move)]
    policy_changes = [fen for fen in sorted(set(a[4]) & set(b[4])) if a[4][fen] != b[4][fen]]
    selection_changed = first["selection"] != second["selection"]
    basis_changed = first["selection_basis"] != second["selection_basis"]
    return {"schema": "trickfish.controlled-comparison.v1", "depth": a[0], "context": a[1],
            "source_analysis_sha256": {label: hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"),
                                                allow_nan=False).encode("utf-8")).hexdigest()
                                       for label, report in (("first", first), ("second", second))},
            "first_runtime": first["objective"].get("runtime"), "second_runtime": second["objective"].get("runtime"),
            "first_build": first["objective"]["controlled_profile"], "second_build": second["objective"]["controlled_profile"],
            "selection_changed": selection_changed, "basis_changed": basis_changed,
            "root_changes": root_changes, "candidate_changes": candidate_changes,
            "shared_policy_changes": policy_changes,
            "compared_fields_match": not any((selection_changed, basis_changed, root_changes, candidate_changes, policy_changes)),
            "scope": "root scores, candidate evidence, selections and shared model predictions; not complete bitwise/search-work identity"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trickfish-practical-repro")
    parser.add_argument("first", type=pathlib.Path)
    parser.add_argument("second", type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("output must be a new file")
        result = compare_controlled_runs(json.loads(args.first.read_text(encoding="utf-8")),
                                         json.loads(args.second.read_text(encoding="utf-8")))
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
