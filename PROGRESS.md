# C++ roadmap progress index

Baseline: `f9ac82b` (2026-10-02).

Implemented-scope index: **45.500%**. This is a planning index, not an estimate of playing strength, Elo, elapsed effort, or proximity to a world-class engine. The initial weights deliberately calibrate the index to the earlier rough 22% estimate; they are project planning choices, not measured costs.

The denominator is 100.000 points. The index is the sum of completed milestone weights. Three decimal places describe the arithmetic, not confidence in the weights. A documentation commit, refactor, or bug fix does not automatically earn points. Partial credit requires an explicit submilestone with an acceptance condition and a weight deducted from its parent. Submilestones must be recorded before implementation; do not assign credit retrospectively just to make the number rise.

Changing scope or weights requires a documented recalibration. Report its effect separately from implementation progress. Completion means the stated scope exists in C++; it does not mean all chess rules, performance targets, or acceptance tests are satisfied beyond that stated scope.

## Milestones

| ID | Scope and completion boundary | Weight | State |
| --- | --- | ---: | --- |
| C01 | FEN parsing and round-trip serialization | 2.000 | Implemented |
| C02 | Piece bitboards, mailbox, and cached side occupancy | 2.000 | Implemented |
| C03 | Reversible updates including promotion, en passant, and castling | 2.000 | Implemented |
| C04 | All-piece pseudo-legal generation and castling path checks | 4.000 | Implemented |
| C05 | Legal filtering and targeted king check detection | 2.000 | Implemented |
| C06 | Recursive perft, divide, and configured multi-position CI baselines | 2.000 | Implemented |
| C07 | Deterministic incremental Zobrist keys with undo restoration | 2.000 | Implemented |
| C08 | Check/mate/stalemate status and conservative insufficient-material detection | 1.000 | Implemented |
| C09 | Material evaluation, terminal scores, and side-to-move perspective | 1.000 | Implemented |
| C10 | Depth-limited negamax/alpha-beta with mate distance and root move | 3.000 | Implemented |
| C11 | Capture/promotion ordering including en passant | 1.000 | Implemented |
| C12 | Quiescence with legal check evasions, promotions, and termination policy | 6.000 | Implemented |
| C13a | Bounded TT storage, full-key probes, depth/bound/move payload, collision/replacement and reset tests | 1.250 | Implemented |
| C13b | Mate score normalization across search plies with round-trip tests | 0.750 | Implemented |
| C13c | Depth-qualified exact/lower/upper search probes and stores, preferred move, and search parity tests | 4.000 | Implemented |
| C14a | Iterative deepening with shared TT, accumulated counters, and completed-depth reporting | 2.000 | Implemented |
| C14b | Legal principal variation with root restoration and search integration tests | 2.000 | Implemented |
| C15a | Node-limited iterative search, exception-safe move restoration, and completed-iteration fallback | 1.500 | Implemented |
| C15b | Deadline-based interruption and completed-depth fallback tests | 1.500 | Implemented |
| C15c | External stop signal with deterministic interruption/restoration tests | 1.000 | Implemented |
| C16 | Phase-aware positional evaluation and endgame scaling | 12.000 | Pending |
| C17a | Legal en passant key normalization including pinned and discovered-check cases | 1.000 | Implemented |
| C17b1 | Reversible repetition-key history, occurrence counts, and threefold threshold tests | 0.750 | Implemented |
| C17b2 | Search integration with path-dependent TT handling and interruption restoration | 1.250 | Implemented |
| C17c1 | Move-count draw classification, terminal precedence, and reset boundary tests | 0.500 | Implemented |
| C17c2 | Search draw policy with rule-clock-safe transposition handling | 0.500 | Pending |
| C18 | C++ UCI protocol including position, go, stop, and lifecycle | 5.000 | Pending |
| C19 | SEE, killer/history, continuation/correction history, and ordering integration | 5.000 | Pending |
| C20 | PVS, aspiration, null move, LMR, futility, razoring, and extensions | 10.000 | Pending |
| C21 | Reproducible search/tactical benchmarks and controlled match infrastructure | 8.000 | Pending |
| C22 | Profile-guided movegen/state optimization with measured regressions | 6.000 | Pending |
| C23 | Tablebase integration and score/draw handling | 3.000 | Pending |
| C24 | Reproducible evaluation tuning, self-play, and SPRT workflow | 5.000 | Pending |

This bounded roadmap does not cover the complete long-term project. NNUE/data training, opening-book methodology, candidate verification, practical selection, opponent modelling, and years of optimization need separate scope decisions. Completing this table is not completing a world-class engine.

## Verification state

GitHub Actions was inspected on 2026-10-27. [Run 43](https://github.com/ceemv22/trickfish/actions/runs/40591838988) at `6f364ff` passed GCC/Linux and MSVC/Windows builds, all four CTest cases, FEN/perft, and configured CLI fixtures. That exact commit contains 45.000 implemented-scope points. The additional C17c1 working-tree changes still require their own CI result. Earlier runs 40 through 42 failed on the invalid occupied-EP-target test fixture; the repair did not disable tests. Local C++ compile/runtime execution is still unavailable.

C07 now hashes the en passant file only when a legal en passant capture exists (C17a); the recorded FEN field is preserved. C09 is a material baseline, not parity with Python positional evaluation. C10 has no repetition or time control; C13c adds main-search TT integration. C12 adds ordered captures, en passant, promotions, and all legal check evasions, with stand-pat disabled in check. A 32-ply quiescence cap returns material after checking terminal states; a checked but non-terminal position can be statically truncated at this safety cap. Repetition-aware termination remains C17. Runtime verification of C12 is pending CI. C11 has no measured speedup claim.

For each subsequent change, report the previous and current implemented index, the milestone/submilestone responsible for the delta, the local checks, and whether the exact commit has passed CI. Keep Python prototype and serious-engine estimates separate: their earlier approximate 60% and 3% estimates have no weighted checklist yet and must not be presented as measured three-decimal indices.

## Index changes

- Baseline: 22.000 points at `f9ac82b`.
- C12 implementation: +6.000 points, bringing implemented scope to 28.000%. No playing-strength or CI-success claim follows from this increment.

C13 was split before storage implementation into C13a (1.250), C13b (0.750), and C13c (4.000). The parent total remains 6.000; this split changes no index points.

- C13a implementation: +1.250 points, implemented scope 29.250%. TT storage is not yet used by search; mate normalization and integration remain pending. New CTest runtime verification awaits CI. Storage uses one preallocated slot array, full-key checks, deeper same-key retention, and direct collision eviction. Probe pointers are for immediate use and must not be retained across stores/reset.

- C13b implementation: +0.750 points, implemented scope 30.000%. Mate scores are normalized relative to the stored node and restored for the probing ply. The reserved mate band starts at +/-99872, covering the current maximum 64 main-search plus 32 quiescence plies. Ordinary material scores are not adjusted. Helpers are not yet called by search; C13c remains pending. CTest round-trip and different-ply fixtures await CI.

- C13c implementation: +4.000 points, implemented scope 34.000%. Main search probes/stores exact/lower/upper bounds with depth checks and normalized mate scores; a legal TT root move is required for a root cutoff. TT moves lead ordering. Tables may be reused explicitly or disabled for parity checks. Quiescence does not use TT entries. Integration CTest fixtures await CI; speedup and playing strength remain unmeasured. Earlier pending statements in this log describe their respective historical steps.

C14 was split before implementation into C14a (2.000) and C14b (2.000), preserving its 4.000-point total.

- C14a implementation: +2.000 points, implemented scope 36.000%. The CLI now runs successive completed depths with one shared TT and accumulated node/hit counters. Terminal roots stop after depth one. PV, time limits, stop handling, and interrupted-depth fallback are not part of C14a. Fixed-depth/iterative and TT-disabled parity fixtures await CI.

- C14b implementation: +2.000 points, implemented scope 38.000%. Search returns the selected main-search line and the CLI prints UCI-coordinate PV moves. The line may end early at terminal/draw states or a TT cutoff; cached cutoffs contribute a legal stored move but not an unverified continuation. Quiescence continuations are not included. PV legality, first-move consistency, length, TT-disabled opening coverage, and root-state regression fixtures await CI. Complete TT-hit continuation reconstruction remains future refinement and earns no extra points automatically.

C15 was split before implementation into C15a (1.500), C15b (1.500), and C15c (1.000), preserving its 4.000-point total.

- C15a implementation: +1.500 points, implemented scope 39.500%. A shared node budget covers main/quiescence visits and all iterations. Move scopes restore state during budget exceptions. Interrupted iterations are discarded; if none completes, a legal fallback has depth 0 and no PV. Root fallback preparation is not counted as a search node. Node/hit counters include interrupted work. Deadline and external stop are pending. Deterministic interruption/restoration tests await CI.

- C15b implementation: +1.500 points, implemented scope 41.000%. Iterative search accepts an absolute steady-clock deadline; --search-time accepts depth and non-negative milliseconds. Deadline and node budget may be combined in the API. Checks occur before main/quiescence node visits and use C15a restoration/fallback. Allocation, fallback preparation, and individual node operations are not hard time bounded. Expired/future deadline tests avoid machine-speed timing assumptions and await CI. External stop remains C15c.

- C15c implementation: +1.000 points, implemented scope 42.000%. Iterative search accepts a caller-owned stop predicate, checked before main/quiescence node visits alongside node/deadline limits. A true result uses the same completed-iteration fallback and move restoration. The callback runs synchronously on the search thread; callers must synchronize state changed from other threads. Immediate, inactive, and deterministic mid-iteration stop tests await CI. No C++ UCI stop-command loop is implemented yet.

C17 was split before implementation into C17a (1.000), C17b (2.000), and C17c (1.000), preserving its 4.000-point total.

- C17a implementation: +1.000 points, implemented scope 43.000%. Full/incremental keys include EP only when a capture survives king-safety checks. Trial board copies avoid recursion through make_move while preserving FEN state. Ten reference cases cover both colors, pins, horizontal discovered check, one legal capturer among two candidates, check evasion, and absent/blocked targets. C++ key-equivalence and make/unmake regressions await CI. No repetition history is added yet. Key values intentionally change for unusable EP targets.

C17b was split before implementation into C17b1 (0.750) and C17b2 (1.250), preserving its 2.000-point total.

- C17b1 implementation: +0.750 points, implemented scope 43.750%. RepetitionHistory records the initial key and subsequent positions, supports guarded pop, counts the current key, and reports the three-occurrence threshold. Callers must push after make and pop alongside unmake; it does not own or validate moves. The FEN alone cannot reconstruct earlier game positions. Knight-cycle, root protection, and alternate-branch regressions await CI. Search does not consume this history yet; no repetition draw scoring or intended-move claim detection is added.

- C17b2 implementation: +1.250 points, implemented scope 45.000%. Iterative search optionally accepts a history ending at the root, copies it for local use, and records/unrecords main/quiescence moves with exception-safe restoration. Three occurrences score zero under an explicit always-claim search policy, after terminal checks. History-aware mode disables TT to avoid reusing path-dependent scores. Search without a supplied history retains previous TT/no-repetition behavior; CLI/FEN alone cannot supply played-game history yet. Caller history is unchanged. Fresh/repeated context, interrupted search, and mismatched-root regressions await CI. This does not implement optional claim selection, intended-move claims, or fivefold adjudication.

- CI regression repair: +0.000 points; implemented scope remains 45.000%. The occupied-EP-target fixture placed a white knight on d6 attacking the non-moving black king on e8. Moving that king to a8 preserves the blocked-target scenario without starting from an illegal check position. Fixture preconditions and contextual diagnostics were added; all CTest cases remain enabled. The repaired commit still requires GCC/MSVC Actions confirmation.

C17c was split before implementation into C17c1 (0.500) and C17c2 (0.500), preserving its 1.000-point total.

- CI confirmation: [run 43](https://github.com/ceemv22/trickfish/actions/runs/40591838988) at `6f364ff` passed both OS builds, all four CTest cases, FEN/perft, and all configured CLI fixtures. This confirms that exact commit, not subsequent working-tree changes.
- C17c1 implementation: +0.500 points, implemented scope 45.500%. MoveCountDraw distinguishes a fifty-move claim opportunity at 100 halfmoves from automatic seventy-five-move draw at 150. Already finished mate/stalemate/insufficient-material positions return no additional move-count classification. Boundary, clock-reset, and terminal precedence tests await CI. Search/evaluation do not consume this helper yet; C17c2 remains pending. Intended-move claims are outside this helper. Rules reference: https://handbook.fide.com/chapter/E012023 (articles 9.3 and 9.6.2).
