def render_report(report):
    candidates = report["candidates"]
    identity = ", ".join(report["objective"]["identity"])
    model = report["reply_model"]["source"]
    lines = ["# Trickfish practical analysis", "", "FEN: `" + report["fen"] + "`", "",
             "Scores are centipawns from the original mover's perspective (" + report["perspective"] + ").",
             "", "Objective engine: " + identity, "", "Reply source: " + model, "",
             "This is a one-reply model expectation, not a measured win probability or a strength claim.", ""]
    if not candidates:
        return "\n".join(lines + ["No legal candidates.", ""])
    best = sorted(candidates, key=lambda item: (-item["objective_cp"], item["move"]))[0]
    lines += ["Objective best among evaluated legal moves: **" + best["move"] + "**.", "",
              "Practical selection under the supplied model: **" + candidates[0]["move"] + "**.", "",
              "| Move | Objective cp | Loss from best cp | Expected cp | Expected minus objective cp |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for candidate in candidates:
        lines.append("| {move} | {objective_cp:.2f} | {objective_loss_cp:.2f} | {expected_cp:.2f} | {trap_cp:.2f} |".format(**candidate))
    for candidate in candidates:
        lines += ["", "## Replies after " + candidate["move"], "",
                  "| Reply | Model probability | Resulting cp |", "| --- | ---: | ---: |"]
        for reply in sorted(candidate["reply_details"], key=lambda item: (-item["probability"], item["move"])):
            lines.append("| {move} | {probability:.4%} | {cp_original_mover:.2f} |".format(**reply))
    lines += ["", "Finite-depth evaluations can disagree across adjacent positions. A positive expected-minus-objective score can reflect horizon effects as well as predicted mistakes.",
              "", "The JSON companion contains raw evaluations and model provenance. Repetition history is unavailable.", ""]
    return "\n".join(lines)
