# Coach demonstration walkthrough

This is a suggested 15-minute conversation using the supplied review package. Use it to collect critical feedback about preparation value and the proposed lines. The packet's technical results do not establish human benefit.

## Opening: two minutes

Explain the task: identify objectively acceptable opening lines that may be useful against a specified playing-strength audience. The packet combines an external objective engine and a pretrained human-move model; their scores and probabilities are not measured game results.

Ask which audience and opening family the coach prepares material for. Show the starting Italian position before revealing the tool's ranking, and ask which move or defense they would examine first. Record their answer without implying that agreement with the tool is the desired result.

## Proposed alternative: five minutes

Open `quiet-italian/worksheet.md`, then `quiet-italian/nominee.pgn` and `quiet-italian/verification.pgn` in the coach's chess viewer. The example position follows 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5.

The local Stockfish 19 / Maia Rapid run screened at depth 8 and checked at depth 12, with both requested ratings 1500. It retained 4.c3 as a review candidate. At verification depth it was 19 cp below the objective choice 4.d4, with modeled reply expectation 75.81 cp above that choice's expectation. These numbers belong to that local packet, not every engine version or future CI artifact. Use each packet's own worksheet if its results differ.

The subsequent Linux integration run with the runner's packaged Stockfish 16 completed all analyses but marked all five cases `needs_review`, including Italian. It did not reproduce a qualifying alternative under that configuration. Present the local Italian result as a configuration-dependent research example, not a robust recommendation. The runs use different objective engine versions, so this difference alone does not isolate its cause.

Walk through the engine's defense and the model's most probable responses. Ask whether the recommended line is sound under the coach's own analysis, whether its defenses are teachable, and whether the explanation is useful for the intended audience. A legal PV is not a proof of optimality or a complete mate line. Do not describe the modeled cp difference as extra Elo, a win-rate improvement or expected tournament points.

## Controls and limitations: four minutes

Open `initial/worksheet.md` to show a case that remained an objective baseline rather than a distinct practical alternative. Then open `scholar-threat-black-defense/worksheet.md` and its nominee-check PGN to inspect the changed recommendation. Do not hide rejected or uncertain cases.

Explain that this is a repeatedly inspected five-position integration set. Deeper searches changed choices in earlier runs, and neither useful human calibration nor a strength gain has been established. The coach should challenge the proposed candidate, not merely approve the presentation.

## Feedback and possible next engagement: four minutes

Ask the coach to complete the relevant `feedback.json` forms or dictate notes for later transcription. Keep answers unfilled until an actual review. If no time was saved, record zero or leave the estimate unknown and describe any extra work in notes. Hypothetical interest in a paid pilot is not a purchase.

Ask which exact preparation task, if any, would justify a small paid analysis. A possible scope to discuss is one agreed opening family, a fixed number of positions, objective baselines and rejected cases, PGN plus readable explanations, and a follow-up review. Agree scope, price and limitations separately before commissioning work. No price or willingness to pay has been validated by this packet.

After the conversation, preserve criticisms and uncertain answers alongside positive feedback. The next decision is whether to fix a demonstrated problem, run a different representative case, or offer an explicitly scoped pilot. More features are not automatically the right response.
