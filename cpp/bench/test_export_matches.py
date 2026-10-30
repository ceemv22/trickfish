import copy
import io
import json
import tempfile
from unittest.mock import patch
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import export_matches as exporter
import uci_matches as matches
from trickfish.position import Position


def make_report(fen, moves, result="*", reason="searched_ply_limit", book=0):
    position = Position.from_fen(fen)
    decisions = []
    for index, text in enumerate(moves):
        legal = {move.to_uci(): move for move in position.legal_moves()}
        if index >= book:
            decisions.append({"move": text, "side": position.side_to_move,
                "engine": "a" if position.side_to_move == "w" else "b"})
        position = position.make_move(legal[text])
    game = {"opening": "fixture", "root_fen": fen, "opening_plies": book, "white": "a", "black": "b",
        "engine_names": {"a": 'A "quoted" \\ engine\nnext', "b": "B"}, "round": 1,
        "moves": list(moves), "decisions": decisions, "result": result, "reason": reason, "final_fen": position.to_fen()}
    return {"schema_version": 1, "policy": {"draws": matches.DRAW_POLICY, "searched_ply_limit": max(1, len(decisions))},
        "engines": {"a": {"sha256": "a" * 64}, "b": {"sha256": "b" * 64}},
        "games": [game], "scores": matches.score_games([game])}


def scheduled_report():
    report = make_report(exporter.INITIAL, ["e2e4"])
    first = report["games"][0]
    first.update(pair=1, pair_game=1)
    second = copy.deepcopy(first)
    second.update(white="b", black="a", pair_game=2)
    for decision in second["decisions"]:
        decision["engine"] = "b" if decision["engine"] == "a" else "a"
    report["games"].append(second)
    report["scores"] = matches.score_games(report["games"])
    report["policy"].update(rounds=1, schedule_seed=0,
        pair_schedule=[{"pair": 1, "round": 1, "opening": "fixture", "white_order": ["a", "b"]}])
    return report


class ExportTests(unittest.TestCase):
    def test_export_cli_rejects_input_collision_before_rendering(self):
        with tempfile.TemporaryDirectory() as directory:
            report = pathlib.Path(directory) / "report.json"
            original = json.dumps(make_report(exporter.INITIAL, ["e2e4"]))
            report.write_text(original)
            with patch.object(exporter.sys, "argv", ["exporter", str(report), "--output", str(report)]):
                with patch.object(exporter.sys, "stderr", io.StringIO()), patch.object(exporter, "export_report") as render:
                    with self.assertRaises(SystemExit) as error: exporter.main()
                    self.assertEqual(error.exception.code, 2)
                    render.assert_not_called()
            self.assertEqual(report.read_text(), original)

    def test_scheduled_report_exports_pair_identity(self):
        pgn = exporter.export_report(scheduled_report())
        self.assertEqual(pgn.count('[TrickfishPair "1"]'), 2)
        self.assertIn('[PairGame "1"]', pgn)
        self.assertIn('[PairGame "2"]', pgn)

    def test_schedule_corruption_is_rejected_before_export(self):
        for change in ("seed", "missing", "reordered", "color", "opening", "root", "prefix", "pair", "plan", "rounds"):
            report = scheduled_report()
            second = report["games"][1]
            if change == "seed": report["policy"]["schedule_seed"] = True
            elif change == "missing": report["games"].pop()
            elif change == "reordered": report["games"].reverse()
            elif change == "color": second.update(white="a", black="b")
            elif change == "opening": second["opening"] = "other"
            elif change == "root": second["root_fen"] = exporter.INITIAL.replace("KQkq", "-")
            elif change == "prefix": second["opening_plies"] = 1
            elif change == "pair": second["pair_game"] = True
            elif change == "plan": report["policy"]["pair_schedule"][0]["white_order"] = ["b", "a"]
            else: report["policy"]["rounds"] = 2
            with self.subTest(change=change), self.assertRaises(ValueError): exporter.export_report(report)

    def check_san(self, fen, text, expected):
        position = Position.from_fen(fen)
        legal = {move.to_uci(): move for move in position.legal_moves()}
        self.assertIn(text, legal)
        self.assertEqual(exporter.san_for_move(position, legal[text]), expected)

    def test_basic_capture_promotion_ep_castling_and_mate_san(self):
        for fen, text, expected in [
            (exporter.INITIAL, "e2e4", "e4"), (exporter.INITIAL, "g1f3", "Nf3"),
            ("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1", "a1a2", "Rxa2"),
            ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q", "a8=Q+"),
            ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8n", "a8=N"),
            ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6", "exd6"),
            ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", "O-O"),
            ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1", "O-O-O"),
            ("7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "g6g7", "Qg7#")]:
            with self.subTest(move=text): self.check_san(fen, text, expected)

    def test_disambiguation_uses_legal_rivals_and_file_rank_or_both(self):
        self.check_san("7k/8/8/8/8/2N5/8/4K1N1 w - - 0 1", "c3e2", "Nce2")
        self.check_san("7k/8/8/8/1b6/2N5/8/4K1N1 w - - 0 1", "g1e2", "Ne2")
        self.check_san("7k/8/8/8/8/R7/8/R3K3 w - - 0 1", "a1a2", "R1a2")
        self.check_san("7k/8/8/8/8/1Q6/8/1Q1Q3K w - - 0 1", "b1c2", "Qb1c2")

    def test_finished_game_has_matching_result_headers_and_san(self):
        report = make_report(exporter.INITIAL, ["f2f3", "e7e5", "g2g4", "d8h4"], "0-1", "checkmate")
        report["games"][0]["started_utc"] = "2026-10-29T00:30:00+02:00"
        pgn = exporter.export_report(report)
        self.assertIn('[Result "0-1"]', pgn)
        self.assertIn("1. f3 e5 2. g4 Qh4# 0-1", pgn)
        self.assertIn('[Date "2026.10.28"]', pgn)
        self.assertNotIn('[SetUp "1"]', pgn)

    def test_black_setup_numbering_unknown_date_and_unfinished_marker(self):
        report = make_report("r3k3/8/8/8/8/8/8/R3K3 b - - 0 7", ["a8a7"])
        pgn = exporter.export_report(report)
        self.assertIn('[SetUp "1"]', pgn)
        self.assertIn('[FEN "r3k3/8/8/8/8/8/8/R3K3 b - - 0 7"]', pgn)
        self.assertIn('[Date "????.??.??"]', pgn)
        self.assertIn('[Result "*"]', pgn)
        self.assertIn("7... Ra7 *", pgn)
        self.assertNotIn("1/2-1/2", pgn)

    def test_header_escaping_and_provenance(self):
        report = make_report(exporter.INITIAL, ["e2e4"])
        pgn = exporter.export_report(report)
        self.assertIn(r'[White "A \"quoted\" \\ engine next"]', pgn)
        self.assertIn('[WhiteSHA256 "' + "a" * 64 + '"]', pgn)

    def test_pgn_preserves_typed_color_specific_profiles(self):
        report = make_report(exporter.INITIAL, ["e2e4"])
        report["games"][0]["applied_options"] = {"a": {"Experimental LMR": True}, "b": {"Experimental LMR": False}}
        pgn = exporter.export_report(report)
        self.assertIn(r'[WhiteUCIProfile "{\"Experimental LMR\":true}"]', pgn)
        self.assertIn(r'[BlackUCIProfile "{\"Experimental LMR\":false}"]', pgn)

    def test_requested_profiles_match_canonical_applied_names(self):
        report = make_report(exporter.INITIAL, ["e2e4"])
        report["profiles"] = {"a": {"experimental lmr": True}, "b": {}}
        report["games"][0]["applied_options"] = {"a": {"Experimental LMR": True}, "b": {}}
        self.assertIn("WhiteUCIProfile", exporter.export_report(report))
        for change in ("value", "type", "missing_game", "missing_engine", "extra_engine", "missing_option", "null"):
            broken = copy.deepcopy(report)
            applied = broken["games"][0]["applied_options"]
            if change == "value": applied["a"]["Experimental LMR"] = False
            elif change == "type": applied["a"]["Experimental LMR"] = 1
            elif change == "missing_game": del broken["games"][0]["applied_options"]
            elif change == "missing_engine": del applied["b"]
            elif change == "extra_engine": applied["c"] = {}
            elif change == "missing_option": applied["a"] = {}
            else: broken["profiles"] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                exporter.export_report(broken)

    def test_profile_validation_checks_every_game_before_output(self):
        report = make_report(exporter.INITIAL, ["e2e4"])
        report["profiles"] = {"a": {}, "b": {}}
        report["games"][0]["applied_options"] = {"a": {}, "b": {}}
        report["games"].append(copy.deepcopy(report["games"][0]))
        report["games"][1]["applied_options"]["b"] = {"Unexpected": True}
        report["scores"] = matches.score_games(report["games"])
        with self.assertRaisesRegex(ValueError, "profiles disagree"):
            exporter.export_report(report)

    def test_corrupted_replay_decisions_summary_and_cap_are_rejected(self):
        original = make_report(exporter.INITIAL, ["e2e4"])
        for change in ("fen", "move", "decision", "summary", "cap", "hash", "result"):
            report = copy.deepcopy(original)
            game = report["games"][0]
            if change == "fen": game["final_fen"] = exporter.INITIAL
            elif change == "move": game["moves"][0] = "e2e5"
            elif change == "decision": game["decisions"][0]["side"] = "b"
            elif change == "summary": report["scores"]["a"]["wins"] = 1
            elif change == "cap": report["policy"]["searched_ply_limit"] = 2
            elif change == "hash": report["engines"]["a"]["sha256"] = "invalid"
            else:
                game["result"], game["reason"] = "1/2-1/2", "stalemate"
                report["scores"] = matches.score_games(report["games"])
            with self.subTest(change=change), self.assertRaises(ValueError): exporter.export_report(report)

    def test_replay_cannot_continue_after_mate(self):
        report = make_report(exporter.INITIAL, ["f2f3", "e7e5", "g2g4", "d8h4"], "0-1", "checkmate")
        report["games"][0]["moves"].append("e2e4")
        report["games"][0]["decisions"].append({"move": "e2e4", "side": "w", "engine": "a"})
        report["policy"]["searched_ply_limit"] = 5
        with self.assertRaisesRegex(ValueError, "after game end"): exporter.export_report(report)


if __name__ == "__main__":
    unittest.main()
