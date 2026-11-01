import itertools
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from trickfish.evaluation import evaluate, evaluate_breakdown
from trickfish.position import Position, STARTING_FEN


def truncated(value, divisor):
    return (1 if value >= 0 else -1) * (abs(value) // divisor)


def expected(position, weights):
    if position.game_status() in ("checkmate", "stalemate") or position.is_insufficient_material(): return evaluate(position)
    detail = evaluate_breakdown(position)
    terms = (detail.pawn_structure, detail.piece_activity, detail.king_safety)
    return detail.total + sum(truncated(term * weight, 100) - term for term, weight in zip(terms, weights))


def main():
    binary = pathlib.Path(sys.argv[1]).resolve(strict=True)
    fens = [STARTING_FEN,
        "rnbq1rk1/ppp2ppp/2np1n2/4p3/4P3/2NP1N2/PPP2PPP/R1BQK2R w KQ - 4 6",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/8/8/8/8/8/4P3/4K3 b - - 0 1",
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "7k/6Q1/6K1/8/8/8/8/8 b - - 150 1",
        "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w - - 0 1"]
    count = 0
    for fen, weights in itertools.product(fens, ((100, 100, 100), (0, 0, 0), (200, 200, 200), (73, 129, 87), (101, 99, 111))):
        position = Position.from_fen(fen)
        result = subprocess.run([str(binary), "--eval-weighted", *map(str, weights), fen], capture_output=True, text=True, check=True, timeout=15)
        if int(result.stdout) != expected(position, weights): raise ValueError("weighted C++/Python evaluator mismatch: " + fen)
        count += 1
    for value in ("-1", "201", "true", "999999999999999999999"):
        result = subprocess.run([str(binary), "--eval-weighted", value, "100", "100"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0: raise ValueError("invalid weight diagnostic was accepted")
    print("Weighted evaluation parity:", count, "independent Python expectations and invalid-input checks passed")


if __name__ == "__main__":
    main()
