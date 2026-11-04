def render_report(report):
    if report.get("schema") == "trickfish.practical-analysis.v2":
        return _render_typed_report(report)
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


def _display_score(score):
    if score["kind"] == "cp":
        return f"{score['cp']:.2f} cp"
    return ("mate win in " if score["winning"] else "mate loss in ") + str(score["mate_moves"])


def _render_typed_report(report):
    lines = ["# Trickfish practical analysis", "", "FEN: `" + report["fen"] + "`", "",
             "All scores use the original mover's perspective (" + report["perspective"] + ").",
             "", "Objective engine: " + ", ".join(report["objective"]["identity"]),
             "", "Reply source: " + report["reply_model"]["source"], "",
             "Selection: **" + (report["selection"] or "none") + "**.", "",
             "Selection basis: `" + report["selection_basis"] + "`.", ""]
    if report["selection_basis"] == "objective_fallback_mixed_scores":
        lines += ["Mate and cp reply outcomes are not averaged together. Selection falls back to the best objective cp move; this is not a practical ranking of the mixed candidates.", ""]
    elif report["selection_basis"].startswith("objective_mate"):
        lines += ["Selection follows engine-reported mate distance, not an expected-centipawn calculation.", ""]
    if "terminal_score" in report:
        lines += ["Terminal score: " + _display_score(report["terminal_score"]), ""]
    lines += ["| Candidate | Objective | Expected cp | Mate-win reply mass | Mate-loss reply mass |",
              "| --- | --- | ---: | ---: | ---: |"]
    for item in report["candidates"]:
        expected = "n/a" if item["expected_cp"] is None else f"{item['expected_cp']:.2f}"
        win = "n/a" if "mate_win_probability" not in item else f"{item['mate_win_probability']:.4%}"
        loss = "n/a" if "mate_loss_probability" not in item else f"{item['mate_loss_probability']:.4%}"
        lines.append(f"| {item['move']} | {_display_score(item['objective'])} | {expected} | {win} | {loss} |")
    for item in report["candidates"]:
        lines += ["", "### Replies after " + item["move"], "",
                  "Objective continuation after the candidate (UCI): " +
                  ("`" + " ".join(item["objective_pv"]) + "`" if item.get("objective_pv") else "not available") + ".", "",
                  "| Reply | Model probability | Objective outcome | Continuation after reply (UCI) |", "| --- | ---: | --- | --- |"]
        for reply in sorted(item["reply_details"], key=lambda value: (-value["probability"], value["move"])):
            pv = "`" + " ".join(reply["pv"]) + "`" if reply.get("pv") else "not available"
            lines.append(f"| {reply['move']} | {reply['probability']:.4%} | {_display_score(reply['score'])} | {pv} |")
        lines += [""]
    lines += ["## All objective root evaluations", "", "| Move | Objective |", "| --- | --- |"]
    lines += [f"| {item['move']} | {_display_score(item['score'])} |" for item in report["root_evaluations"]]
    lines += ["", "Mate reply mass is model probability of reaching an engine-reported mate outcome, not a calibrated game win probability.",
              "Displayed continuations are legal engine PV prefixes, not proofs of optimality or necessarily complete mate lines.",
              "Finite depth and horizon effects remain. See the JSON evidence; repetition history is unavailable.", ""]
    return "\n".join(lines)
