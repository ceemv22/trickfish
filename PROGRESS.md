# C++ roadmap progress index

Baseline: `f9ac82b` (2026-10-02).

Implemented-scope index: **66.500%**. This is a planning index, not an estimate of playing strength, Elo, elapsed effort, or proximity to a world-class engine. The initial weights deliberately calibrate the index to the earlier rough 22% estimate; they are project planning choices, not measured costs.

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
| C16a | Reference bishop-pair term integrated into static evaluation/search with terminal precedence tests | 0.500 | Implemented |
| C16b1 | Python-reference rook-file term with color/file boundary and search integration tests | 0.500 | Implemented |
| C16c | Phase-aware pawn structure, explainable breakdown, and Python term-parity fixtures | 3.000 | Implemented |
| C16e | Reference piece/king activity, phase-aware king safety, and full evaluator parity fixtures | 6.000 | Implemented |
| C16f | Additional position-dependent endgame/drawish score scaling and fixtures | 2.000 | Pending |
| C17a | Legal en passant key normalization including pinned and discovered-check cases | 1.000 | Implemented |
| C17b1 | Reversible repetition-key history, occurrence counts, and threefold threshold tests | 0.750 | Implemented |
| C17b2 | Search integration with path-dependent TT handling and interruption restoration | 1.250 | Implemented |
| C17c1 | Move-count draw classification, terminal precedence, and reset boundary tests | 0.500 | Implemented |
| C17c2 | Search draw policy with rule-clock-safe transposition handling | 0.500 | Implemented |
| C18a | UCI handshake and transactional legal startpos/FEN/move-history loading | 1.500 | Implemented |
| C18b | Asynchronous depth/node/movetime search, stop/quit/EOF lifecycle, and protocol tests | 2.000 | Implemented |
| C18c | Remaining-clock allocation and UCI clock-control tests | 1.500 | Implemented |
| C19 | SEE, killer/history, continuation/correction history, and ordering integration | 5.000 | Pending |
| C20a | PVS with full-window reference path, score/PV parity, and interruption regression checks | 2.000 | Implemented |
| C20c | Aspiration windows with widening, reference parity, and interrupted retry restoration | 1.500 | Implemented |
| C20d | Null move, LMR, futility, razoring, and extensions | 6.500 | Pending |
| C21a | Fixed-suite search benchmark, deterministic repeats, legal PV validation, and provenance reports | 2.000 | Implemented |
| C21b | Tactical suites and controlled match infrastructure | 6.000 | Pending |
| C22 | Profile-guided movegen/state optimization with measured regressions | 6.000 | Pending |
| C23 | Tablebase integration and score/draw handling | 3.000 | Pending |
| C24 | Reproducible evaluation tuning, self-play, and SPRT workflow | 5.000 | Pending |

This bounded roadmap does not cover the complete long-term project. NNUE/data training, opening-book methodology, candidate verification, practical selection, opponent modelling, and years of optimization need separate scope decisions. Completing this table is not completing a world-class engine.

## Verification state

GitHub Actions was inspected on 2026-10-28. PVS commit `2106708` passed both OS jobs in [run 53](https://github.com/ceemv22/trickfish/actions/runs/40754923019), confirming configured checks at the 65.000-point implementation. The new aspiration-window working tree passed eight local benchmark-tool validation tests. C++ aspiration/parity/interrupted-retry execution and paired process benchmarks still require CI for the next pushed commit. Local C++ compile/runtime execution is unavailable.

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

- CI confirmation: classification commit `23b13bd` passed [run 44](https://github.com/ceemv22/trickfish/actions/runs/40592951569).
- C17c2 implementation: +0.500 points, implemented scope 46.000%. Main/quiescence search adjudicates automatic seventy-five-move draws after terminal checks. Iterative API optionally always claims an available fifty-move draw; default/CLI policy is automatic-only. Search TT keys include capped halfmove clock and policy while repetition keys remain unchanged. Drawn roots return no move/PV; intended-move claims and choosing a win instead of an optional claim are not modeled. TT clock-isolation, horizon threshold, claim selection, mate precedence, and pawn-reset regressions await CI. Static --eval remains material/terminal evaluation without this search policy.

C16 was split before implementation into C16a (0.500) and C16b (11.500), preserving its 12.000-point total.

- CI confirmation: `44b345f` passed both OS jobs and all configured checks in [run 45](https://github.com/ceemv22/trickfish/actions/runs/40593824927).
- C16a implementation: +0.500 points, implemented scope 46.500%. Static evaluation adds the Python reference bishop-pair term: +30 for at least two white bishops, -30 for at least two black bishops, counted once per side regardless of promotions or square colors. Main-search leaves/quiescence use that static score; --material remains unchanged. Terminal/recognized insufficient-material handling still takes precedence in evaluate. This is not phase-aware positional parity, tuning, or a strength claim. CTest color/sign, three-bishop saturation, terminal precedence, and search integration fixtures await CI.

C16b was split before rook-file implementation into C16b1 (0.500) and C16b2 (11.000), preserving its 11.500-point total.

- C16b1 implementation: +0.500 points, implemented scope 47.000%. Static/search evaluation ports the Python rook-file term: per rook, +10 if its file has no friendly pawn and +10 if it has no enemy pawn, signed by color. With no pawns anywhere the term is disabled. This intentionally preserves the reference behavior, including +10 with only a friendly pawn on the file. Color, blocked/open file, doubled rook, pawnless, and search fixtures await CI. The pawn-reset draw regression now expects 610 rather than 600 because this position has a +10 reference rook-file term. No strength claim or tuning is implied.

- CI confirmation: bishop-pair commit `64a7d45` passed [run 46](https://github.com/ceemv22/trickfish/actions/runs/40594229285); this does not confirm the subsequent rook-file changes.

C18 was split before implementation into C18a (1.500), C18b (2.000), and C18c (1.500), preserving its 5.000-point total.

- C18a/C18b implementation: +3.500 points, implemented scope 50.500%. Added --uci/default-entry UCI, handshake/readiness, transactional startpos/FEN/legal-move loading, and complete supplied move history. A jthread owns copies of position/history; synchronized output and joined stop/position/new-game/quit/EOF transitions avoid shared mutable board state. Search accepts depth/nodes/movetime or infinite/bare-go mode; infinite defers bestmove until stop even if the depth ceiling is reached. Final info uses side-to-move cp or mate distance in moves, plus depth/nodes/PV; no live per-iteration callback is added. A depth-zero fallback omits score. Position rejection includes a non-moving checked king, back-rank pawns, and EP rank mismatch, but is not exhaustive legal-history validation.
- UCI limitations: wtime/btime/increments/movestogo remain C18c; ponder, searchmoves, mate limits, options, and Chess960 are unsupported. The frontend always supplies history, so its search currently disables TT as required by C17b2. Search is single-worker, not parallel tree search. Each go starts a fresh search context. No GUI compatibility or strength claim follows. C++ parser/lifecycle tests and nine stdlib Python process-protocol tests are configured for both CI runners; their new C++ runtime results are pending.

- C18c implementation: +1.500 points, implemented scope 52.000%. UCI now parses wtime/btime, winc/binc, and positive movestogo; active-side selection and explicit movetime precedence feed the existing steady-clock interruption path. Pure allocation follows the Python baseline's remaining/horizon plus half-increment policy with a max(overhead, remaining/20) reserve, default horizon 30. Unsigned arithmetic is capped before addition. Unlike the old Python minimum-one behavior, exhausted usable time yields zero without spending an unearned increment. Move Overhead is a case-insensitive spin option, 0..10000 ms, default 10, persistent across new games and applied to subsequent clock-based searches only. Infinite mode ignores time deadlines. No tuned clock-management or tournament-readiness claim follows. Allocation boundary/overflow CTests and 13 process tests await CI; the Python reference engine is unchanged.

Before pawn-evaluation implementation, C16b2 was split into C16c (3.000) and C16d (8.000), preserving its 11.000-point total.

- C16c implementation: +3.000 points, implemented scope 55.000%. Added capped 0..24 material phase and the Python reference pawn-structure term: extra doubled-pawn penalties, isolated-pawn penalties, and passed-pawn bonuses scaled by advancement/phase. EvaluationBreakdown and --eval-detail expose implemented terms, their static sum, and the separate terminal-aware score. Search already consumes evaluate_static, so the new pawn term changes search scores; --material stays unchanged. C++ phase capture/promotion/undo, edge-file, doubled/isolated/passed, promoted-phase cap, and terminal precedence fixtures are configured. An 80-position process parity suite compares implemented components against Python, including color mirrors and legal child/promotion/EP states. Python reference validation and updated quiescence fixture expectations passed locally; new C++ runtime/parity results are pending CI. Piece activity, king terms, tuning, and strength measurement remain outside this milestone.

Before activity/king-term implementation, C16d was split into C16e (6.000) and C16f (2.000), preserving its 8.000-point total. C16f goes beyond the reference phase/pawn/king weighting and remains separately pending.

- C16e implementation: +6.000 points, implemented scope 61.000%. Ported the remaining current Python static terms: pawn advancement/central-file and minor-piece centrality, conditional seventh-rank rook activity, phase-scaled home-square/pawn-shield king safety, and king centrality when no heavy pieces remain. The c/g-square bonus is positional, not a castling-history assertion. Breakdown/CLI expose all seven score components; terminal precedence is separate. The parity suite now uses the public Python evaluator and validates 118 reference positions, with vertical color reflections preserving castled files. New frozen component and search fixtures cover activity, king safety, low-phase rounding, and heavy-piece gating. Python fixture validation and reference depth-one scores passed locally; all new C++ execution awaits CI. C16f additional endgame/drawish scaling remains pending. Reference parity is neither tuned evaluation nor measured playing strength.

- Additional local audit: the unchanged Python suite ran 92 tests; 90 passed and two existing search/CLI expectations asserted 900 while the reference returned 897. No Python source or test files were changed in this package. The 118-state reference fixture/symmetry validation passed; this does not execute C++. Git staging was blocked by permission denied on .git/index.lock, so no local commit was created by the agent.

Before benchmark implementation, C21 was split into C21a (2.000) and C21b (6.000), preserving its 8.000-point total. C21a accepts a versioned fixed FEN suite, repeated deterministic completed searches, independent legal-PV validation, binary/suite provenance, machine-readable output, and a CI smoke run. Wall time is process-inclusive and is not an isolated search-speed metric.

- C21a implementation: +2.000 points, implemented scope 63.000%. Added a versioned nine-position suite and stdlib benchmark runner for repeated diagnostic iterative searches with fresh process/TT state. Full result/PV/depth/node equality is required across repeats; the Python legal-move reference validates every PV. Reports include suite/binary SHA-256, checkout metadata, environment, parameters, scores, nodes, and process-inclusive wall-time samples/medians. Checkout metadata does not prove the binary was built from that checkout. Six local fault/validation tests and suite legality checks passed. CI runs those tests plus depth-two repeated searches on both OS runners and prints the JSON report. Real C++ benchmark execution awaits the next pushed commit; no speedup, tuning, or strength conclusion follows. C21b tactical suites and controlled matches remain pending.

Before PVS implementation, C20 was split into C20a (2.000) and C20b (8.000), preserving its 10.000-point total. C20a requires null-window probes with full-window re-search where needed, a selectable full-window reference, TT/history/draw parity, legal PVs, and safe interruption. No speedup or strength acceptance threshold is implied.

- C20a implementation: +2.000 points, implemented scope 65.000%. Main search uses a full window for the first move and null-window probes for later moves at wide-window nodes, with full-window re-search for an improvement below beta. Null-window nodes retain their existing window; quiescence is unchanged. Public search APIs accept a trailing use_pvs flag (default true); --search-ab runs the full-window diagnostic reference. SearchResult exposes cumulative probe/re-search attempts, including interrupted work. CTests compare fixed/iterative scores and legal PVs with TT off/on/collision storage, special moves, mate/stalemate/dead positions, history mode, move-count draws, and interrupted root/history restoration. The benchmark can compare repeated PVS and full-window runs, requiring equal scores/depths while permitting tied move/PV differences; report schema is now 2. Eight local Python validation tests pass. C++ execution, including the PVS-path exercise assertion and paired CI benchmark, remains pending; no node reduction or strength claim follows.

Before aspiration implementation, C20b was split into C20c (1.500) and C20d (6.500), preserving 8.000 points. C20c requires bounded-window retries with widening to the full score range, selectable disabling, full-window score/PV checks, and preservation of the last completed iteration on interruption.

- C20c implementation: +1.500 points, implemented scope 66.500%. Iterative search starts depths above one with a symmetric 25-point radius around the previous completed score, skipping narrow windows for mate-band scores. Failed windows double their radius up to the full score range without committing a partial result. The trailing aspiration_window API argument accepts 0 (disabled) through 100001; fixed-depth search stays full-window. SearchResult counts fail-low/high attempts across retries and interrupted work. --search-ab disables both PVS and aspiration; benchmark metadata records both policies. CTests cover TT/PVS combinations, 1/25/100001-point radii, special/terminal positions, history mode, both failure directions, and interruption at retry-root entry. Eight local tooling tests and Python opening depth scores 12/0/12 passed; all new C++ execution awaits CI. Default radius is an untuned heuristic, not a measured speedup or strength improvement.
