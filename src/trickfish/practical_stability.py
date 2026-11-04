import argparse
import hashlib
import json
import pathlib
from math import isclose

from .objective_score import ObjectiveScore
from .position import Position
from .practical import _score


def _typed_score(value):
    score = ObjectiveScore(cp=value.get("cp"), mate_moves=value.get("mate_moves"), winning=value.get("winning"))
    if value.get("kind") != score.as_dict()["kind"]:
        raise ValueError("score kind disagrees with its value")
    return score.as_dict()


def validate_analysis(report):
    if report.get("schema") != "trickfish.practical-analysis.v2":
        raise ValueError("stability comparison requires v2 analyses")
    position = Position.from_fen(report["fen"])
    if report["perspective"] != position.side_to_move:
        raise ValueError("report perspective disagrees with FEN")
    legal = {move.to_uci() for move in position.legal_moves()}
    roots = {item["move"]: _typed_score(item["score"]) for item in report["root_evaluations"]}
    if set(roots) != legal or len(roots) != len(report["root_evaluations"]):
        raise ValueError("root evidence must cover each legal move exactly once")
    candidates = {item["move"]: item for item in report["candidates"]}
    if len(candidates) != len(report["candidates"]) or not set(candidates) <= legal:
        raise ValueError("invalid candidate coverage")
    for move, item in candidates.items():
        if _typed_score(item["objective"]) != roots[move]:
            raise ValueError("candidate objective disagrees with root evidence")
        if item["expected_cp"] is not None:
            _score(item["expected_cp"])
    if legal and report["selection"] not in candidates:
        raise ValueError("selection must be a retained legal candidate")
    if not legal and (report["selection"] is not None or candidates):
        raise ValueError("terminal report cannot select a move")
    bases = {"expected_cp", "objective_fallback_mixed_scores", "objective_mate_win", "objective_mate_loss_delay", "terminal"}
    if report["selection_basis"] not in bases:
        raise ValueError("unknown selection basis")
    objective = report["objective"]
    depth = objective["depth"]
    if type(depth) is not int or depth < 1:
        raise ValueError("analysis requires positive integer depth")
    model = report["reply_model"]
    model_context = {key: value for key, value in model.items() if key != "positions"}
    positions = model.get("positions", [])
    if isinstance(positions, list):
        policies = {entry["fen"]: entry["probabilities"] for entry in positions}
        if len(policies) != len(positions):
            raise ValueError("duplicate reply-policy positions")
    elif isinstance(positions, dict):
        policies = positions
    else:
        raise ValueError("invalid reply-policy positions")
    ratings = {entry["active_rating"] for entry in positions} if isinstance(positions, list) else {model["rating"]}
    supplied_rating = report.get("opponent_rating")
    if len(ratings) > 1 or (supplied_rating is not None and ratings and ratings != {supplied_rating}):
        raise ValueError("inconsistent opponent ratings")
    rating = supplied_rating if supplied_rating is not None else next(iter(ratings), None)
    margin = _score(report["margin_cp"])
    if margin < 0:
        raise ValueError("negative margin")
    context = {"fen": report["fen"], "perspective": report["perspective"], "margin_cp": margin,
               "opponent_rating": rating, "model": model_context,
               "engine": {key: objective[key] for key in ("executable_sha256", "identity", "options")}}
    return depth, context, roots, candidates, policies


def compare_depths(reports):
    validated = sorted([(*validate_analysis(report), report) for report in reports], key=lambda item: item[0])
    if len(validated) < 2 or len({item[0] for item in validated}) != len(validated):
        raise ValueError("at least two distinct analysis depths are required")
    context = validated[0][1]
    if any(item[1] != context for item in validated[1:]):
        raise ValueError("position, engine, reply-model or rating contexts differ")
    seen_policies = {}
    for _, _, _, _, policies, _ in validated:
        for fen, probabilities in policies.items():
            if fen in seen_policies:
                previous = seen_policies[fen]
                if previous.keys() != probabilities.keys() or any(not isclose(
                        _score(previous[move]), _score(probability), rel_tol=0, abs_tol=1e-9)
                        for move, probability in probabilities.items()):
                    raise ValueError("reply predictions changed between depths for a shared position")
            seen_policies[fen] = probabilities
    transitions = []
    snapshots = []
    for depth, _, roots, candidates, _, report in validated:
        snapshots.append({"depth": depth, "selection": report["selection"],
                          "selection_basis": report["selection_basis"], "candidates": sorted(candidates),
                          "analysis_sha256": hashlib.sha256(json.dumps(report, sort_keys=True,
                              separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()})
    for before, after in zip(validated, validated[1:]):
        shallow, _, old_roots, old_candidates, _, old = before
        deep, _, new_roots, new_candidates, _, new = after
        changes = []
        for move in sorted(old_roots):
            old_score, new_score = old_roots[move], new_roots[move]
            if old_score != new_score:
                changes.append({"move": move, "before": old_score, "after": new_score,
                                "cp_delta": new_score["cp"] - old_score["cp"]
                                if old_score["kind"] == new_score["kind"] == "cp" else None})
        common = []
        for move in sorted(set(old_candidates) & set(new_candidates)):
            first, second = old_candidates[move], new_candidates[move]
            common.append({"move": move, "expected_cp_before": first["expected_cp"],
                           "expected_cp_after": second["expected_cp"],
                           "expected_cp_delta": second["expected_cp"] - first["expected_cp"]
                           if first["expected_cp"] is not None and second["expected_cp"] is not None else None})
        transitions.append({"from_depth": shallow, "to_depth": deep,
                            "selection_changed": old["selection"] != new["selection"],
                            "basis_changed": old["selection_basis"] != new["selection_basis"],
                            "added_candidates": sorted(set(new_candidates) - set(old_candidates)),
                            "removed_candidates": sorted(set(old_candidates) - set(new_candidates)),
                            "previous_selection_retained": old["selection"] in new_candidates if old["selection"] else None,
                            "root_score_changes": changes, "common_candidate_changes": common})
    return {"schema": "trickfish.practical-stability.v1", "context": context,
            "digest_format": "sha256 of UTF-8 json.dumps with sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False",
            "snapshots": snapshots, "transitions": transitions,
            "limitations": ["descriptive depth sensitivity, not confidence or playing strength",
                            "matching recorded context is not a complete environment certificate"]}


def render_stability(comparison):
    lines = ["# Practical depth sensitivity", "", "FEN: `" + comparison["context"]["fen"] + "`", "",
             "| Depth | Selection | Basis | Retained candidates |", "| ---: | --- | --- | ---: |"]
    for item in comparison["snapshots"]:
        lines.append(f"| {item['depth']} | {item['selection'] or 'none'} | {item['selection_basis']} | {len(item['candidates'])} |")
    for item in comparison["transitions"]:
        lines += ["", f"## Depth {item['from_depth']} to {item['to_depth']}", "",
                  "Selection changed: " + str(item["selection_changed"]) + ". Basis changed: " + str(item["basis_changed"]) + ".", "",
                  "Added candidates: " + (", ".join(item["added_candidates"]) or "none") + ".", "",
                  "Removed candidates: " + (", ".join(item["removed_candidates"]) or "none") + ".", "",
                  "Root scores changed: " + str(len(item["root_score_changes"])) + "."]
    lines += ["", "These are observations at finite depths, not evidence of improvement, calibrated confidence or playing strength.",
              "Candidate sets can change even when the selected move does not. Inspect the JSON and source analyses.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trickfish-practical-stability")
    parser.add_argument("analyses", nargs="+", type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or (args.report and (args.report.exists() or args.report.resolve() == args.output.resolve())):
            raise ValueError("output paths must be separate new files")
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.analyses]
        result = compare_depths(reports)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        if args.report:
            with args.report.open("x", encoding="utf-8") as stream:
                stream.write(render_stability(result))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
