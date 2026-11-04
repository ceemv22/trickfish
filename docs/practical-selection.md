# Practical selection prototype

`trickfish.practical_analysis.analyze_practical_moves` implements an offline one-reply selection boundary with typed centipawn and mate scores. It does not change engine search or UCI move selection. An external UCI objective adapter, optional Maia-2 reply adapter, JSON analysis command and Markdown review export are available. Integration examples are a manual-review set, not evidence of human calibration or playing strength. The older `trickfish.practical.rank_practical_moves` remains a centipawn-only library interface.

The objective evaluator receives a position and the original mover's color. `ObjectiveScore` contains either finite centipawns or a nonnegative mate distance with an explicit winning/losing flag in that fixed perspective. Explicit winner information preserves terminal mate-zero orientation. `UciObjective.evaluate` returns this typed value; the legacy callable interface returns cp only and still rejects mate scores. A finite number alone cannot prove that an adapter uses the correct units or perspective.

All legal root moves are evaluated and retained in the objective evidence. If any report winning mate, the shortest reported winning mate is selected without a human-model query. If every move reports losing mate, the longest reported distance is selected, with no claim of an expected-score optimization. Otherwise losing-mate root moves are excluded and cp candidates within `margin_cp` of the best finite objective score survive. For each surviving cp candidate, the reply model receives the successor position and a positive opponent-rating parameter. Its distribution must contain exactly all legal reply UCI strings, including zero-probability replies, with finite probabilities in [0, 1] summing to one within 1e-9. Invalid distributions fail rather than being silently normalized or truncated. Rating support and calibration are the adapter's responsibility.

For candidate m and reply r, the implementation computes:

```text
objective_loss(m) = best_objective - objective(m)
expected(m) = sum(P(r | after m, rating) * objective(after m, r))
trap(m) = expected(m) - objective(m)
```

When every positive-probability reply outcome is cp, candidates are ordered by expected cp, then objective cp, then UCI string. Trap score is reported separately: a large difference is not enough to select a move with a worse expected outcome. If any retained candidate has mate reply mass, its expected/trap cp values are null, mate-win/loss masses are reported separately, and selection falls back to the objectively best cp move across retained candidates. That fallback is not a practical comparison of mixed scores. The finite `cp_component` is only the probability-weighted contribution of cp replies, not a mixed-outcome expectation. Zero-probability replies are not evaluated. No-reply cp successors retain their objective score; terminal roots return no candidates and an explicit typed terminal score. Position-only inputs do not carry repetition history, so this interface does not certify history-dependent game outcomes.

The tests exercise objective-margin exclusion, an alternative candidate favored by expected value, a certain adequate defense removing speculative benefit, black-root score orientation, terminal positions, and rejected probability/evaluation inputs. They do not measure human prediction accuracy, practical strength or Elo.

Further validation requires held-out evaluation using the exported analysis evidence. Observational game results require controls for player strength and position selection; they are not automatically a paired causal experiment. No external model, executable, dataset, or license decision is bundled by this prototype.

## External objective and analysis export

From a checkout with `PYTHONPATH=src`, run:

```powershell
python -m trickfish.practical_cli --engine C:/engines/stockfish.exe --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" --replies replies.json --rating 1500 --depth 10 --margin-cp 30 --output analysis.json
```

The engine executable is supplied by the user and runs as a separate process. No shell command string is evaluated. `--engine-arg` can be repeated for engines requiring arguments. A new engine session uses its own defaults, and `ucinewgame`/`isready` precede every uncached evaluation. This first adapter does not configure engine strength, hash, threads, networks or tablebases. Use a full-strength engine binary with suitable defaults. Node budgets and controlled engine options remain future work.

The adapter waits for handshake/readiness, requests fixed depth, and requires the final main-PV score to be exact cp or mate at at least that depth plus a legal bestmove. Bound-only and shallow results fail the analysis. Mate distances remain typed and are not converted to large cp constants. Mate zero is accepted only for an actual terminal checkmate, detected before searching. Stalemate and insufficient-material positions score zero. Fifty-move claims, repetition history and automatic move-count draws are not adjudicated by this interface. Timeout, premature exit and malformed analysis fail with process cleanup. Timeout applies to each protocol operation, not the whole campaign.

`replies.json` is an object containing:

- `schema`: `trickfish.reply-distributions.v1`
- `rating`: the exact requested integer rating
- `source`: a nonempty description identifying the supplied model/version or synthetic baseline
- `positions`: a mapping from complete successor FEN strings to complete legal UCI-reply probability mappings

Distributions must be present for every objectively retained root move. Missing positions fail; there is no silent uniform fallback. The source label is user-supplied metadata, not a certification of human calibration. The core validates legal coverage and mass when a distribution is used. Full FEN keys include clocks and en-passant fields. The optional Maia adapter records its actual checkpoint and package version separately from this supplied-file provider.

The CLI now emits `trickfish.practical-analysis.v2`, with explicit score kinds, nullable cp fields, all root evaluations, selection and selection basis, typed reply outcomes and mate reply masses. The report also records root FEN, original mover perspective, margin, raw final UCI lines, engine identity/command/executable SHA-256, depth and reply-model provenance. Consumers of v1 must migrate rather than treating nullable cp fields as numeric values. The Markdown renderer still accepts older v1 reports. Existing output files are refused. The receipt does not hash external engine networks, libraries or script arguments and therefore is not a complete reproducible environment certificate. Uncached cost is roughly all legal root moves plus positive-probability replies to retained cp candidates; this can be expensive. Per-position caching avoids evaluating the same full FEN twice within one analysis.

## Maia-2 and coach review

Maia inference is optional. Use Python 3.11 or 3.12 and install `maia2==0.11.0` in an isolated environment, or install this project's `practical` extra. The reference engine and recorded-distribution CLI do not require Torch or Maia. Python 3.13 and later are not supported by this Maia package release; the extra's environment marker does not imply support there.

```powershell
python -m trickfish.practical_cli --engine C:/engines/stockfish.exe --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" --maia rapid --maia-cache C:/models/maia2 --rating 1500 --player-rating 1700 --depth 6 --output analysis.json --report analysis.md
```

`--replies` and `--maia` are mutually exclusive. Maia requires an explicit cache directory and the original player's rating. After a candidate, the opponent is the active player: `--rating` is passed as Maia's active rating, while `--player-rating` is passed as the other player's rating. Maia handles black-board mirroring internally; the adapter does not mirror again. The separate White expected-score output is ignored rather than treated as a move probability or objective evaluation.

The official loader downloads or validates the selected Rapid/Blitz checkpoint in the supplied directory. Model files and dependencies are not vendored. The receipt records package version, checkpoint SHA-256, requested device, model kind, both ratings, raw and normalized distributions and raw mass. Maia-2 uses coarse rating buckets (below 1100, 100-point buckets through 1999, and 2000+); changing a rating within the same bucket is not finer personalization. The adapter requires exact legal-move coverage. Its public inference API rounds probabilities to four decimals, so only rounding-sized mass error is normalized, with the original values retained. Gross mass errors fail. Rounding can discard very small probabilities; this prototype does not recover the unrounded logits.

The Markdown companion distinguishes the objectively best evaluated move from the expected-score selection and lists candidate scores and reply probabilities/results. Expected-minus-objective can include finite-depth horizon effects and is not an estimate of extra win rate. Output files must be new. If a later report write fails, an already written JSON file can remain; inspect it before retrying with new paths.

`examples/practical-positions.json` contains move-replayable ordinary and trap/defense positions. Run the review set with:

```powershell
python examples/run_practical_review.py --engine C:/engines/stockfish.exe --maia-cache C:/models/maia2 --output-dir review --depth 6
```

`--case initial` runs just one case. The output directory must be new. Each case runs in its own process and produces JSON/Markdown or a recorded rejection in `summary.json`. Typed mate results no longer fail the current CLI; the legacy cp-only callable still rejects them. A completed report can explicitly use an objective fallback instead of a practical ranking. A failed case is not a successful analysis.

The manual `Practical Integration` Actions workflow defaults to all five cases, installs the optional model, uses the runner's packaged Stockfish, and preserves review outputs. It does not run on ordinary pushes, certify model calibration, or establish strength. Its Stockfish version can differ from local runs and is recorded in the receipt. Model download availability is an external dependency.

Sources: [official Maia-2 inference interface](https://github.com/CSSLab/maia2/tree/67bee6ce7e2f264344fe6d2026a2e18c76a82efa), [official Stockfish releases](https://github.com/official-stockfish/Stockfish/releases). Maia upstream now recommends Maia-3 for new projects; this adapter deliberately implements the agreed Maia-2 experiment and pins its API rather than silently substituting another model. No commercial benefit has been established.

### Local integration observations

In the earlier v1 run on 2026-11-04, Windows Stockfish 19 and Maia-2 0.11.0 Rapid completed the initial, quiet Italian, Stafford-entry and Englund-entry cases at depth four, rating 1500 for both players and margin 30 cp. The Scholar's Mate defense case was rejected on an unsupported mate score; the review command correctly returned failure for the full set. Four successes and one rejection were not a fully passing integration set. Those accepted analyses contained 479 unique objective evaluations in total, and their exported positive-probability reply sums were checked against every reported expectation. These shallow runs establish an integration path only. They are not recommendation-quality, calibration or strength evidence.

After typed mate handling, the same five-case depth-four review completed all five cases locally with Stockfish 19 / Maia Rapid and 606 unique objective evaluations in total. The Scholar defense case recorded 22 losing-mate root moves and retained three cp candidates; the selected move was g7g6. All reported finite expectations were independently recomputed from exported reply distributions/outcomes. Mixed mate/cp fallback and mate-zero perspective behavior are covered separately by synthetic regressions, not inferred from a case that happened to retain only cp outcomes. All 116 local Python tests pass. These results do not replace the manual Actions integration run or establish recommendation quality at greater depths.

The downloaded Stockfish archive SHA-256 was `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`, checked against the official release asset digest. The Rapid checkpoint SHA-256 was `65aae8465eed5e65df66a24ea7370715579f9e5435098d06fe18bdb1e267e997`, matching the official loader. Local inference used Torch 2.8.0 CPU; the review subprocesses set `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1`. Repeated fresh-position depth-four Stockfish evaluation of the initial position returned 23 cp twice; a black-to-move position returned 32 cp for Black and -32 for White. Terminal and searched mate results were both rejected explicitly. This is a small repeatability check, not a determinism guarantee across engines or machines. The optional integration Actions workflow still needs a separate manual run after push.

An earlier local integration smoke used the project's native C++ UCI executable at depth one with explicitly synthetic uniform responses. It exercises a real process and JSON output; it is not a Stockfish integration certification or human-strength experiment. Unit process fixtures separately exercise bounds, mate, shallow output, illegal bestmove, EOF, timeout and score orientation. The next product-facing milestone is held-out position analyses reviewed by prospective coaches or creators. Payment readiness is not inferred from passing these tests.

## Depth sensitivity

Run the same review set at multiple distinct positive depths with `--depths 4 6` instead of `--depth`. Analyses are placed in `depth-4/`, `depth-6/` and per-case comparisons in `comparison/`. A failed analysis prevents that case's comparison and makes the command fail; it is not counted as a stable recommendation. Single-depth invocation retains the existing flat output layout. The manual Practical Integration workflow now defaults to comparison `4,6` for all cases. Its `depth` input applies only when `comparison` is `single`.

Existing v2 reports can also be compared without rerunning models:

```powershell
python -m trickfish.practical_stability depth-4/initial.json depth-6/initial.json --output initial-comparison.json --report initial-comparison.md
```

Comparisons require the same full FEN, perspective, margin, recorded engine executable hash/identity/options, reply-model metadata and opponent rating. A report must include every legal root move exactly once and select a retained legal candidate, or no move for a terminal root. The comparator rejects repeated depths, conflicting typed root/candidate evidence, and changed reply distributions for shared positions (absolute tolerance 1e-9). An added `opponent_rating` field records this setting explicitly; older v2 reports can infer it from used reply-model evidence. Different model-used position subsets are expected as candidate sets change. Matching recorded metadata is not proof of an identical complete runtime: external engine networks and library environments can still be incompletely captured.

`trickfish.practical-stability.v1` records depth snapshots, changed selections/bases, added/removed candidates, root score changes and finite expected-cp changes for common candidates. Mate transitions do not receive cp deltas. Each snapshot includes a SHA-256 of the complete source analysis serialized as sorted compact JSON (ASCII escaping enabled, non-finite values forbidden), independent of source filename/whitespace. This is a content fingerprint, not an authenticity signature. The tool does not assign confidence, infer improvement or declare readiness from a fixed threshold.

The local five-position review with Stockfish 19 / Maia Rapid, rating 1500 for both players and margin 30 cp completed at depths four and six. Selections were:

| Case | Depth 4 | Depth 6 |
| --- | --- | --- |
| Initial | e2e4 | e2e4 |
| Quiet Italian | c2c3 | c2c3 |
| Stafford entry | d2d3 | f2f3 |
| Englund entry | e2e4 | c1g5 |
| Scholar defense | g7g6 | d8e7 |

Selection changed in three of five cases, and retained candidate sets changed in all five. These are descriptive observations on a repeatedly inspected integration set, not held-out calibration or evidence that depth six is adequate. All 122 local Python tests pass, including incompatible-context, incomplete-root, changed-policy, candidate-boundary and mate-transition regressions. The automated two-depth review runner was additionally exercised on the initial position with the actual external components. New Python CI and the manual optional-model workflow require their own post-push results.

The manual integration boundary at `af9aea2` subsequently passed in [Practical Integration run 41900440242](https://github.com/ceemv22/trickfish/actions/runs/41900440242). Its Linux runner completed all ten analyses (five cases at depths four/six), comparisons and artifact upload. Artifact `13356069722` preserves the review outputs. This validates that commit's external-component integration, not later unpushed changes or recommendation quality.

A further local Stockfish 19 / Maia Rapid depth-eight run completed all five cases under the same recorded model/rating settings. Compared with depth six, Stafford changed from f2f3 to d2d3 and Englund from c1g5 to c1f4; initial e2e4, Italian c2c3 and Scholar defense d8e7 remained selected. Two of five selections still changed. This remains an inspected integration set and does not establish a minimum sufficient depth or human benefit.

## Replayed objective continuations

New objective evaluations require a nonempty PV on the final exact score line, beginning with the final legal bestmove. Every PV move is replayed through the Python legal move generator using actual Move objects, preserving castling, en-passant and promotion flags. Invalid or missing PVs fail with engine-process cleanup. This adapter reads the PV move list from the tail of the final score line, as emitted by Stockfish; engines using other layouts are not certified by this integration. The replay checks legality, not optimality, history-dependent adjudication, or a complete mate proof.

Nonterminal objective receipts add `pv` and `pv_final_fen`. `UciObjective.continuation` returns an evaluated position's immutable UCI continuation without another search; terminal scores have an empty continuation. Practical v2 candidates add `objective_pv` (starting after our candidate), and positive-probability reply details add `pv` (starting after the opponent's specified reply). The Markdown report displays both with explicit starting context. Older v2 reports without these additive fields remain renderable, with unavailable continuations marked accordingly. A PV can be shorter than the requested search depth or reported mate distance; it is an engine-reported legal prefix, not a guaranteed full line.

All 126 local Python tests pass, including missing/mismatched/illegal-tail PV process regressions and golden-FEN replay fixtures for special moves. A real Stockfish 19 / Maia Rapid depth-six Scholar-defense report was generated with continuations. Independent python-chess replay validated 366 PV plies across 89 objective records, including final FENs; exported finite expectations were also recomputed. This continuation follow-up requires its own post-push CI, separate from the accepted `af9aea2` run.
