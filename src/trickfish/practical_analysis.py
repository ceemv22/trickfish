from math import fsum, isclose

from .objective_score import ObjectiveScore
from .practical import _score


def analyze_practical_moves(position, evaluator, reply_model, rating, margin_cp=30):
    margin_cp = _score(margin_cp)
    if margin_cp < 0 or type(rating) is not int or rating <= 0:
        raise ValueError("nonnegative margin and positive integer rating required")
    perspective = position.side_to_move

    def evaluate(child):
        score = evaluator(child, perspective)
        if not isinstance(score, ObjectiveScore):
            raise ValueError("typed objective score required")
        return score

    roots = [(move, position.make_move(move)) for move in position.legal_moves()]
    scored = [(move, child, evaluate(child)) for move, child in roots]
    root_evaluations = [{"move": move.to_uci(), "score": score.as_dict()} for move, _, score in scored]
    if not scored:
        return {"candidates": [], "root_evaluations": [], "selection": None, "selection_basis": "terminal",
                "terminal_score": evaluate(position).as_dict()}
    wins = [entry for entry in scored if entry[2].winning is True]
    finite = [entry for entry in scored if entry[2].cp is not None]
    if wins or not finite:
        ordered = sorted(wins or scored, key=lambda item: (
            item[2].mate_moves if wins else -item[2].mate_moves, item[0].to_uci()))
        candidates = [{"move": move.to_uci(), "objective": score.as_dict(), "objective_cp": None,
                       "objective_loss_cp": None, "expected_cp": None, "trap_cp": None, "reply_details": []}
                      for move, _, score in ordered]
        return {"candidates": candidates, "root_evaluations": root_evaluations,
                "selection": candidates[0]["move"],
                "selection_basis": "objective_mate_win" if wins else "objective_mate_loss_delay"}
    best = max(score.cp for _, _, score in finite)
    candidates = []
    for move, child, score in finite:
        loss = best - score.cp
        if loss > margin_cp:
            continue
        replies = {reply.to_uci(): reply for reply in child.legal_moves()}
        details = []
        if replies:
            probabilities = dict(reply_model(child, rating))
            if probabilities.keys() != replies.keys():
                raise ValueError("reply probabilities must cover exactly all legal replies")
            probabilities = {key: _score(value) for key, value in probabilities.items()}
            if any(not 0 <= value <= 1 for value in probabilities.values()) or not isclose(
                    fsum(probabilities.values()), 1, rel_tol=0, abs_tol=1e-9):
                raise ValueError("invalid reply probability mass")
            for uci, probability in probabilities.items():
                if probability > 0:
                    outcome = evaluate(child.make_move(replies[uci]))
                    details.append({"move": uci, "probability": probability,
                                    "score": outcome.as_dict(), "cp_original_mover": outcome.cp})
        win_mass = fsum(item["probability"] for item in details if item["score"]["winning"] is True)
        loss_mass = fsum(item["probability"] for item in details if item["score"]["winning"] is False)
        cp_component = fsum(item["probability"] * item["score"]["cp"] for item in details if item["score"]["cp"] is not None)
        expected = None if win_mass or loss_mass else _score(cp_component if replies else score.cp)
        candidates.append({"move": move.to_uci(), "objective": score.as_dict(), "objective_cp": score.cp,
                           "objective_loss_cp": loss, "expected_cp": expected,
                           "trap_cp": None if expected is None else expected - score.cp,
                           "mate_win_probability": win_mass, "mate_loss_probability": loss_mass,
                           "cp_component": cp_component if replies else score.cp, "reply_details": details})
    mixed = any(candidate["expected_cp"] is None for candidate in candidates)
    if mixed:
        candidates.sort(key=lambda item: (-item["objective_cp"], item["move"]))
    else:
        candidates.sort(key=lambda item: (-item["expected_cp"], -item["objective_cp"], item["move"]))
    return {"candidates": candidates, "root_evaluations": root_evaluations,
            "selection": candidates[0]["move"],
            "selection_basis": "objective_fallback_mixed_scores" if mixed else "expected_cp"}
