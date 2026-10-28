<p align="center">
  <img src="assets/trickfish-logo.png" alt="Trickfish logo" width="280">
</p>

<h1 align="center">Trickfish</h1>

Trickfish is a chess-engine research project with a Python reference engine and a C++ performance core. Its long-term goal is to select, among objectively acceptable moves, the move whose adequate defense is hardest to find and execute. Candidate verification and practical move selection are planned; they are not part of the current search.

## Current implementation

Python provides the reference rules, positional evaluation, search, and a clock-aware UCI reference interface. C++ provides mutable position state, legal move generation, perft, the current Python reference static evaluation terms, and an initial search implementation with a basic asynchronous UCI frontend. Cross-language fixtures compare the complete static breakdown and terminal-aware scores; search behavior remains separate. No playing-strength or Elo claim has been established.

### Python reference engine

| Area | Current state |
| --- | --- |
| FEN | Parse, validate, render, and serialize |
| Board state | Immutable 64-square tuple |
| Move representation | Immutable UCI-coordinate move value |
| Move application | Immutable successor position with clocks, rights, en passant, promotion, and castling updates |
| Pseudo-legal moves | Knight, bishop, rook, queen, king, and pawn moves |
| Pawn support | Single step, double step, ordinary captures, promotion, and en passant |
| Castling | Rights, piece placement, empty path, and attack checks for the king's route |
| Attack map | Detect attacks by either side without changing side to move |
| Game state | Check, checkmate, stalemate, and ongoing-position status |
| Evaluation | Phase-aware white-positive score with material, activity, pawn structure, bishop pair, rook files, king safety/activity, mate, and dead-position terms |
| Search | Iterative deepening, deadline control, negamax, alpha-beta, capture-first ordering, quiescence, Zobrist transposition table, principal variation, and node count |
| Position key | Deterministic 64-bit Zobrist key for board, side, castling, and legal en passant state |
| Game history | Immutable position sequence with threefold-repetition counting |
| Draw rules | Threefold repetition, 50/75-move thresholds, and insufficient-material detection |
| Perft | Recursive legal-node counter with standard positions through depth 3 and root divide |
| CLI | Position display, status, evaluation, depth-limited search, legal/pseudo-legal move listing, perft, and divide |
| UCI | Handshake, readiness, new game, startpos/FEN with moves, depth/movetime/clock search, stop, bestmove, and quit |
| Tests | FEN, move values, legal filtering, move application, CLI, and perft |

`moves` reports legal moves after applying each candidate and checking the moving side's king. `pseudo-moves` exposes the raw generator for debugging. Castling checks the king's starting, transit, and destination squares against the attack map.

### C++ performance core

| Area | Implemented scope |
| --- | --- |
| Position | Twelve piece bitboards, 64-square mailbox, cached side occupancy, clocks, castling rights, and en passant state |
| Updates | Reversible make/unmake for ordinary moves, captures, promotions, en passant, and castling |
| Move generation | Fixed-capacity move list, all-piece pseudo-legal generation, castling path checks, and legal filtering |
| Attacks | Compile-time pawn/knight/king tables, blocker-aware sliding attacks, aggregate attack maps, and targeted king check detection |
| Position key | Incremental deterministic 64-bit Zobrist key with undo restoration; only legal en passant availability is hashed |
| Game state | Check, checkmate, stalemate, and conservative insufficient-material detection |
| Evaluation | White-positive reference material, piece activity, pawn structure, bishop pair, rook files, and phase-aware king safety/activity, mate/stalemate/insufficient-material handling, and side-to-move score conversion |
| Search | Negamax, alpha-beta, mate-distance scores, capture/promotion ordering, quiescence, bounded TT, and iterative deepening |
| TT | Full-key checks, depth-qualified exact/lower/upper bounds, mate-score normalization, and preferred-move ordering |
| Output | Best root move, legal main-search PV, side-to-move score, completed depth, and accumulated node count |
| Perft | Recursive node count and root divide |
| UCI | Handshake/readiness, startpos/FEN with legal moves and history, asynchronous depth/node/movetime/remaining-clock search, stop, new game, quit, and EOF |

The C++ UCI frontend has a baseline remaining-clock allocator and Move Overhead option; ponder, configurable Hash/Threads, and Chess960 remain unsupported. Additional endgame/drawish scaling, evaluation tuning, and advanced pruning remain pending. Both implementations include en passant in the key only when a legal capture exists. A separate C++ repetition-key history container supports push/pop and current-position occurrence counts; iterative search optionally accepts this history. It validates the root key, uses a local copy, and scores three occurrences as zero under an always-claim policy. Main and quiescence moves update the copy with safe unwind. This mode disables TT because scores depend on the played history. Diagnostic --search calls without a history retain TT/no-repetition behavior. The UCI frontend supplies the complete move list history and therefore uses history-aware search with TT disabled. A standalone FEN cannot reconstruct played-game history. Their deterministic key tables differ, so numeric Python/C++ key equality is not an acceptance criterion.

Quiescence searches captures, en passant, and promotions. In check it searches all legal evasions and disables stand-pat. It is capped at 32 quiescence plies; after checking terminal states, the cap returns static evaluation even if the position is still in check. This is a safety truncation, not a guarantee of tactical completeness. Main search accepts depths 1 through 64. TT entries are used by main search, not quiescence.

`--search` runs depths successively with a shared TT and reports the last completed depth. It stops terminal roots after the first iteration. The reported PV covers selected main-search moves, excludes quiescence continuations, and may truncate at TT cutoffs or terminal/draw states. It is not guaranteed to reach the reported depth. `--search-time` accepts a depth and a non-negative millisecond budget using a steady-clock deadline. Deadline checks occur before main/quiescence node visits; setup and individual node operations can overrun the budget. The iterative-search API also accepts a stop predicate. It runs synchronously before node visits; a true result preserves the same completed-iteration fallback. Callers must synchronize any predicate state changed from another thread. The diagnostic CLI remains a one-shot command; the UCI frontend maps its stop command to the search stop predicate. `--search-nodes` caps main/quiescence node visits across all iterations. On node-budget or deadline exhaustion it restores position state and returns the last completed iteration; before depth one completes it returns a legal fallback with depth 0, an empty PV, and `stopped true`. Root fallback preparation is outside the node budget. `--divide` prints the node count under each legal root move and the total.

### Evaluation detail and parity

`--eval-detail [fen]` reports `phase`, `material`, `piece_activity`, `pawn_structure`, `bishop_pair`, `rook_files`, `king_safety`, `king_activity`, `static_total`, and `evaluation`. Terms and totals are white-positive. Phase is a 0..24 index, not an added score: knights/bishops contribute 1, rooks 2, and queens 4, summed across both sides and capped at 24 for promoted material. Pawn advancement bonuses increase toward the endgame.

The pawn term matches the current Python reference: -15 per extra pawn on a file, -12 per pawn without a friendly pawn on an adjacent file, and a passed-pawn bonus when no enemy pawn lies ahead on the same/adjacent file. The passed bonus is `8 + 8 * advance + floor((24 - phase) * 2 * advance / 24)`. These are reference heuristics, not tuned parameters. `static_total` sums all seven score components; `evaluation` applies mate/stalemate/recognized-insufficient-material precedence, so the two may differ in finished positions. Static evaluation does not apply search move-count/repetition draw policy.

CI is configured to compare the complete C++ evaluation breakdown and terminal-aware score with the public Python evaluator on 118 positions, including color reflections and legal children, promotions, and en passant. These fixtures check reference agreement on selected positions; they do not prove universal equivalence or a playing-strength improvement.

Piece activity rewards pawn advancement/central files, knight/bishop centrality, and rooks on the enemy seventh rank while enemy pawns remain. King safety combines a c/g home-rank square bonus with neighboring home-pawn shields, scaled by material phase. The square bonus does not infer castling history. King centrality is scaled toward the endgame and disabled whenever any queen or rook remains. These formulas preserve the current Python reference and have not been tuned.

### Verification coverage

The C++ workflow is configured to build with GCC on Linux and MSVC on Windows. It runs initial-position FEN round-trip, depth-3 perft on four positions, divide fixtures, and CLI material/game-state/evaluation fixtures. CTest adds position-state restoration, incremental-key and occupancy checks, targeted check detection parity, TT storage/score normalization, and search regressions including TT-disabled and iterative comparisons. UCI adds parser/position/lifecycle CTest coverage and a standard-library Python subprocess suite for handshake, completed search, readiness during infinite search, stop, transactional positions, limits, mate reporting, and history transmission.

The configured perft counts are 8,902 for the initial position, 97,862 for Kiwipete, 2,812 for the endgame fixture, and 9,467 for the promotion/check-evasion fixture. These are acceptance targets, not a statement that an uninspected commit has passed CI. Check the Actions result for the exact commit being reviewed. Perft verifies move-generation behavior on those trees; it does not establish search quality or playing strength. Passing search fixtures establishes those regression cases, not general tactical correctness or evaluator parity with Python.

[PROGRESS.md](PROGRESS.md) records a weighted C++ implementation-scope index. Its percentages are planning arithmetic, not measured progress toward world-class playing strength. Implementation and exact-commit CI confirmation are tracked separately.

## Running the prototype

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH="src"

python -m trickfish.cli
python -m trickfish.cli moves
python -m trickfish.cli pseudo-moves
python -m trickfish.cli status "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"
python -m trickfish.cli eval "7k/8/8/8/8/8/8/KQ6 w - - 0 1"
python -m trickfish.cli eval-detail
python -m trickfish.cli search 3
python -m trickfish.cli search-time 1000
python -m trickfish.cli moves "8/7k/8/8/3Q4/8/K7/8 w - - 0 1"
python -m trickfish.cli perft 3
python -m trickfish.cli divide 3
python -m trickfish.uci
python -m unittest discover -s tests -v
```

## C++ UCI frontend

Running `trickfish_cpp` without arguments, or with `--uci`, enters UCI mode. Explicit diagnostic arguments retain their existing behavior, including a quoted FEN argument for FEN round-trip output. Launching without arguments no longer prints the initial FEN and exits.

Supported commands are `uci`, `isready`, `ucinewgame`, `position startpos`, `position fen` with six fields, an optional `moves` list, `go`, `stop`, and `quit`. Moves are resolved against the legal move list so promotions, castling, and en passant keep their internal flags. An invalid position command reports `info string error` and leaves the previously accepted position/history unchanged. Parsing rejects a checked non-moving king, pawns on promotion ranks, and EP ranks inconsistent with the active side; it does not prove that every FEN is historically reachable.

Search runs on a worker thread with independent position/history copies. `isready` responds while search is active. `stop` joins the worker and produces one `bestmove` for that search; replacing a position/search, starting a new game, quitting, or reaching EOF also stops and joins it. Search limits can combine `depth` (1 through 64), `nodes`, and `movetime` in milliseconds. A bare `go` or `go infinite` waits for `stop` before emitting `bestmove`, including when the depth ceiling is reached. Info is emitted when search finishes, not after every iteration. A budget exhausted before depth one yields an unscored depth-zero legal fallback.

The frontend accepts `wtime`/`btime`, `winc`/`binc`, and positive `movestogo`. It selects the clock and increment for the active side. An explicit `movetime` takes precedence over clock allocation; `go infinite` ignores time deadlines. If clock parameters are supplied without the active side's remaining time, the request is rejected unless movetime or infinite mode supplies the applicable policy. Unsupported `searchmoves`, `mate`, and pondering requests are not implemented. The allocator is a baseline heuristic and has not been tuned or validated by controlled matches. Supplying `position ... moves` enables played-game repetition handling; FEN alone supplies no earlier history. This mode currently disables TT and uses the existing always-claim repetition search policy. It does not make the search multithreaded internally.

Clock allocation uses `remaining / movestogo + increment / 2`, with a default horizon of 30 moves. The budget is capped by remaining time after reserving the larger of 5% of the clock or `Move Overhead`. The advertised `Move Overhead` spin option ranges from 0 to 10000 ms, defaults to 10, and applies to subsequent clock-based searches. It persists across `ucinewgame`; invalid option updates preserve the old value. If usable time is exhausted, the budget is zero and search returns its depth-zero fallback. A future increment is never spent when no usable time remains. Overflow-safe allocation does not guarantee avoidance of flag losses: setup and individual node operations can still overrun the deadline.

Example clock commands are `setoption name Move Overhead value 20` and `go wtime 60000 btime 60000 winc 1000 binc 1000 movestogo 30`. Explicit `movetime` is not reduced by Move Overhead. Hash/Threads and other options are not advertised.

Example input after launching the binary:

```text
uci
isready
position startpos moves e2e4 e7e5
go depth 4
```

Use `stop` to interrupt an active search and `quit` to exit. Scores are side-to-move positive: ordinary scores use `score cp`, mate scores use `score mate` in full moves. `bestmove 0000` indicates no root move, including already adjudicated automatic draws. Protocol reference: [UCI specification distributed with Stockfish](https://sources.debian.org/src/stockfish/17-1/debian/engine-interface.txt).

## Engine direction

Trickfish is being designed around two separate measurements:

1. **Objective result:** the evaluation after the strongest defense found by search.
2. **Practical result:** the difficulty and consequence of the opponent's plausible responses.

The planned practical measurement is a selection constraint. It will be applied only after candidate moves pass an objective-loss limit and tactical re-search.

For a candidate move `m`, the eventual selection stage will compare:

```text
objective value after best defense
evaluation uncertainty
number and quality of defensive resources
cost of likely defensive mistakes
time required to find adequate defense
game context and configured risk budget
```

The relevant failure case is a trap that works only when the opponent misses one obvious response. Candidate verification must identify and reject that case.

## Planned core

| Layer | Responsibilities |
| --- | --- |
| Position | Piece placement, side to move, castling, en passant, clocks, make/unmake, repetition state, Zobrist key |
| Move generation | Pseudo-legal moves, attack maps, legal filtering, promotions, en passant, castling, perft |
| Search | Iterative deepening, alpha-beta, quiescence, transposition table, move ordering, pruning, extensions, time control |
| Evaluation | Material, pawn structure, mobility, king safety, threats, passed pawns, space, endgame scaling |
| Candidate verification | Re-search of selected candidates, tactical stability checks, uncertainty tracking |
| Practical selection | Candidate eligibility, defensive-resource analysis, opponent-response model, risk-budget policy |
| Interfaces | UCI protocol, command-line analysis, structured analysis output |
| Measurement | Perft suite, tactical regression suite, SPRT engine matches, fixed opening sets, reproducible hardware and time controls |

## Development sequence

### Python reference

- [x] Legal rules, FEN, immutable move application, and multi-position perft
- [x] Legal-en-passant Zobrist keys, repetition history, and draw-rule helpers
- [x] Phase-aware positional evaluation and explainable breakdown
- [x] Alpha-beta, quiescence, TT, iterative deepening, and principal variation
- [x] Deadline-based search and UCI depth/movetime/clock/stop support

### C++ core

- [x] Mutable bitboards, mailbox, occupancy, and reversible updates
- [x] Complete legal move generation, attack detection, perft, and divide
- [x] Incremental Zobrist keys and restoration regression fixtures
- [x] Material evaluation with terminal and insufficient-material handling
- [x] Depth-limited alpha-beta with mate-distance scores
- [x] Capture/promotion ordering and quiescence with check evasions
- [x] Bounded TT with score normalization and depth-qualified bounds
- [x] Iterative deepening with shared TT and completed-depth reporting
- [x] Legal principal variation output with explicit TT truncation
- [x] Node budget with state restoration and completed-iteration fallback
- [x] Steady-clock deadline with completed-iteration fallback
- [x] API stop predicate with completed-iteration fallback and state restoration
- [x] Legal-en-passant repetition-equivalent keys
- [x] Reversible repetition-key history container and three-occurrence threshold
- [x] Optional history-aware iterative search with conservative TT exclusion
- [x] Separate fifty-move claim and seventy-five-move automatic-draw classification
- [x] Automatic seventy-five-move search draws, optional fifty-move claim policy, and clock-aware TT keys
- [x] Reference bishop-pair term in static evaluation and search
- [x] Reference rook-file term in static evaluation and search
- [x] Phase-aware pawn structure and explainable implemented-term breakdown
- [x] Reference piece/king activity and phase-aware king safety
- [ ] Additional position-dependent endgame/drawish scaling
- [x] Basic asynchronous C++ UCI with legal positions, history, depth/node/movetime, and stop lifecycle
- [x] UCI remaining-clock allocation, increments, movestogo, and Move Overhead option
- [x] PVS with selectable full-window alpha-beta reference and parity fixtures
- [x] Iterative aspiration windows with widening and interrupted-retry fixtures
- [x] Quiet killer ordering with per-search lifetime and selectable disabling
- [x] Bounded quiet history with cutoff rewards and prior-quiet penalties
- [x] Legal-recapture material exchange diagnostic with special-move/pin fixtures
- [x] Targeted legal recaptures with full-generator exchange reference
- [x] Bounded exchange search with exhaustive reference parity and work counters
- [ ] SEE/search integration, continuation/correction history, other pruning, and extensions
- [x] Fixed-suite repeatable diagnostic search benchmark and provenance reports
- [x] Bounded tactical regression objectives with mirrored-color fixtures
- [ ] Broader tactical benchmark suites, tuning, self-play, and SPRT matches

### Research layers

- [ ] Candidate verification
- [ ] Practical move selection
- [ ] Opponent-specific experiments and published benchmark methodology

Checked items indicate implemented scope. They do not certify the latest commit's CI result or playing strength.

## Language plan

The current Python code exists to establish rules, tests, and the decision model quickly. It is not intended to be the final high-performance search core.

The target architecture is a C++26 engine core for position updates, move generation, search, and evaluation. The actual build baseline is C++23 (`cxx_std_23` in `CMakeLists.txt`), with compiler extensions disabled. C++26 is an architectural target, not the currently required compiler standard. Python remains the behavioral reference and supports tooling, experiments, fixtures, data preparation, and analysis.

The C++ core is under `cpp/`. Local C++ compilation and runtime execution have not been established in the current development environment; GitHub Actions provides the configured GCC/MSVC build and runtime verification. The commands below require an installed CMake and compatible compiler.

Windows with Visual Studio:

```powershell
cmake -S . -B build -A x64
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
.\build\Release\trickfish_cpp.exe --perft 3
.\build\Release\trickfish_cpp.exe --divide 3
.\build\Release\trickfish_cpp.exe --material
.\build\Release\trickfish_cpp.exe --eval
.\build\Release\trickfish_cpp.exe --eval-detail
.\build\Release\trickfish_cpp.exe --status
.\build\Release\trickfish_cpp.exe --search 3
.\build\Release\trickfish_cpp.exe --search-nodes 6 10000
.\build\Release\trickfish_cpp.exe --search-time 6 1000
.\build\Release\trickfish_cpp.exe --uci
```

Linux with a single-configuration generator:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
./build/trickfish_cpp --search 3
```

`--material`, `--eval`, `--eval-detail`, `--eval-stm`, `--status`, and `--insufficient-material` accept an optional quoted FEN. `--perft`, `--divide`, `--search`, and `--search-ab` accept a depth followed by an optional quoted FEN. `--search-nodes` accepts depth, a non-negative node limit, and an optional quoted FEN. `--search-time` accepts depth, a non-negative millisecond budget, and an optional quoted FEN. Without a FEN, commands use the initial position. `--eval` is white-positive; `--eval-stm` and search scores are side-to-move positive. Mate scores use a separate magnitude of 100,000, with search adjusting for distance. Diagnostic search output is separate from UCI mode, which is selected with --uci or by launching with no arguments.

The C++ `move_count_draw_status` API reports claim availability at 100 halfmoves and automatic draw at 150. It returns no additional move-count classification for positions already finished by mate, stalemate, or recognized insufficient material. Search now adjudicates automatic seventy-five-move draws in main and quiescence nodes, with mate checked first. The iterative API optionally always claims an available fifty-move draw; the default CLI policy does not claim it automatically. Intended-move claims and selecting a win instead of an optional claim remain unmodeled. Search TT keys include halfmove clock and draw policy; repetition keys still omit clocks. Static `--eval` does not apply this search draw policy. Its non-terminal score combines material, a one-time 30-point bonus per side with at least two bishops, the Python rook-file term, phase-aware pawn structure, piece activity, king safety, and king activity. Each rook gets 10 points if its file lacks a friendly pawn and another 10 if it lacks an enemy pawn; the entire rook-file term is disabled when no pawns remain. `--material` remains material-only. See [FIDE Laws, articles 9.3 and 9.6.2](https://handbook.fide.com/chapter/E012023).

Main search defaults to principal variation search (PVS): the first move uses the current full window, later moves probe with a null window, and an improvement below beta triggers a full-window re-search. This changes search windows, not nominal depth or legal move coverage. Quiescence keeps its existing alpha-beta behavior. `--search-ab depth [fen]` selects the full-window diagnostic reference with PVS, aspiration, killer and quiet-history ordering disabled; `SearchOptions::use_pvs` controls iterative search and the positional API remains available. `SearchResult` includes probe/re-search attempt counts, cumulative across iterative and interrupted work. Tied best moves and PVs may differ between algorithms. PVS commit `2106708` passed its configured CI checks; this does not establish a speedup.

Iterative search uses aspiration windows from depth two: an initial 25-point radius around the last completed score doubles after fail-low/high until the result is inside the window, with bounds clamped to the full score range. Mate-band previous scores use a full window. `SearchOptions::aspiration_window` (also available through the positional API) accepts 0 to disable it, or 1..100001 for the starting radius. Failed or interrupted retries never replace the last completed iteration; their work remains in cumulative node and failure counters. Fixed-depth API searches retain a full root window. The default radius is untuned. Aspiration commit `47b3c83` passed its configured CI checks.

Main-search quiet beta cutoffs retain two unique killer moves per ply. A legal TT move sorts first, followed by captures/promotions, the two killer quiets, and remaining quiet moves with deterministic coordinate ties. Captures, en passant, and promotions are never recorded as killers. Quiescence retains its existing ordering. Killer state is shared across depths/retries of one search and reset for each new search. Iterative search uses `SearchOptions::use_killers`; the positional API also retains its switch; result counters report quiet killer cutoffs and killer moves actually searched. This is an untuned ordering heuristic; new C++ parity/lifetime checks await this change's CI.

The structured C++ iterative API accepts `SearchOptions` (TT, PVS, killer ordering, quiet history, aspiration radius, and draw policy), `SearchLimits` (node limit, deadline, and stop callback), and an optional repetition-history pointer. CLI and UCI use this entry point. The legacy positional overload forwards to the same implementation with the same defaults. Existing CTests exercise both forms; the configuration refactor passed CI at `1602584`. These are C++ API settings, not additional UCI options.

Quiet history uses a side/from/to table within each search, shared across iterative depths and retries. A quiet beta cutoff receives `min(512, depth * depth)` and previously searched quiets on that node receive the negative bonus. Gravity updates keep values within +/-16384. History breaks ties after tactical/killer priority and before coordinate ties; it does not alter quiescence ordering or prune moves. `SearchOptions::use_history` disables it; result counters report rewards, penalties and moves searched with nonzero history. The table resets per search. These are untuned heuristics, with runtime/parity checks pending this change's CI.

## Search benchmark

Run from the repository root after a Release build:

```powershell
python cpp/bench/search_benchmark.py .\build\Release\trickfish_cpp.exe --depth 3 --repeats 3 --output build/search-benchmark.json
```

On Linux, use `./build/trickfish_cpp` as the binary path. The versioned nine-position suite covers opening/castling, captures/recaptures, en passant, promotion, a pawn ending, mate, and stalemate. Each repeat launches a fresh diagnostic iterative PVS search with aspiration windows, killer and quiet-history ordering, a fresh transposition table, automatic move-count draw policy, and no played-game repetition history. This differs from history-aware UCI search, which currently disables TT.

The runner rejects interrupted searches, unexpected output, illegal principal variations, and differences in score, move, PV, depth, or node count between repeats. The Python legal-move reference checks PV legality; it does not independently certify search scores. JSON records binary/suite SHA-256, checkout state, platform, parameters, results, node counts, and wall-time samples/medians. Checkout metadata identifies the working checkout, not the source provenance of an arbitrary supplied binary. Timing includes process startup and initialization; compare the same suite/depth/build settings on the same machine. These are diagnostic measurements, not Elo or controlled match results.

Add `--compare-alphabeta` to repeat each fixture through `--search-ab` as well. The reference disables PVS, aspiration, killer and quiet-history ordering. Report schema 2 records aspiration, killer and quiet-history policies and includes the reference run and PVS-minus-reference node delta, requiring equal scores and completed depths while allowing tied move/PV differences. Both runs are independently checked for legal PVs and deterministic repetition.

CI is configured to run depth-two PVS and full-window searches twice for every fixture on both OS runners and print the JSON report in the job log. It checks repeatability within each job; it imposes no timing threshold or cross-machine performance comparison. New benchmark runtime results require the next commit's completed CI run.

The separate `cpp/bench/tactical_suite.json` contains ten shallow regression cases: queen capture, queen promotion, en passant, mate in one, and forced check evasion, each for both colors. Run it with:

```powershell
python cpp/bench/search_benchmark.py .\build\Release\trickfish_cpp.exe --suite cpp/bench/tactical_suite.json --depth 1 --repeats 2 --compare-alphabeta --output build/tactical-regression.json
```

Optional `expect.bestmoves` lists accepted legal root moves. `expect.mate_in_one` requires a checkmating root move, independently verified by the Python rules reference, and the C++ one-ply mate score of 99999. Fixtures are validated before search, and every repeat in both algorithms must satisfy its objective. Objective failures abort report generation. The JSON report retains the objectives alongside results and provenance. CI is configured to execute this suite on both runners; the new process results await this package's completed CI. This is a bounded correctness smoke suite, not a tactical rating or playing-strength benchmark.

The diagnostic `--see move [fen]` reports material exchange gain from the initial mover's perspective. The initial move must be a legal capture or promotion. `static_exchange` then exhaustively considers legal recaptures on the same target square, with either side allowed to stop. It includes promotion material gain and initial en passant; legal move generation excludes pinned recaptures and unsafe king captures. The caller's position is preserved.

The default evaluator generates only attackers of the target using current occupancy and filters them for king safety, including all four recapture promotions. `static_exchange_reference` and `--see-reference move [fen]` retain the full legal-move generator for comparison. Both paths solve the same restricted exchange model. The targeted path uses alpha-beta windows translated by each capture gain, the optional-stop lower bound of zero, and immediate-gain upper bounds. The full-generator reference remains exhaustive. It ignores off-target tactics, mate values, and forced-check continuations, and can branch substantially. It is not used in search ordering or pruning. For example:

```powershell
.\build\Release\trickfish_cpp.exe --see a1a2 "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"
```

The expected exchange gain is 900. The original exchange baseline passed CI at `30bda03`. Targeted recapture generation passed CI at `1cd22a5`. New bounded/exhaustive parity and work-counter checks await this package's completed CI.

`--see-detail move [fen]` reports `score`, `nodes` (visited recapture states, including entries pruned before move generation), and `cutoffs` (bound/branch pruning events). The `analyze_exchange` API returns the same fields; its reference flag selects exhaustive evaluation. These counters measure exchange work, not main-search nodes or elapsed speed. No runtime improvement is established by their presence.

## Verification standard

Rule and state changes require focused behavioral checks and established perft baselines. Search changes require regression cases and comparison with a reference path where applicable. Report local checks separately from the Actions result for the exact pushed commit. Playing-strength changes require controlled matches with reproducible hardware, openings, and time controls. Practical-selection work requires its own evaluation methodology.

## License

No license has been selected.
