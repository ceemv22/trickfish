import argparse
import json
import pathlib
import re
import subprocess
import sys

from multipv_validation import validate_result
from search_benchmark import digest, validate_output_path
from trickfish.position import Position, STARTING_FEN


def validate_progress(data, fen, depth, count):
    if (not isinstance(data, dict) or set(data) != {"progress_schema_version", "iterations", "result"} or
        type(data["progress_schema_version"]) is not int or data["progress_schema_version"] != 1 or
        not isinstance(data["iterations"], list)):
        raise ValueError("invalid search progress schema")
    final = data["result"]
    validate_result(final, fen, depth, count)
    nodes = 0
    for expected_depth, event in enumerate(data["iterations"], 1):
        validate_result(event, fen, expected_depth, count)
        if event["stopped"] or event["completed_depth"] != expected_depth or event["nodes"] <= nodes:
            raise ValueError("progress must contain only successive completed iterations with cumulative work")
        nodes = event["nodes"]
    if len(data["iterations"]) != final["completed_depth"] or nodes > final["nodes"]:
        raise ValueError("final search result differs from completed progress horizon")
    if data["iterations"]:
        last = data["iterations"][-1]
        keys = ("rank", "score", "completed_depth", "bestmove", "pv")
        if len(last["lines"]) != len(final["lines"]) or any(
            any(before[key] != after[key] for key in keys) or before["nodes"] > after["nodes"]
            for before, after in zip(last["lines"], final["lines"])):
            raise ValueError("final search changed the last completed PV batch")
    return {"iterations": len(data["iterations"]), "completed_depth": final["completed_depth"],
        "nodes": final["nodes"], "stopped": final["stopped"], "lines": len(final["lines"])}


def parse_info(text):
    words = text.split()
    if words[:1] != ["info"]: raise ValueError("expected UCI info line")
    result = {"pv": [], "score_kind": None, "score": None}
    seen = set()
    index = 1
    while index < len(words):
        name = words[index]
        if name in seen: raise ValueError("duplicate UCI info field")
        seen.add(name)
        if name == "pv":
            result["pv"] = words[index + 1:]
            break
        if name == "score":
            if index + 2 >= len(words) or words[index + 1] not in ("cp", "mate") or re.fullmatch(r"-?[0-9]+", words[index + 2]) is None:
                raise ValueError("invalid UCI score field")
            result["score_kind"], result["score"] = words[index + 1], int(words[index + 2])
            index += 3
            continue
        if name not in ("depth", "nodes", "time", "nps", "multipv") or index + 1 >= len(words):
            raise ValueError("unexpected UCI info field")
        value = words[index + 1]
        if not value.isascii() or not value.isdecimal() or int(value) > (1 << 64) - 1:
            raise ValueError("invalid unsigned UCI info value")
        result[name] = int(value)
        index += 2
    if not {"depth", "nodes", "time", "nps"} <= seen or not 0 <= result["depth"] <= 64:
        raise ValueError("missing UCI progress fields or invalid depth")
    if result.get("multipv", 1) < 1 or ((result["time"] == 0 or result["nodes"] == 0) and result["nps"] != 0):
        raise ValueError("invalid UCI rank or sub-millisecond NPS")
    if result["depth"] == 0:
        if "score" in seen or result["pv"]: raise ValueError("depth-zero fallback advertised a searched score/PV")
    elif "score" not in seen:
        raise ValueError("completed UCI progress has no score")
    return result


def score_order(line):
    if line["score_kind"] == "cp": return (1, line["score"])
    if line["score"] > 0: return (2, -line["score"])
    return (0, -line["score"])


def trace_signature(batches):
    return [(batch["depth"], batch["nodes"], [(line.get("multipv", 1), line["score_kind"], line["score"], line["pv"])
        for line in batch["lines"]]) for batch in batches]


def validate_uci_batches(lines, fen, count, explicit_ranks=None):
    if explicit_ranks is None: explicit_ranks = count > 1
    position = Position.from_fen(fen)
    legal = {move.to_uci(): move for move in position.legal_moves()}
    terminal = not legal or position.halfmove_clock >= 150 or position.is_insufficient_material()
    groups = []
    for text in lines:
        line = parse_info(text)
        if ("multipv" in line) != explicit_ranks: raise ValueError("unexpected UCI MultiPV marker policy")
        rank = line.get("multipv", 1)
        if rank == 1: groups.append([])
        if not groups or rank != len(groups[-1]) + 1: raise ValueError("incomplete or reordered UCI rank batch")
        groups[-1].append(line)
    if not groups: raise ValueError("no UCI progress batches")
    if len(groups) > 1 and groups[0][0]["depth"] == 0: raise ValueError("fallback must be the final UCI result")
    batches = []
    for group in groups:
        first = group[0]
        expected = 1 if terminal or first["depth"] == 0 else min(count, len(legal))
        if len(group) != expected: raise ValueError("partial UCI progress batch")
        if any(any(line[key] != first[key] for key in ("depth", "nodes", "time", "nps")) for line in group):
            raise ValueError("UCI batch mixed depth/work/timing")
        roots = []
        for line in group:
            if line["depth"] > 0 and not terminal and not line["pv"]:
                raise ValueError("completed UCI line has no PV")
            replay = position
            for text in line["pv"]:
                moves = {move.to_uci(): move for move in replay.legal_moves()}
                if text not in moves: raise ValueError("illegal UCI progress PV")
                replay = replay.make_move(moves[text])
            if line["pv"]: roots.append(line["pv"][0])
        if len(roots) != len(set(roots)): raise ValueError("UCI progress repeated root move")
        if first["depth"] > 0 and [score_order(line) for line in group] != sorted([score_order(line) for line in group], reverse=True):
            raise ValueError("UCI progress scores are not ranked")
        current = {key: first[key] for key in ("depth", "nodes", "time", "nps")}
        current["lines"] = group
        if batches:
            previous = batches[-1]
            if current["depth"] not in (previous["depth"], previous["depth"] + 1) or current["nodes"] <= previous["nodes"] or current["time"] < previous["time"]:
                raise ValueError("UCI progress regressed or skipped a completed depth")
            if current["depth"] == previous["depth"]:
                if current["nodes"] <= previous["nodes"] or any(
                    any(before[key] != after[key] for key in ("score_kind", "score", "pv"))
                    for before, after in zip(previous["lines"], group)):
                    raise ValueError("UCI final work update changed completed PVs")
        elif current["depth"] not in (0, 1):
            raise ValueError("UCI progress did not begin at the first completed iteration")
        batches.append(current)
    return batches


def cases():
    return [("single", STARTING_FEN, 3, 1), ("multi", STARTING_FEN, 2, 3),
        ("ep", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", 2, 3),
        ("winning-mate", "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", 2, 2),
        ("terminal", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 3, 3),
        ("dead", "4k3/8/8/8/8/8/8/4K3 w - - 0 1", 2, 3)]


def main():
    parser = argparse.ArgumentParser(description="Replay completed search iterations and compare observed/unobserved native results")
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    validate_output_path(args.output, [binary])
    before = digest(binary)
    results = []
    for name, fen, depth, count in cases():
        command = [str(binary), "--multi-pv-progress", str(depth), str(count), fen]
        observed = subprocess.run(command, capture_output=True, text=True, timeout=45, check=True)
        data = json.loads(observed.stdout)
        summary = validate_progress(data, fen, depth, count)
        command[1] = "--multi-pv"
        ordinary = subprocess.run(command, capture_output=True, text=True, timeout=45, check=True)
        if data["result"] != json.loads(ordinary.stdout): raise ValueError("observer changed final native result or work")
        results.append({"id": name, **summary, "observer_trace_identical": True})
    if digest(binary) != before: raise ValueError("binary changed during progress validation")
    report = {"progress_validation_schema_version": 1, "binary_sha256": before, "cases": results,
        "inference": "completed-iteration/counter/observer parity checks; no speed or strength inference"}
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(text)
    else: args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
