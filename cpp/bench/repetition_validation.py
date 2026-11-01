import argparse
import json
import pathlib
import sys

from ponder_validation import RecordedQueue
from search_benchmark import digest, validate_output_path
from search_progress import validate_uci_batches
from uci_matches import Engine, opening_position, parse_bestmove
from trickfish.position import STARTING_FEN


OPTION = "Experimental Repetition Ordering"
CYCLE = ["g1f3", "g8f6", "f3g1", "f6g8"]
ADVANTAGE = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def cases():
    return [
        {"id": "fresh", "fen": STARTING_FEN, "moves": [], "depth": 3},
        {"id": "twofold", "fen": STARTING_FEN, "moves": CYCLE, "depth": 3},
        {"id": "third-at-child", "fen": ADVANTAGE, "moves": CYCLE + CYCLE[:3], "depth": 2,
            "expected_score": 0, "expected_bestmove": "f6g8"},
        {"id": "root-threefold", "fen": ADVANTAGE, "moves": CYCLE * 2, "depth": 2, "expected_score": 0},
        {"id": "pawn-after-cycle", "fen": STARTING_FEN, "moves": CYCLE + ["e2e4"], "depth": 2},
        {"id": "castle", "fen": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "moves": ["e1g1"], "depth": 2},
        {"id": "en-passant", "fen": "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "moves": [], "depth": 2},
        {"id": "promotion", "fen": "4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "moves": [], "depth": 2},
        {"id": "clock-boundary", "fen": "4k3/8/8/8/8/8/q7/R3K3 w - - 149 1", "moves": [], "depth": 2},
        {"id": "mate-precedence", "fen": "7k/6Q1/6K1/8/8/8/8/8 b - - 150 1", "moves": [], "depth": 1},
    ]


def validate_trace(case, records):
    root, _ = opening_position(case)
    batches = validate_uci_batches([line for line in records if line.startswith("info depth ")], root.to_fen(), 1)
    replies = [line for line in records if line.startswith("bestmove")]
    if len(replies) != 1: raise ValueError("repetition probe requires exactly one bestmove")
    best, hint = parse_bestmove(replies[0])
    if hint is not None: raise ValueError("repetition probe did not request ponder predictions")
    legal = {move.to_uci() for move in root.legal_moves()}
    if best != "0000" and best not in legal: raise ValueError("illegal repetition-probe bestmove")
    last = batches[-1]
    line = last["lines"][0]
    if best == "0000" and legal and root.halfmove_clock < 150:
        raise ValueError("unexpected null repetition-probe bestmove")
    if line["pv"] and best != line["pv"][0]: raise ValueError("repetition bestmove disagrees with primary PV")
    if last["depth"] != case["depth"]: raise ValueError("repetition probe did not finish requested depth")
    if "expected_score" in case and (line["score_kind"] != "cp" or line["score"] != case["expected_score"]):
        raise ValueError("repetition objective score mismatch")
    if "expected_bestmove" in case and best != case["expected_bestmove"]:
        raise ValueError("repetition objective bestmove mismatch")
    return {"depth": last["depth"], "score_kind": line["score_kind"], "score": line["score"],
        "nodes": last["nodes"], "bestmove": best, "pv": line["pv"]}


def compare_traces(reference, candidate):
    if any(reference[key] != candidate[key] for key in ("depth", "score_kind", "score")):
        raise ValueError("move-only repetition ordering changed completed score/depth")
    return {"score_depth_equal": True, "node_delta": candidate["nodes"] - reference["nodes"],
        "bestmove_equal": candidate["bestmove"] == reference["bestmove"], "pv_equal": candidate["pv"] == reference["pv"]}


def run_cases(binary):
    results = []
    for case in cases():
        traces = []
        for enabled in (False, True):
            with Engine(binary, 30, {OPTION: enabled}) as engine:
                records = []
                engine.events = RecordedQueue(records)
                engine.choose(case["fen"], case["moves"], "go depth " + str(case["depth"]))
                traces.append(validate_trace(case, records))
        results.append({"id": case["id"], "reference": traces[0], "candidate": traces[1], **compare_traces(*traces)})
    return results


def main():
    parser = argparse.ArgumentParser(description="Replay real UCI history-aware move ordering against uncached scores")
    parser.add_argument("binary", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    validate_output_path(args.output, [binary])
    before = digest(binary)
    results = run_cases(binary)
    if digest(binary) != before: raise ValueError("binary changed during repetition validation")
    report = {"repetition_validation_schema_version": 1, "binary_sha256": before, "cases": results,
        "inference": "fixed-depth nonselective score/depth and legal-PV checks; node changes are descriptive, not speed or strength evidence"}
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(text)
    else: args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
