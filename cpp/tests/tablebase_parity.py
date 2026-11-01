import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("python_chess", type=pathlib.Path)
    parser.add_argument("tables", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.python_chess.resolve()))
    import chess
    import chess.syzygy
    binary = args.binary.resolve(strict=True)
    tables = args.tables.resolve(strict=True)
    def digest(path):
        with path.open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()
    binary_hash = digest(binary)
    inventory = {path.name: digest(path) for path in tables.iterdir() if path.suffix in (".rtbw", ".rtbz")}
    if args.output:
        target = args.output.resolve()
        if target == binary or (target.exists() and target.samefile(binary)) or target.is_relative_to(tables) or target.is_relative_to(args.python_chess.resolve()):
            raise ValueError("tablebase evidence must not replace an input binary, dependency or data file")
    fens = [
        "4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
        "4k3/8/8/8/8/8/8/3QK3 b - - 0 1",
        "8/8/8/8/8/4k3/3Q4/K7 b - - 0 1",
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "4k3/8/8/8/8/8/p7/4K3 b - - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/8/8/8/8/8/8/3RK3 w - - 99 1",
        "4k3/8/8/8/8/8/8/3QK3 w - - 100 1"]
    cases = []
    def run(command):
        result = subprocess.run([str(binary), *command], capture_output=True, text=True, timeout=30, check=True)
        return json.loads(result.stdout)
    with chess.syzygy.open_tablebase(str(tables)) as reference:
        for fen in fens:
            board = chess.Board(fen)
            dtz = reference.probe_dtz(board)
            sign = (dtz > 0) - (dtz < 0)
            wdl = 2 + sign * (2 if abs(dtz) + board.halfmove_clock <= 100 else 1)
            result = run(["--tablebase", str(tables), fen])
            if not result["available"] or (result["wdl"], result["dtz"]) != (wdl, abs(dtz)):
                raise ValueError("Fathom/Python DTZ/WDL mismatch: " + fen + " " + str(result))
            legal = {move.uci() for move in board.legal_moves}
            if {entry["move"] for entry in result["moves"]} != legal or len(result["moves"]) != len(legal):
                raise ValueError("tablebase root move decoding/coverage mismatch")
            search = run(["--search-tablebase", "2", str(tables), fen])
            if search["bestmove"] not in legal and not (board.halfmove_clock >= 100 and search["bestmove"] == "0000"):
                raise ValueError("tablebase search returned illegal move")
            if board.halfmove_clock >= 100:
                if search["used"] or search["score"] != 0: raise ValueError("tablebase overrode fifty-move claim")
            else:
                expected = 50000 if wdl == 4 else -50000 if wdl == 0 else 0
                if not search["used"] or (abs(search["score"]) < 99872 and search["score"] != expected):
                    raise ValueError("tablebase outcome band mismatch")
                if search["bestmove"] != result["bestmove"]: raise ValueError("search escaped recommended DTZ root")
                replay = board.copy()
                for text in search["pv"]:
                    move = chess.Move.from_uci(text)
                    if move not in replay.legal_moves: raise ValueError("illegal tablebase-search PV")
                    replay.push(move)
            cases.append({"fen": fen, "wdl": wdl, "dtz": dtz, "search": search})
    for fen in ("4k3/8/8/8/8/8/8/4K2R w K - 0 1", "4k3/ppp5/8/8/8/8/PPP5/4K3 w - - 0 1"):
        if run(["--tablebase", str(tables), fen])["available"]: raise ValueError("unsupported tablebase root was probed")
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
    from uci_matches import Engine
    fixture = (args.output.parent if args.output else binary.parent).resolve() / ("syzygy fixture " + uuid.uuid4().hex)
    fixture.mkdir()
    copies = []
    try:
        for name in ("KQvK.rtbw", "KQvK.rtbz"):
            path = fixture / name
            path.write_bytes((tables / name).read_bytes())
            copies.append(path)
        with Engine(binary, 30, {"Claim Fifty Move Draw": True}) as engine:
            engine.send("setoption name SyzygyPath value " + str(fixture))
            engine.send("isready")
            engine.until("readyok")
            _, info, _ = engine.choose(fens[0], [], "go depth 2")
            if " score cp 50000 " not in info: raise ValueError("UCI did not apply space-containing Syzygy path")
            engine.send("setoption name SyzygyPath value " + str(fixture / "absent"))
            engine.send("isready")
            try: engine.until("readyok")
            except RuntimeError as error:
                if "rejected command" not in str(error): raise
            else: raise ValueError("invalid Syzygy path was accepted")
            engine.until("readyok")
            _, info, _ = engine.choose(fens[0], [], "go depth 2")
            if " score cp 50000 " not in info: raise ValueError("invalid path discarded previous tablebase setting")
            engine.send("setoption name SyzygyPath value <empty>")
            engine.send("isready")
            engine.until("readyok")
            _, info, _ = engine.choose(fens[0], [], "go depth 2")
            if " score cp 50000 " in info: raise ValueError("disabled tablebase remained active")
        (fixture / "KQvK.rtbz").unlink()
        if run(["--tablebase", str(fixture), fens[0]])["available"]:
            raise ValueError("missing DTZ file fabricated a root oracle result")
    finally:
        for path in copies: path.unlink(missing_ok=True)
        fixture.rmdir()
    if digest(binary) != binary_hash or inventory != {path.name: digest(path) for path in tables.iterdir() if path.suffix in (".rtbw", ".rtbz")}:
        raise ValueError("tablebase binary or source data changed during parity checks")
    if args.output:
        args.output.write_text(json.dumps({"tablebase_validation_schema_version": 1, "binary_sha256": binary_hash,
            "table_files": inventory, "cases": cases,
            "inference": "real pinned tablebase WDL/DTZ and legal-root parity; no playing-strength measurement"}, indent=2) + "\n", encoding="utf-8")
    print("Real Syzygy parity:", len(cases), "roots and unsupported-boundary checks passed")


if __name__ == "__main__":
    main()
