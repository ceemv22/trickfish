# Practical selection prototype

`trickfish.practical.rank_practical_moves` implements an offline one-reply selection boundary. It does not change engine search or UCI move selection. An external UCI objective adapter and JSON analysis command are available. Maia is not connected yet; reply-model tests use explicitly synthetic providers and establish algorithm behavior only.

The objective evaluator receives a position and the original mover's color. Every score must be finite centipawns in that fixed perspective, including scores after the opponent replies. Adapters must handle terminal results explicitly and must not pass mate-distance encodings as centipawns. A finite number alone cannot prove that an adapter uses the correct units or perspective.

All legal root moves are evaluated. Only moves within `margin_cp` of the best objective score survive. For each surviving move, the reply model receives the successor position and a positive opponent-rating parameter. Its distribution must contain exactly all legal reply UCI strings, including zero-probability replies, with finite probabilities in [0, 1] summing to one within 1e-9. Invalid distributions fail rather than being silently normalized or truncated. Rating support and calibration are the adapter's responsibility.

For candidate m and reply r, the implementation computes:

```text
objective_loss(m) = best_objective - objective(m)
expected(m) = sum(P(r | after m, rating) * objective(after m, r))
trap(m) = expected(m) - objective(m)
```

Candidates are ordered by expected score, then objective score, then UCI string for deterministic ties. Trap score is reported separately: a large difference is not enough to select a move with a worse expected outcome. No-reply successors retain their objective score without calling the reply model; terminal roots return no candidates. Providers must adjudicate draws with legal moves. Position-only inputs do not carry repetition history, so this interface does not certify history-dependent game outcomes.

The tests exercise objective-margin exclusion, an alternative candidate favored by expected value, a certain adequate defense removing speculative benefit, black-root score orientation, terminal positions, and rejected probability/evaluation inputs. They do not measure human prediction accuracy, practical strength or Elo.

Next integration steps are a versioned human-reply adapter and held-out evaluation using the exported analysis evidence. Observational game results require controls for player strength and position selection; they are not automatically a paired causal experiment. No external model, executable, dataset, or license decision is bundled by this prototype.

## External objective and analysis export

From a checkout with `PYTHONPATH=src`, run:

```powershell
python -m trickfish.practical_cli --engine C:/engines/stockfish.exe --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" --replies replies.json --rating 1500 --depth 10 --margin-cp 30 --output analysis.json
```

The engine executable is supplied by the user and runs as a separate process. No shell command string is evaluated. `--engine-arg` can be repeated for engines requiring arguments. A new engine session uses its own defaults, and `ucinewgame`/`isready` precede every uncached evaluation. This first adapter does not configure engine strength, hash, threads, networks or tablebases. Use a full-strength engine binary with suitable defaults. Node budgets and controlled engine options remain future work.

The adapter waits for handshake/readiness, requests fixed depth, and requires the final main-PV score to be exact centipawns at at least that depth plus a legal bestmove. Bound-only, shallow and mate results fail the whole analysis. Checkmates are explicitly unsupported by this centipawn-only research objective; no arbitrary large score is substituted. Stalemate and insufficient-material positions score zero. Fifty-move claims, repetition history and automatic move-count draws are not adjudicated by this interface. Timeout, premature exit and malformed analysis fail with process cleanup. Timeout applies to each protocol operation, not the whole campaign.

`replies.json` is an object containing:

- `schema`: `trickfish.reply-distributions.v1`
- `rating`: the exact requested integer rating
- `source`: a nonempty description identifying the supplied model/version or synthetic baseline
- `positions`: a mapping from complete successor FEN strings to complete legal UCI-reply probability mappings

Distributions must be present for every objectively retained root move. Missing positions fail; there is no silent uniform fallback. The source label is user-supplied metadata, not a certification of human calibration. The core validates legal coverage and mass when a distribution is used. Full FEN keys include clocks and en-passant fields. A future Maia adapter must record the actual model checkpoint and preprocessing rather than merely labeling arbitrary probabilities as Maia.

The output schema `trickfish.practical-analysis.v1` records the root FEN, original mover perspective, margin, all accepted candidate scores, positive-probability reply details, raw final UCI score lines, engine identity/command/executable SHA-256, depth, and the source-file SHA-256 plus used reply distributions. Existing output files are refused. The receipt does not hash external engine networks, libraries or script arguments and therefore is not a complete reproducible environment certificate. Uncached cost is roughly all legal root moves plus positive-probability replies to retained candidates; this can be expensive. Per-position caching avoids evaluating the same full FEN twice within one analysis.

Local integration smoke uses the project's native C++ UCI executable at depth one with explicitly synthetic uniform responses. It exercises a real process and JSON output; it is not a Stockfish integration certification or human-strength experiment. Unit process fixtures separately exercise bounds, mate, shallow output, illegal bestmove, EOF, timeout and score orientation. The next product-facing milestone is a real versioned human-model adapter and held-out position analyses reviewed by prospective coaches or creators. Payment readiness is not inferred from passing these tests.
