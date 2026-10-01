# C++ roadmap progress index

Baseline: `f9ac82b` (2026-10-02).

Implemented-scope index: **22.000%**. This is a planning index, not an estimate of playing strength, Elo, elapsed effort, or proximity to a world-class engine. The initial weights deliberately calibrate the index to the earlier rough 22% estimate; they are project planning choices, not measured costs.

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
| C12 | Quiescence with legal check evasions, promotions, and termination policy | 6.000 | Pending |
| C13 | Bounded transposition table with depth/bounds and mate normalization | 6.000 | Pending |
| C14 | Iterative deepening, principal variation, and completed-depth reporting | 4.000 | Pending |
| C15 | Deadline/node limits and stop with position restoration | 4.000 | Pending |
| C16 | Phase-aware positional evaluation and endgame scaling | 12.000 | Pending |
| C17 | Legal-en-passant repetition key semantics, history, and move-count draw policy | 4.000 | Pending |
| C18 | C++ UCI protocol including position, go, stop, and lifecycle | 5.000 | Pending |
| C19 | SEE, killer/history, continuation/correction history, and ordering integration | 5.000 | Pending |
| C20 | PVS, aspiration, null move, LMR, futility, razoring, and extensions | 10.000 | Pending |
| C21 | Reproducible search/tactical benchmarks and controlled match infrastructure | 8.000 | Pending |
| C22 | Profile-guided movegen/state optimization with measured regressions | 6.000 | Pending |
| C23 | Tablebase integration and score/draw handling | 3.000 | Pending |
| C24 | Reproducible evaluation tuning, self-play, and SPRT workflow | 5.000 | Pending |

This bounded roadmap does not cover the complete long-term project. NNUE/data training, opening-book methodology, candidate verification, practical selection, opponent modelling, and years of optimization need separate scope decisions. Completing this table is not completing a world-class engine.

## Verification state

At this baseline, local static review and `git diff --check` have been performed during development. No local C++ compile/runtime result has been established. GitHub Actions is configured for GCC/Linux and MSVC/Windows builds, FEN/perft, state restoration, search baselines, and CLI fixtures. The Actions result for `f9ac82b` has not been inspected in this session. Therefore a CI-confirmed percentage is **unknown**, not 22.000% and not zero.

C07 currently includes every recorded FEN en passant file in the key; legal-capture normalization is reserved for C17. C09 is a material baseline, not parity with Python positional evaluation. C10 has no quiescence, repetition, TT, or time control. C11 has no measured speedup claim.

For each subsequent change, report the previous and current implemented index, the milestone/submilestone responsible for the delta, the local checks, and whether the exact commit has passed CI. Keep Python prototype and serious-engine estimates separate: their earlier approximate 60% and 3% estimates have no weighted checklist yet and must not be presented as measured three-decimal indices.
