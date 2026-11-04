# Practical selection prototype

`trickfish.practical.rank_practical_moves` implements an offline one-reply selection boundary. It does not change engine search or UCI move selection. Stockfish and Maia are not connected yet; current tests use explicitly synthetic providers and establish algorithm behavior only.

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

Next integration steps are an external UCI objective adapter with explicit score/terminal handling, a versioned human-reply adapter, preserved analysis provenance and held-out evaluation. Observational game results require controls for player strength and position selection; they are not automatically a paired causal experiment. No external model, executable, dataset, or license decision is bundled by this prototype.
