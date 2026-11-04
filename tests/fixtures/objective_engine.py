import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "cp"
for raw in sys.stdin:
    line = raw.strip()
    if line == "uci":
        print("id name Synthetic Objective Fixture", flush=True)
        print("uciok", flush=True)
    elif line == "isready":
        print("readyok", flush=True)
    elif line.startswith("go depth "):
        depth = line.split()[-1]
        if mode == "timeout":
            time.sleep(10)
        elif mode == "eof":
            break
        elif mode in {"mate", "mate-loss", "mate-zero"}:
            distance = {"mate": "2", "mate-loss": "-2", "mate-zero": "0"}[mode]
            print("info depth " + depth + " score mate " + distance + " pv e2e4", flush=True)
        elif mode == "bound":
            print("info depth " + depth + " score cp 35 lowerbound", flush=True)
        elif mode == "shallow":
            print("info depth 0 score cp 35", flush=True)
        elif mode == "pv-missing":
            print("info depth " + depth + " score cp 35", flush=True)
        elif mode in {"pv-mismatch", "pv-illegal-tail", "pv-empty"}:
            pv = {"pv-mismatch": "d2d4", "pv-illegal-tail": "e2e4 e2e5", "pv-empty": ""}[mode]
            print("info depth " + depth + " score cp 35 pv " + pv, flush=True)
        else:
            print("info depth " + depth + " score cp 35 pv e2e4", flush=True)
        print("bestmove " + ("e1e8" if mode == "illegal" else "e2e4"), flush=True)
    elif line == "quit":
        break
