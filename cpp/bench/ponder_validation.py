import argparse
import json
import pathlib
import queue
import subprocess
import sys

from search_benchmark import digest, validate_output_path
from search_progress import validate_uci_batches
from uci_matches import Engine, parse_bestmove, validate_prediction
from trickfish.position import Position, STARTING_FEN


class RecordedQueue(queue.Queue):
    def __init__(self, records):
        super().__init__()
        self.records = records

    def get(self, *args, **kwargs):
        item = super().get(*args, **kwargs)
        if item is not None: self.records.append(item)
        return item


class ProbeEngine(Engine):
    def __init__(self, binary, count=1, prediction=False):
        super().__init__(binary, 20, {"MultiPV": count, "Ponder": prediction})
        self.records = []
        self.events = RecordedQueue(self.records)


def begin(engine, fen, command):
    engine.send("position fen " + fen)
    engine.send("isready")
    engine.until("readyok")
    before = len(engine.records)
    engine.send(command)
    return before


def require_pending(records):
    if any(line.startswith("bestmove") for line in records):
        raise ValueError("ponder emitted bestmove before hit/stop")


def barrier(engine, before):
    engine.send("isready")
    engine.until("readyok")
    require_pending(engine.records[before:])


def expect_rejection(engine, command):
    before = len(engine.records)
    engine.send(command)
    rejected = False
    try:
        engine.until("info string error:")
    except RuntimeError:
        rejected = any(line.startswith("info string error:") for line in engine.records[before:])
    if not rejected: raise ValueError("invalid ponder command was not rejected: " + command)
    engine.send("isready")
    engine.until("readyok")


def validate_reply(records, fen, count, prediction):
    replies = [line for line in records if line.startswith("bestmove")]
    if len(replies) != 1: raise ValueError("ponder lifecycle did not produce exactly one bestmove")
    best, hint = parse_bestmove(replies[0])
    position = Position.from_fen(fen)
    legal = {move.to_uci() for move in position.legal_moves()}
    if best == "0000":
        if legal and position.halfmove_clock < 150: raise ValueError("unexpected null ponder bestmove")
    elif best not in legal:
        raise ValueError("illegal ponder bestmove")
    if hint is not None: validate_prediction(position, best, hint)
    infos = [line for line in records if line.startswith("info depth ")]
    batches = validate_uci_batches(infos, fen, count)
    last = batches[-1]
    pv = last["lines"][0]["pv"]
    if pv and best != pv[0]: raise ValueError("ponder bestmove differs from saved primary PV")
    expected = pv[1] if prediction and len(pv) >= 2 else None
    if hint != expected: raise ValueError("ponder prediction differs from option snapshot or primary PV")
    return {"depth": last["depth"], "nodes": last["nodes"], "batches": len(batches),
        "bestmove": best, "ponder_move": hint}


def run_probes(binary):
    results = []
    for count in (1, 3):
        with ProbeEngine(binary, count, True) as engine:
            before = begin(engine, STARTING_FEN, "go ponder depth 2")
            engine.until("info depth 2 ")
            barrier(engine, before)
            saved = validate_uci_batches([line for line in engine.records[before:] if line.startswith("info depth ")], STARTING_FEN, count)[-1]
            engine.send("setoption name Ponder value false")
            engine.send("isready")
            engine.until("readyok")
            require_pending(engine.records[before:])
            engine.send("ponderhit")
            engine.until("bestmove")
            summary = validate_reply(engine.records[before:], STARTING_FEN, count, True)
            if summary["nodes"] != saved["nodes"] or summary["depth"] != saved["depth"]:
                raise ValueError("completed ponder restarted on hit")
            expect_rejection(engine, "ponderhit")
            validate_reply(engine.records[before:], STARTING_FEN, count, True)
            best, _, _ = engine.choose(STARTING_FEN, [], "go depth 2")
            if best not in {move.to_uci() for move in Position.from_fen(STARTING_FEN).legal_moves()} or engine.last_ponder is not None:
                raise ValueError("updated Ponder option did not affect the next search")
            results.append({"id": f"completed-{count}", **summary, "no_restart": True, "settings_snapshot_checked": True})
    black = Position.from_fen(STARTING_FEN)
    black = black.make_move(next(move for move in black.legal_moves() if move.to_uci() == "e2e4"))
    for name, fen, go in (("movetime", STARTING_FEN, "go ponder movetime 0 depth 64"),
            ("white-clock", STARTING_FEN, "go ponder wtime 0 btime 1000 depth 64"),
            ("black-clock", black.to_fen(), "go ponder wtime 1000 btime 0 depth 64")):
        with ProbeEngine(binary, 3, False) as engine:
            before = begin(engine, fen, go)
            engine.until("info depth 1 ")
            barrier(engine, before)
            engine.send("ponderhit")
            engine.until("bestmove")
            summary = validate_reply(engine.records[before:], fen, 3, False)
            if summary["depth"] < 1 or summary["nodes"] == 0: raise ValueError("ponder budget activated before hit")
            results.append({"id": name, **summary, "zero_budget_activated_at_hit": True})
    for name, fen, go, release, count in (
            ("stop", STARTING_FEN, "go ponder depth 1", "stop", 3),
            ("terminal", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "go ponder depth 2", "ponderhit", 3),
            ("zero-nodes", STARTING_FEN, "go ponder nodes 0", "ponderhit", 1)):
        with ProbeEngine(binary, count, True) as engine:
            before = begin(engine, fen, go)
            if name != "zero-nodes": engine.until("info depth 1 ")
            barrier(engine, before)
            if name == "stop":
                expect_rejection(engine, "ponderhit extra")
                require_pending(engine.records[before:])
            engine.send(release)
            engine.until("bestmove")
            summary = validate_reply(engine.records[before:], fen, count, True)
            if name == "zero-nodes" and (summary["depth"] != 0 or summary["nodes"] != 0):
                raise ValueError("ponder node budget was reset at hit")
            results.append({"id": name, **summary})
    with ProbeEngine(binary) as engine:
        for command in ("ponderhit", "ponderhit extra", "go ponder infinite", "go ponder ponder", "go ponder winc 1",
                "go ponder movetime 18446744073709551615"):
            before = len(engine.records)
            expect_rejection(engine, command)
            require_pending(engine.records[before:])
        before = begin(engine, STARTING_FEN, "go infinite depth 1")
        engine.until("info depth 1 ")
        expect_rejection(engine, "ponderhit")
        require_pending(engine.records[before:])
        engine.send("stop")
        engine.until("bestmove")
        validate_reply(engine.records[before:], STARTING_FEN, 1, False)
        results.append({"id": "invalid-and-nonponder-hit", "invalid_commands_rejected": True})
    for name, ending in (("eof", ""), ("quit", "quit\n")):
        process = subprocess.run([str(binary), "--uci"], input="setoption name MultiPV value 3\nposition startpos\ngo ponder depth 64\n" + ending,
            capture_output=True, text=True, timeout=20, check=True)
        summary = validate_reply(process.stdout.splitlines(), STARTING_FEN, 3, False)
        results.append({"id": name, **summary})
    with Engine(binary, 20, {"Ponder": True}) as engine:
        engine.choose(STARTING_FEN, [], "go depth 2")
        if engine.last_ponder is None: raise ValueError("enabled normal-search prediction was not delivered")
        engine.choose(STARTING_FEN, [], "go depth 1")
        if engine.last_ponder is not None: raise ValueError("missing prediction retained a stale prior reply")
        results.append({"id": "match-client", "prediction_replay_checked": True, "stale_prediction_cleared": True})
    return results


def main():
    parser = argparse.ArgumentParser(description="Probe UCI ponder/hit clocks, lifecycle and legal predictions")
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    validate_output_path(args.output, [binary])
    before = digest(binary)
    results = run_probes(binary)
    if digest(binary) != before: raise ValueError("binary changed during ponder validation")
    report = {"ponder_validation_schema_version": 1, "binary_sha256": before, "cases": results,
        "inference": "protocol/deadline/lifecycle/prediction checks; no speed or playing-strength inference"}
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(text)
    else: args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
