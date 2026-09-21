<p align="center">
  <img src="assets/trickfish-logo.png" alt="Trickfish logo" width="280">
</p>

<h1 align="center">Trickfish</h1>

Trickfish is a chess-engine research project. Its long-term problem is narrow: after search identifies several moves that preserve the position, determine which move creates the highest practical cost for the opponent without accepting an unjustified loss in objective evaluation.

## Current implementation

The repository contains an early Python position prototype. It is not yet a playable engine and has no strength or Elo claim.

| Area | Current state |
| --- | --- |
| FEN | Parse, validate, render, and serialize |
| Board state | Immutable 64-square tuple |
| Move representation | Immutable UCI-coordinate move value |
| Move application | Immutable successor position with clocks, rights, en passant, promotion, and castling updates |
| Pseudo-legal moves | Knight, bishop, rook, queen, king, and basic pawn moves |
| Pawn support | Single step, double step, ordinary captures, promotion, and en passant |
| Castling | Rights, piece placement, empty path, and attack checks for the king's route |
| Attack map | Detect attacks by either side without changing side to move |
| CLI | Position display and move listing |
| Tests | FEN, move values, CLI, and piece-specific move generation |

`moves` currently reports pseudo-legal moves. Attack detection is implemented, but moves that expose the moving side's king are not yet filtered. Castling checks the king's starting, transit, and destination squares against the attack map.

## Running the prototype

PowerShell:

```powershell
cd "$env:USERPROFILE\Desktop\trickfish"
$env:PYTHONPATH="src"

python -m trickfish.cli
python -m trickfish.cli moves
python -m trickfish.cli moves "8/7k/8/8/3Q4/8/K7/8 w - - 0 1"
python -m unittest discover -s tests -v
```

## Engine direction

Trickfish is being designed around two separate measurements:

1. **Objective result:** the evaluation after the strongest defense found by search.
2. **Practical result:** the difficulty and consequence of the opponent's plausible responses.

The second measurement must never replace the first. It is only used after candidate moves survive a configurable objective-loss limit and deeper tactical verification.

For a candidate move `m`, the eventual selection stage will compare:

```text
objective value after best defense
evaluation uncertainty
number and quality of defensive resources
cost of likely defensive mistakes
time required to find adequate defense
game context and configured risk budget
```

This creates a testable distinction between a move that is objectively best, a move that is objectively acceptable but difficult to defend, and a speculative trap that fails against a clear response.

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
- [x] Pseudo-legal knight, bishop, rook, queen, king, and basic pawn moves
- [x] Immutable successor position for every supported move type
- [ ] Pawn double step, promotion, and en passant
- [ ] Castling and attack detection
- [ ] Legal move filtering and perft baselines
- [ ] Make/unmake and Zobrist hashing
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
