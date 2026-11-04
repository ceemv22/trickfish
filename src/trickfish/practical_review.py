import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from math import fsum, isclose
import pathlib

from .practical import _score
from .practical_pgn import render_practical_pgn, render_nominee_probe
from .practical_stability import compare_depths
from .position import Position
from .variation import replay_uci_line


@dataclass(frozen=True)
class ReviewPolicy:
    minimum_screen_depth: int = 8
    minimum_verification_depth: int = 12
    maximum_objective_loss_cp: float = 30
    minimum_modeled_advantage_cp: float = 10

    def __post_init__(self):
        if (type(self.minimum_screen_depth) is not int or type(self.minimum_verification_depth) is not int or
                not 0 < self.minimum_screen_depth < self.minimum_verification_depth):
            raise ValueError("review depths must be positive increasing integers")
        if _score(self.maximum_objective_loss_cp) < 0 or _score(self.minimum_modeled_advantage_cp) < 0:
            raise ValueError("review score thresholds must be nonnegative")


def _verify_expectations(report):
    for candidate in report["candidates"]:
        replies = candidate["reply_details"]
        if not replies:
            continue
        probabilities = [_score(reply["probability"]) for reply in replies]
        if any(not 0 < probability <= 1 for probability in probabilities) or not isclose(
                fsum(probabilities), 1, rel_tol=0, abs_tol=1e-9):
            raise ValueError("invalid source reply mass")
        mixed = any(reply["score"]["kind"] == "mate" for reply in replies)
        if mixed:
            if candidate["expected_cp"] is not None or candidate["trap_cp"] is not None:
                raise ValueError("mixed outcomes cannot supply expected cp")
        else:
            expected = fsum(reply["probability"] * _score(reply["score"]["cp"]) for reply in replies)
            if candidate["expected_cp"] is None or not isclose(_score(candidate["expected_cp"]), expected, rel_tol=0, abs_tol=1e-8):
                raise ValueError("reported expectation disagrees with reply evidence")
    if report["selection_basis"] == "expected_cp" and report["candidates"]:
        if any(item["expected_cp"] is None or item["objective"]["cp"] is None for item in report["candidates"]):
            raise ValueError("expected-cp selection contains unrankable outcomes")
        ranked = sorted(report["candidates"], key=lambda item: (-_score(item["expected_cp"]),
                        -_score(item["objective"]["cp"]), item["move"]))
        if ranked[0]["move"] != report["selection"]:
            raise ValueError("reported selection disagrees with expected-cp ranking")


def assess_review(screen, verification, policy=ReviewPolicy()):
    comparison = compare_depths([screen, verification])
    if screen["objective"]["depth"] >= verification["objective"]["depth"]:
        raise ValueError("verification depth must exceed screening depth")
    _verify_expectations(screen)
    _verify_expectations(verification)
    render_practical_pgn(verification, 0)
    nominee = screen["selection"]
    if nominee is not None:
        render_nominee_probe(verification, nominee)
    reasons = []
    if screen["objective"]["depth"] < policy.minimum_screen_depth or verification["objective"]["depth"] < policy.minimum_verification_depth:
        reasons.append("insufficient_depth")
    if screen["selection"] != verification["selection"]:
        reasons.append("selection_changed")
    if screen["selection_basis"] != "expected_cp" or verification["selection_basis"] != "expected_cp":
        reasons.append("not_expected_cp_selection")
    roots = {item["move"]: item["score"] for item in verification["root_evaluations"]}
    finite = {move: score["cp"] for move, score in roots.items() if score["kind"] == "cp"}
    winning_mates = any(score["kind"] == "mate" and score["winning"] for score in roots.values())
    best_move = min(finite, key=lambda move: (-finite[move], move)) if finite and not winning_mates else None
    if best_move is not None:
        render_nominee_probe(verification, best_move)
    def defense_pv(move):
        if move is None:
            return []
        child = replay_uci_line(Position.from_fen(verification["fen"]), [move])
        return next(record.get("pv", []) for record in verification["objective"]["evaluations"] if record["fen"] == child.to_fen())
    loss = None
    advantage = None
    if nominee not in finite or best_move is None:
        reasons.append("mate_or_terminal_objective")
    else:
        loss = finite[best_move] - finite[nominee]
        if loss > min(policy.maximum_objective_loss_cp, verification["margin_cp"]):
            reasons.append("objective_margin_failed")
        if loss == 0:
            reasons.append("objective_baseline")
        retained = {item["move"]: item for item in verification["candidates"]}
        if nominee not in retained or best_move not in retained:
            reasons.append("candidate_not_retained")
        else:
            selected_expected = retained[nominee]["expected_cp"]
            baseline_expected = retained[best_move]["expected_cp"]
            if selected_expected is None or baseline_expected is None:
                reasons.append("mixed_outcome_comparison")
            else:
                advantage = selected_expected - baseline_expected
                if advantage < policy.minimum_modeled_advantage_cp:
                    reasons.append("insufficient_modeled_advantage")
    retained = {item["move"]: item for item in verification["candidates"]}
    replies = retained.get(nominee, {}).get("reply_details", [])
    return {"schema": "trickfish.expert-review.v1", "fen": verification["fen"],
            "policy": asdict(policy), "screening_depth": screen["objective"]["depth"],
            "verification_depth": verification["objective"]["depth"], "nominee": nominee,
            "verification_selection": verification["selection"], "objective_best_finite_move": best_move,
            "nominee_defense_pv": defense_pv(nominee), "objective_choice_defense_pv": defense_pv(best_move),
            "top_model_replies": sorted(replies, key=lambda item: (-item["probability"], item["move"]))[:3],
            "verified_objective_loss_cp": loss, "modeled_advantage_over_objective_cp": advantage,
            "status": "review_candidate" if not reasons else "needs_review", "reasons": reasons,
            "comparison": comparison,
            "limitations": ["engineering triage, not validated human benefit or payment readiness",
                            "finite-depth verification and model expectations remain uncertain"]}


def render_review(review):
    labels = {"insufficient_depth": "Analysis is below the recorded depth threshold",
              "selection_changed": "The selected move changed in the deeper run",
              "not_expected_cp_selection": "Selection does not use comparable expected centipawn outcomes",
              "mate_or_terminal_objective": "Mate or terminal outcomes require a separate assessment",
              "objective_margin_failed": "The nominee exceeds the allowed objective loss",
              "objective_baseline": "The nominee is already an objective-best move, not a distinct practical alternative",
              "candidate_not_retained": "The nominee or baseline was removed by the deeper candidate filter",
              "mixed_outcome_comparison": "Mate and centipawn outcomes cannot be averaged together",
              "insufficient_modeled_advantage": "Modeled advantage is below the review threshold"}
    reasons = "; ".join(labels[reason] for reason in review["reasons"]) or "Recorded triage conditions are met; expert review is still required"
    title = "Candidate for expert review" if review["status"] == "review_candidate" else "Further review required"
    policy = review["policy"]
    loss = "unavailable" if review["verified_objective_loss_cp"] is None else f"{review['verified_objective_loss_cp']:.2f}"
    advantage = "unavailable" if review["modeled_advantage_over_objective_cp"] is None else f"{review['modeled_advantage_over_objective_cp']:.2f}"
    return "\n".join(["# Expert review worksheet", "", "FEN: `" + review["fen"] + "`", "",
                      "Status: **" + title + "**. " + reasons + ".", "",
                      f"Recorded thresholds: screening depth at least {policy['minimum_screen_depth']}, verification depth at least {policy['minimum_verification_depth']}, objective loss at most {policy['maximum_objective_loss_cp']} cp, modeled advantage at least {policy['minimum_modeled_advantage_cp']} cp.", "",
                      "Screening nominee: " + (review["nominee"] or "none") + ". Verification selection: " + (review["verification_selection"] or "none") + ".", "",
                      "Objective choice at verification depth: " + (review["objective_best_finite_move"] or "none") + ".", "",
                      "Verified objective loss cp: " + loss + ". Modeled advantage over objective baseline cp: " + advantage + ".", "",
                      "Engine defense after the nominee (UCI): `" + " ".join(review["nominee_defense_pv"]) + "`.", "",
                      "Engine defense after the objective choice (UCI): `" + " ".join(review["objective_choice_defense_pv"]) + "`.", "",
                      "Most probable modeled replies: " + "; ".join(f"{item['move']} ({item['probability']:.2%})" for item in review["top_model_replies"]) + ".", "",
                      "This worksheet does not establish improvement or commercial readiness. verification.pgn contains retained verification candidates; nominee.pgn separately checks the screening move, including when it was removed by the deeper filter.", "",
                      "Reviewer questions:", "", "- Is the best defense understandable and likely for the intended audience?",
                      "- Is the candidate sound under a stronger independent check?",
                      "- Does the explanation save preparation time?",
                      "- Would this line belong in a lesson or repertoire, and why?", "",
                      "Reviewer notes: ____________________", ""])


def main(argv=None):
    parser = argparse.ArgumentParser(prog="trickfish-practical-review")
    parser.add_argument("screen", type=pathlib.Path)
    parser.add_argument("verification", type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument("--policy", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise ValueError("review directory must be new")
        raw_screen = args.screen.read_bytes()
        raw_verified = args.verification.read_bytes()
        screen, verification = json.loads(raw_screen), json.loads(raw_verified)
        policy = ReviewPolicy(**json.loads(args.policy.read_text())) if args.policy else ReviewPolicy()
        review = assess_review(screen, verification, policy)
        review["source_files_sha256"] = {"screen": hashlib.sha256(raw_screen).hexdigest(),
                                        "verification": hashlib.sha256(raw_verified).hexdigest()}
        rendered = json.dumps(review, indent=2, allow_nan=False)
        pgn = render_practical_pgn(verification)
        nominee_pgn = render_nominee_probe(verification, review["nominee"]) if review["nominee"] is not None else None
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "assessment.json").write_text(rendered, encoding="utf-8")
        (args.output_dir / "worksheet.md").write_text(render_review(review), encoding="utf-8")
        (args.output_dir / "verification.pgn").write_text(pgn, encoding="utf-8")
        if nominee_pgn is not None:
            (args.output_dir / "nominee.pgn").write_text(nominee_pgn, encoding="utf-8")
        (args.output_dir / "screen.json").write_bytes(raw_screen)
        (args.output_dir / "verification.json").write_bytes(raw_verified)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(2, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
