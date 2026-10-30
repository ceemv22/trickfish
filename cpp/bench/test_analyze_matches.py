import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import analyze_matches as analyzer
from test_export_matches import make_report
from uci_matches import score_games
from trickfish.position import STARTING_FEN

WHITE_WIN = ["e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "g8f6", "h5f7"]
BLACK_WIN = ["f2f3", "e7e5", "g2g4", "d8h4"]
DRAW = ["g1f3", "g8f6", "f3g1", "f6g8"] * 2
UNFINISHED = ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6"]
OUTCOMES = {"W": (WHITE_WIN, "1-0", "checkmate"), "L": (BLACK_WIN, "0-1", "checkmate"),
    "D": (DRAW, "1/2-1/2", "always_claim_threefold"), "U": (UNFINISHED, "*", "searched_ply_limit")}


def report_for_pairs(outcomes):
    games, plan = [], []
    report = None
    for pair, kinds in enumerate(outcomes, 1):
        pair_games = []
        for white, kind in zip(("a", "b"), kinds):
            moves, result, reason = OUTCOMES[kind]
            source = make_report(STARTING_FEN, moves, result, reason)
            report = source
            game = source["games"][0]
            if white == "b":
                game.update(white="b", black="a")
                for decision in game["decisions"]:
                    decision["engine"] = "b" if decision["engine"] == "a" else "a"
            game.update(opening="opening-" + str(pair), pair=pair)
            pair_games.append(game)
        if pair % 2 == 0: pair_games.reverse()
        for index, game in enumerate(pair_games, 1): game["pair_game"] = index
        games.extend(pair_games)
        plan.append({"pair": pair, "round": 1, "opening": "opening-" + str(pair),
            "white_order": [game["white"] for game in pair_games]})
    report.update(games=games, scores=score_games(games))
    report["policy"].update(rounds=1, schedule_seed=0, pair_schedule=plan, searched_ply_limit=8)
    return report


class AnalysisTests(unittest.TestCase):
    def test_all_five_pair_score_bins_and_color_opening_totals(self):
        report = report_for_pairs([("L", "W"), ("L", "D"), ("W", "W"), ("W", "D"), ("W", "L")])
        original = copy.deepcopy(report)
        result = analyzer.analyze_report(report)
        self.assertEqual(report, original)
        self.assertEqual(result["paired"]["bin_counts"], [1, 1, 1, 1, 1])
        self.assertEqual(result["paired"]["completed_pairs"], 5)
        self.assertEqual(result["overall"]["scores"]["a"], {"wins": 4, "losses": 4, "draws": 2, "unfinished": 0})
        self.assertEqual(result["overall"]["points"]["a"]["half_points"], 10)
        self.assertEqual(result["overall"]["points"]["a"]["points"], 5)
        self.assertEqual(result["paired"]["points"]["a"]["score_fraction"], 0.5)
        self.assertEqual(result["termination_reasons"], {"checkmate": 8, "always_claim_threefold": 2})
        self.assertEqual(result["by_engine_color"]["a"]["white"]["games"], 5)
        self.assertEqual(result["by_engine_color"]["a"]["black"]["games"], 5)
        self.assertEqual([entry["points"]["a"]["score_fraction"] for entry in result["by_opening"].values()],
            [0, 0.25, 0.5, 0.75, 1])
        self.assertEqual(result["method"]["inference"], "none")

    def test_one_unfinished_game_excludes_entire_pair_but_not_finished_game(self):
        result = analyzer.analyze_report(report_for_pairs([("W", "U")]))
        self.assertEqual(result["overall"]["completed"], 1)
        self.assertEqual(result["overall"]["unfinished"], 1)
        self.assertEqual(result["overall"]["points"]["a"]["points"], 1)
        self.assertEqual(result["paired"]["completed_pairs"], 0)
        self.assertEqual(result["paired"]["unfinished_pairs"], 1)
        self.assertEqual(result["paired"]["bin_counts"], [0] * 5)
        self.assertIsNone(result["paired"]["points"]["a"]["score_fraction"])

    def test_all_unfinished_produces_null_fractions_not_draw_scores(self):
        result = analyzer.analyze_report(report_for_pairs([("U", "U")]))
        for label in ("a", "b"):
            self.assertIsNone(result["overall"]["points"][label]["score_fraction"])
            self.assertEqual(result["overall"]["scores"][label]["draws"], 0)
            self.assertEqual(result["overall"]["scores"][label]["unfinished"], 2)
        json.dumps(result, allow_nan=False)

    def test_legacy_report_keeps_individual_scores_without_inventing_pairs(self):
        report = make_report(STARTING_FEN, WHITE_WIN, "1-0", "checkmate")
        result = analyzer.analyze_report(report)
        self.assertFalse(result["paired"]["available"])
        self.assertEqual(result["overall"]["points"]["a"]["score_fraction"], 1)
        self.assertIsNone(result["by_engine_color"]["a"]["black"]["score_fraction"])
        self.assertFalse(result["by_opening"]["fixture"]["paired"]["available"])

    def test_black_to_move_setup_uses_assigned_colors_for_scoring(self):
        report = make_report("8/8/8/8/8/5kq1/8/7K b - - 0 1", ["g3g2"], "0-1", "checkmate")
        result = analyzer.analyze_report(report)
        self.assertEqual(result["overall"]["points"]["a"]["points"], 0)
        self.assertEqual(result["overall"]["points"]["b"]["points"], 1)
        self.assertEqual(result["by_engine_color"]["a"]["white"]["losses"], 1)
        self.assertEqual(result["by_engine_color"]["b"]["black"]["wins"], 1)

    def test_corrupted_last_game_summary_and_schedule_are_rejected(self):
        original = report_for_pairs([("W", "D"), ("L", "W")])
        for field in ("move", "summary", "schedule", "result"):
            report = copy.deepcopy(original)
            if field == "move": report["games"][-1]["moves"][-1] = "a1a8"
            elif field == "summary": report["scores"]["a"]["wins"] += 1
            elif field == "schedule": report["games"][-1]["pair_game"] = 1
            else:
                report["games"][-1]["result"] = "*"
                report["scores"] = score_games(report["games"])
            with self.subTest(field=field), self.assertRaises(ValueError): analyzer.analyze_report(report)

    def test_cli_records_source_hash_and_protects_source_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "match.json"
            output = source.with_name("analysis.json")
            source.write_text(json.dumps(report_for_pairs([("W", "D")])))
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(pathlib.Path(analyzer.__file__).resolve()), str(source),
                "--output", str(output)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(report["source_report"]["sha256"], analyzer.digest(source))
            self.assertEqual(report["paired"]["bin_counts"], [0, 0, 0, 1, 0])
            with patch.object(analyzer.sys, "argv", ["analysis", str(source), "--output", str(source)]):
                with patch.object(analyzer.sys, "stderr", io.StringIO()), patch.object(analyzer, "analyze_report") as analyze:
                    with self.assertRaises(SystemExit): analyzer.main()
                    analyze.assert_not_called()
            self.assertEqual(source.read_bytes(), original)

    def test_invalid_replay_does_not_write_analysis_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "match.json"
            output = source.with_name("analysis.json")
            report = report_for_pairs([("W", "D")])
            report["games"][-1]["final_fen"] = STARTING_FEN
            source.write_text(json.dumps(report))
            with patch.object(analyzer.sys, "argv", ["analysis", str(source), "--output", str(output)]):
                with self.assertRaises(ValueError): analyzer.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
