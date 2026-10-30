import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import pathlib
import sys

from export_matches import validated_pgn_games
from search_benchmark import digest, validate_output_path
from uci_matches import score_games


def half_points(game, label):
    if game["result"] == "*": return None
    if game["result"] == "1/2-1/2": return 1
    winner = game["white"] if game["result"] == "1-0" else game["black"]
    return 2 if winner == label else 0


def point_totals(a_units, completed):
    units = {"a": a_units, "b": 2 * completed - a_units}
    return {label: {"half_points": value, "points": value / 2, "maximum_points": completed,
        "score_fraction": value / (2 * completed) if completed else None} for label, value in units.items()}


def game_summary(games):
    completed = [game for game in games if game["result"] != "*"]
    units = sum(half_points(game, "a") for game in completed)
    return {"games": len(games), "completed": len(completed), "unfinished": len(games) - len(completed),
        "scores": score_games(games), "points": point_totals(units, len(completed))}


def pair_summary(games, available):
    if not available:
        return {"available": False, "reason": "no validated pair schedule"}
    bins = [0] * 5
    unfinished = 0
    for index in range(0, len(games), 2):
        values = [half_points(game, "a") for game in games[index:index + 2]]
        if None in values:
            unfinished += 1
        else:
            bins[sum(values)] += 1
    complete = sum(bins)
    return {"available": True, "pairs": len(games) // 2, "completed_pairs": complete,
        "unfinished_pairs": unfinished, "a_pair_score_values": [0, 0.5, 1, 1.5, 2], "bin_counts": bins,
        "points": point_totals(sum(index * count for index, count in enumerate(bins)), 2 * complete)}


def analyze_report(report):
    for _ in validated_pgn_games(report):
        pass
    games = report["games"]
    paired = "pair_schedule" in report["policy"]
    openings = defaultdict(list)
    for game in games:
        openings[game["opening"]].append(game)
    colors = {}
    for label in ("a", "b"):
        colors[label] = {}
        for color in ("white", "black"):
            selected = [game for game in games if game[color] == label]
            summary = game_summary(selected)
            colors[label][color] = {"games": summary["games"], "completed": summary["completed"],
                **summary["scores"][label], **summary["points"][label]}
    return {"analysis_schema_version": 1, "match_schema_version": report["schema_version"],
        "engines": report["engines"], "profiles": report.get("profiles"), "match_policy": report["policy"],
        "method": {"kind": "descriptive", "unfinished_games": "excluded from points and score fractions",
            "unfinished_pairs": "either unfinished game excludes the entire pair from pair scoring",
            "pair_order": "validated adjacent color swaps" if paired else "unavailable (legacy report)", "inference": "none"},
        "overall": game_summary(games), "paired": pair_summary(games, paired), "by_engine_color": colors,
        "by_opening": {name: {**game_summary(selected), "paired": pair_summary(selected, paired)}
            for name, selected in sorted(openings.items())},
        "termination_reasons": dict(sorted(Counter(game["reason"] for game in games).items()))}


def main():
    parser = argparse.ArgumentParser(description="Replay-validated descriptive match accounting; no strength inference")
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    source = args.report.resolve(strict=True)
    try:
        validate_output_path(args.output, [source])
    except ValueError as error:
        parser.error(str(error))
    source_hash = digest(source)
    analysis = analyze_report(json.loads(source.read_text(encoding="utf-8")))
    if digest(source) != source_hash:
        raise ValueError("match report changed during analysis")
    analysis.update(created_utc=datetime.now(timezone.utc).isoformat(), source_report={"path": str(source), "sha256": source_hash})
    encoded = json.dumps(analysis, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
