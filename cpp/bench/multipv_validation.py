import argparse
import json
import pathlib
import subprocess
import sys

from search_benchmark import digest, parse_result, validate_output_path
from trickfish.position import Position, STARTING_FEN


def integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def validate_result(data, fen, depth, count):
    root_fields = {"schema_version", "completed_depth", "nodes", "stopped", "lines"}
    line_fields = {"rank", "score", "completed_depth", "nodes", "bestmove", "pv"}
    if (not isinstance(data, dict) or set(data) != root_fields or type(data["schema_version"]) is not int or
        data["schema_version"] != 1 or not integer(data["completed_depth"], 0, depth) or
        not integer(data["nodes"], 0, (1 << 64) - 1) or type(data["stopped"]) is not bool or
        not isinstance(data["lines"], list) or not 1 <= len(data["lines"]) <= count):
        raise ValueError("invalid MultiPV result schema")
    position = Position.from_fen(fen)
    legal = {move.to_uci(): move for move in position.legal_moves()}
    terminal = not legal or position.halfmove_clock >= 150 or position.is_insufficient_material()
    if data["completed_depth"] == 0:
        if not data["stopped"] or len(data["lines"]) != 1: raise ValueError("invalid depth-zero MultiPV fallback")
    elif data["nodes"] == 0:
        raise ValueError("completed MultiPV batch has no work")
    if terminal and len(data["lines"]) != 1: raise ValueError("terminal root has multiple MultiPV lines")
    if not terminal:
        if data["completed_depth"] > 0 and len(data["lines"]) != min(count, len(legal)):
            raise ValueError("incomplete MultiPV batch advertised as completed")
        if not data["stopped"] and data["completed_depth"] != depth:
            raise ValueError("MultiPV did not complete requested depth")
    seen, scores = set(), []
    line_work = 0
    for rank, line in enumerate(data["lines"], 1):
        if (not isinstance(line, dict) or set(line) != line_fields or type(line["rank"]) is not int or line["rank"] != rank or
            not integer(line["score"], -(1 << 31), (1 << 31) - 1) or type(line["completed_depth"]) is not int or
            line["completed_depth"] != data["completed_depth"] or not integer(line["nodes"], 0, data["nodes"]) or
            not isinstance(line["pv"], list) or len(line["pv"]) > data["completed_depth"]):
            raise ValueError("invalid MultiPV line schema or depth")
        best = line["bestmove"]
        if best is None:
            if line["pv"] or not terminal or len(data["lines"]) != 1:
                raise ValueError("unexpected empty MultiPV root")
        elif not isinstance(best, str) or best not in legal or best in seen:
            raise ValueError("illegal or repeated MultiPV root")
        else:
            seen.add(best)
            if data["completed_depth"] > 0 and (not line["pv"] or line["pv"][0] != best):
                raise ValueError("MultiPV best move differs from PV")
            if line["score"] == 99999:
                child = position.make_move(legal[best])
                opponent = "b" if child.side_to_move == "w" else "w"
                if child.legal_moves() or not child.is_square_attacked(child._king_square(child.side_to_move), opponent):
                    raise ValueError("MultiPV mate-in-one score has no immediate mate")
        replay = position
        for text in line["pv"]:
            if not isinstance(text, str): raise ValueError("PV move must be text")
            moves = {move.to_uci(): move for move in replay.legal_moves()}
            if text not in moves: raise ValueError("illegal MultiPV continuation")
            replay = replay.make_move(moves[text])
        scores.append(line["score"])
        line_work += line["nodes"]
    if scores != sorted(scores, reverse=True) or line_work > data["nodes"]:
        raise ValueError("MultiPV rank or aggregate work mismatch")
    if terminal and data["completed_depth"] > 0:
        opponent = "b" if position.side_to_move == "w" else "w"
        checked = position.is_square_attacked(position._king_square(position.side_to_move), opponent)
        expected = -100000 if not legal and checked else 0
        if scores != [expected]: raise ValueError("terminal MultiPV score mismatch")
    return {"depth": data["completed_depth"], "nodes": data["nodes"], "lines": len(data["lines"]),
        "bestmoves": [line["bestmove"] for line in data["lines"]], "scores": scores}


def cases():
    return [("start", STARTING_FEN, 2, 3),
        ("white-ep", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", 1, 16),
        ("black-ep", "4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1", 1, 16),
        ("promotions", "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", 1, 16),
        ("castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", 1, 4),
        ("mate-in-one", "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", 1, 3),
        ("mate", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 2, 3),
        ("stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 2, 3),
        ("dead", "4k3/8/8/8/8/8/8/4K3 w - - 0 1", 2, 3),
        ("clock", "4k3/8/8/8/8/8/R7/4K3 w - - 150 1", 2, 3)]


def main():
    parser = argparse.ArgumentParser(description="Independently replay MultiPV JSON diagnostics and verify single-PV compatibility")
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    validate_output_path(args.output, [binary])
    original_hash = digest(binary)
    results = []
    for name, fen, depth, count in cases():
        process = subprocess.run([str(binary), "--multi-pv", str(depth), str(count), fen],
            capture_output=True, text=True, timeout=30, check=True)
        data = json.loads(process.stdout)
        results.append({"id": name, **validate_result(data, fen, depth, count)})
        if name == "mate-in-one" and data["lines"][0]["score"] != 99999:
            raise ValueError("MultiPV missed the declared immediate-mate fixture")
    process = subprocess.run([str(binary), "--multi-pv", "2", "1", STARTING_FEN],
        capture_output=True, text=True, timeout=30, check=True)
    single = json.loads(process.stdout)
    validate_result(single, STARTING_FEN, 2, 1)
    legacy = subprocess.run([str(binary), "--search", "2", STARTING_FEN], capture_output=True, text=True, timeout=30, check=True)
    reference = parse_result(legacy.stdout, STARTING_FEN, 2)
    line = single["lines"][0]
    if (single["nodes"] != reference["nodes"] or any(line[key] != reference[key] for key in ("score", "bestmove", "pv")) or
        single["completed_depth"] != reference["depth"]):
        raise ValueError("single-PV diagnostic differs from legacy search")
    if digest(binary) != original_hash: raise ValueError("binary changed during MultiPV validation")
    report = {"multipv_validation_schema_version": 1, "binary_sha256": original_hash, "cases": results,
        "single_pv_trace_identical": True, "inference": "protocol/legal-PV/terminal checks; not playing strength"}
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(text)
    else: args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
