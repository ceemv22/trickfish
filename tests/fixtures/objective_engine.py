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
        elif mode == "mate":
            print("info depth " + depth + " score mate 2", flush=True)
        elif mode == "bound":
            print("info depth " + depth + " score cp 35 lowerbound", flush=True)
        elif mode == "shallow":
            print("info depth 0 score cp 35", flush=True)
        else:
            print("info depth " + depth + " score cp 35 pv e2e4", flush=True)
        print("bestmove " + ("e1e8" if mode == "illegal" else "e2e4"), flush=True)
    elif line == "quit":
        break
