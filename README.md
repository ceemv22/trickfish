<p align="center">
  <img src="assets/trickfish-logo.png" alt="Trickfish logo" width="280">
</p>

<h1 align="center">Trickfish</h1>

Trickfish is a chess-engine research project. Its long-term problem is to choose, from moves that survive objective search, the move whose correct defense is hardest to find and execute. A difficult move is still rejected when deeper search finds an adequate refutation or when its evaluation loss exceeds the configured limit.

## Current implementation

The repository contains an early Python position prototype. It is not yet a playable engine and has no strength or Elo claim.

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
| Position key | Deterministic 64-bit Zobrist key for board, side, castling, and legal en passant state |
| Game history | Immutable position sequence with threefold-repetition counting |
| Perft | Recursive legal-node counter with standard positions through depth 3 and root divide |
| CLI | Position display, legal/pseudo-legal move listing, perft, and divide |
| Tests | FEN, move values, legal filtering, move application, CLI, and perft |

`moves` reports legal moves after applying each candidate and checking the moving side's king. `pseudo-moves` exposes the raw generator for debugging. Castling checks the king's starting, transit, and destination squares against the attack map.

The perft suite covers the initial position plus standard positions that exercise castling, check-evasion, promotions, and move application. Each currently runs through depth 3. `divide` prints the node count below every legal root move so an incorrect branch can be isolated without inspecting the full tree.

## Running the prototype

PowerShell:

```powershell
cd "$env:USERPROFILE\Desktop\trickfish"
$env:PYTHONPATH="src"

python -m trickfish.cli
python -m trickfish.cli moves
python -m trickfish.cli pseudo-moves
python -m trickfish.cli moves "8/7k/8/8/3Q4/8/K7/8 w - - 0 1"
python -m trickfish.cli perft 3
python -m trickfish.cli divide 3
python -m unittest discover -s tests -v
```

## Engine direction

Trickfish is being designed around two separate measurements:

1. **Objective result:** the evaluation after the strongest defense found by search.
2. **Practical result:** the difficulty and consequence of the opponent's plausible responses.

The practical measurement is a selection constraint, not a substitute for evaluation. It is applied only after candidate moves pass an objective-loss limit and tactical re-search.

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

- [x] FEN parsing, serialization, and board rendering
- [x] Move value and UCI coordinates
- [x] Pseudo-legal generation for all pieces
- [x] Immutable successor position with clocks, rights, promotion, en passant, and castling updates
- [x] Pawn double step, promotion, and en passant
- [x] Castling and attack detection
- [x] Legal move filtering and initial-position perft baselines through depth 3
- [x] Established multi-position perft suite and divide output
- [x] Deterministic Zobrist position key with legal en passant treatment
- [x] Repetition history and threefold-repetition counting
- [ ] Fifty-move rule and insufficient-material adjudication
- [ ] Mutable make/unmake for the C++ search core
- [ ] First evaluation and alpha-beta search
- [ ] UCI support and time management
- [ ] Candidate verification
- [ ] Practical move selection
- [ ] Opponent-specific experiments and published benchmark methodology

## Language plan

The current Python code exists to establish rules, tests, and the decision model quickly. It is not intended to be the final high-performance search core.

The target architecture is a C++26 engine core for move generation, position updates, search, and evaluation, with Python retained for tooling, experiments, test fixtures, data preparation, and analysis. Until C++26 compiler support is stable across the supported toolchains, the core will stay within a portable C++20/23 subset and avoid draft-only dependencies. The move to C++ begins after the Python prototype has complete legal move generation and perft coverage; that gives the C++ implementation a precise behavioral reference instead of rewriting unfinished logic.

## Verification standard

Every chess rule added to the core requires focused tests before it becomes part of the aggregate move list. Legal move generation will be checked with established perft positions before search work starts. Playing-strength changes will be measured in controlled matches. Practical-selection work will be evaluated independently from raw engine strength.

## License

No license has been selected.
