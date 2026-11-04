# Coach pilot guide

Purpose: find out whether these analyses help a coach or repertoire creator prepare useful material. This is a research pilot, not a proven strength product.

Start with `index.md`. Review the marked candidate and at least one objective baseline or rejected case. Open each worksheet and its PGN in your usual chess tool. The nominee-check PGN shows the deeper engine defense against the original proposal. Source analyses, policy and hashes remain available for inspection.

For each reviewed case, fill its `feedback.json` using a reviewer identifier of your choice. Leave unreviewed answers null and change status from `not_reviewed` to `reviewed` only after an actual review. Keep the FEN, nominee and assessment hash unchanged so the response remains attached to the exact analysis you saw. Use a separate package copy for each reviewer. No feedback is submitted automatically.

Suggested answer values:

- `soundness`: `sound`, `unsound`, or `uncertain`, after your own stronger check.
- `would_use`: `yes`, `no`, or `uncertain` for an actual lesson or repertoire.
- `minutes_saved`: your nonnegative estimate, or null if you cannot estimate it.
- `would_consider_paid_pilot`: `yes`, `no`, or `uncertain`; this is hypothetical interest, not a purchase.
- `reviewed_at_utc`: the actual review timestamp, or null until reviewed.
- `notes`: best defense, misleading lines, missing explanations and what would make the analysis useful.

Discuss these questions after the review:

1. Which line would you actually use, and for which audience?
2. What preparation did the packet save or create?
3. Would a narrowly specified paid analysis be useful, and what would it need to include?

Do not treat model probabilities as calibrated win rates, review-candidate status as proof of soundness, or a willingness-to-pay answer as revenue. This repeatedly inspected five-position set cannot establish general usefulness. Record negative results and uncertain judgments alongside positive feedback.

A paid pilot should have an agreed scope, deliverables, limitations and price before work is commissioned. This package itself sets no price, creates no subscription and makes no promise of improved game results. Broader product development should follow actual expert feedback and observed payment, rather than the number of passing tests.
