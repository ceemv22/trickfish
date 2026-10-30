import json
import io
import pathlib
import tempfile
import sys
import unittest
from collections import Counter
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import uci_matches as matches
from trickfish.position import Position

INITIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class FakeEngine:
    closed = []
    choice = None

    def __init__(self, binary, timeout, profile=None):
        self.binary = binary
        self.name = "fake"
        self.applied_options = {} if profile is None else profile

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed.append(self.binary)

    def choose(self, fen, moves, go):
        position = Position.from_fen(fen)
        for text in moves:
            legal = {move.to_uci(): move for move in position.legal_moves()}
            position = position.make_move(legal[text])
        selected = self.choice if self.choice is not None else position.legal_moves()[0].to_uci()
        if isinstance(selected, Exception):
            raise selected
        return selected, "info depth 1", 1.0


class MatchTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.closed = []
        FakeEngine.choice = None

    def test_mate_precedes_clock_and_repetition_draws(self):
        position = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 150 1")
        counts = Counter({matches.repetition_identity(position): 5})
        self.assertEqual(matches.adjudicate(position, counts), ("1-0", "checkmate"))

    def test_automatic_and_claim_draw_policies_are_explicit(self):
        for clock, count, reason in [(150, 1, "seventy_five_moves"), (0, 5, "fivefold_repetition"),
            (100, 1, "always_claim_fifty_moves"), (0, 3, "always_claim_threefold")]:
            position = Position.from_fen(f"4k3/8/8/8/8/8/8/R3K3 w - - {clock} 1")
            self.assertEqual(matches.adjudicate(position, Counter({matches.repetition_identity(position): count})),
                ("1/2-1/2", reason))

    def test_repetition_identity_ignores_only_inactive_ep_and_clocks(self):
        inactive = Position.from_fen("4k3/8/8/3p4/8/8/8/4K3 w - d6 4 8")
        plain = Position.from_fen("4k3/8/8/3p4/8/8/8/4K3 w - - 0 1")
        self.assertEqual(matches.repetition_identity(inactive), matches.repetition_identity(plain))
        legal = Position.from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
        no_ep = Position.from_fen("4k3/8/8/3pP3/8/8/8/4K3 w - - 0 1")
        self.assertNotEqual(matches.repetition_identity(legal), matches.repetition_identity(no_ep))

    def test_opening_history_is_replayed_for_repetition(self):
        opening = {"id": "cycle", "fen": INITIAL, "moves": ["g1f3", "g8f6", "f3g1", "f6g8"] * 2}
        position, counts = matches.opening_position(opening)
        self.assertEqual(matches.adjudicate(position, counts), ("1/2-1/2", "always_claim_threefold"))

    def test_ply_cap_is_unfinished_and_processes_are_closed(self):
        game = matches.play_game({"id": "start", "fen": INITIAL}, {"a": "A", "b": "B"},
            "a", "go depth 1", 1, 5, FakeEngine)
        self.assertEqual((game["result"], game["reason"]), ("*", "searched_ply_limit"))
        self.assertEqual(FakeEngine.closed, ["B", "A"])
        scores = matches.score_games([game])
        self.assertEqual(scores["a"]["unfinished"], 1)
        self.assertEqual(scores["a"]["draws"], 0)
        self.assertEqual(len(game["decisions"]), 1)

    def test_mate_on_last_allowed_ply_scores_for_assigned_engine(self):
        FakeEngine.choice = "g6g7"
        game = matches.play_game({"id": "mate", "fen": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"},
            {"a": "A", "b": "B"}, "b", "go depth 1", 1, 5, FakeEngine)
        self.assertEqual((game["result"], game["reason"]), ("1-0", "checkmate"))
        self.assertEqual(matches.score_games([game])["b"]["wins"], 1)

    def test_engine_errors_are_not_forfeit_results_and_close_both_engines(self):
        for value in ["a1a8", RuntimeError("engine failed")]:
            FakeEngine.closed = []
            FakeEngine.choice = value
            with self.assertRaises(RuntimeError):
                matches.play_game({"id": "start", "fen": INITIAL}, {"a": "A", "b": "B"},
                    "a", "go depth 1", 1, 5, FakeEngine)
            self.assertEqual(FakeEngine.closed, ["B", "A"])

    def test_main_pairs_colors_and_keeps_caps_unscored(self):
        source = pathlib.Path(matches.__file__).resolve()
        output = io.StringIO()
        def game(opening, binaries, white, go, max_plies, timeout, profiles=None):
            return {"white": white, "black": "b" if white == "a" else "a", "result": "*", "reason": "searched_ply_limit"}
        arguments = [str(source), str(source), str(source), "--depth", "1", "--seed", "123", "--max-plies", "2"]
        with patch.object(matches.sys, "argv", arguments), patch.object(matches.sys, "stdout", output):
            with patch.object(matches, "play_game", side_effect=game) as play:
                matches.main()
        report = json.loads(output.getvalue())
        self.assertEqual([call.args[2] for call in play.call_args_list], ["a", "b", "b", "a", "a", "b"])
        self.assertEqual(report["policy"]["schedule_seed"], 123)
        self.assertEqual([call.args[0]["id"] for call in play.call_args_list],
            [pair["opening"] for pair in report["policy"]["pair_schedule"] for _ in range(2)])
        self.assertEqual([game["pair_game"] for game in report["games"]], [1, 2] * 3)
        self.assertEqual(len(report["games"]), 6)
        self.assertEqual(report["scores"]["a"], {"wins": 0, "losses": 0, "draws": 0, "unfinished": 6})
        self.assertEqual(report["engines"]["a"]["sha256"], matches.digest(source))

    def test_node_budget_is_forwarded_without_implicit_depth_and_recorded(self):
        source = pathlib.Path(matches.__file__).resolve()
        for value in (1, 64, (1 << 64) - 1):
            output = io.StringIO()
            arguments = [str(source), str(source), str(source), "--nodes", str(value), "--max-plies", "2"]
            def game(opening, binaries, white, go, max_plies, timeout, profiles=None):
                self.assertEqual(go, f"go nodes {value}")
                return {"white": white, "black": "b" if white == "a" else "a", "result": "*", "reason": "searched_ply_limit"}
            with self.subTest(value=value), patch.object(matches.sys, "argv", arguments):
                with patch.object(matches.sys, "stdout", output), patch.object(matches, "play_game", side_effect=game) as play:
                    matches.main()
            report = json.loads(output.getvalue())
            self.assertEqual(play.call_count, 6)
            self.assertEqual(report["policy"]["search_budget"], {"kind": "nodes", "value": value})
            self.assertEqual(report["policy"]["go"], f"go nodes {value}")
            self.assertEqual(report["scores"]["a"]["unfinished"], 6)

    def test_invalid_and_conflicting_node_budgets_fail_before_starting_games(self):
        for flags in (["--nodes", "0"], ["--nodes", "-1"], ["--nodes", str(1 << 64)],
            ["--nodes", "1", "--depth", "1"], ["--nodes", "1", "--movetime", "1"]):
            with self.subTest(flags=flags), patch.object(matches.sys, "argv", ["runner", "missing-a", "missing-b", *flags]):
                with patch.object(matches.sys, "stderr", io.StringIO()), patch.object(matches, "play_game") as play:
                    with self.assertRaises(SystemExit) as raised: matches.main()
                    self.assertEqual(raised.exception.code, 2)
                    play.assert_not_called()

    def test_match_output_cannot_overwrite_binary_openings_or_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            a, b = root / "a", root / "b"
            a.write_bytes(b"engine a")
            b.write_bytes(b"engine b")
            openings, profiles = root / "openings.json", root / "profiles.json"
            openings.write_text(pathlib.Path(matches.__file__).with_name("match_openings.json").read_text())
            profiles.write_text('{"version":1,"engines":{"a":{},"b":{}}}')
            for output in (a, b, openings, profiles):
                original = output.read_bytes()
                arguments = ["runner", str(a), str(b), "--openings", str(openings), "--profiles", str(profiles), "--output", str(output)]
                with self.subTest(output=output), patch.object(matches.sys, "argv", arguments):
                    with patch.object(matches.sys, "stderr", io.StringIO()), patch.object(matches, "play_game") as play:
                        with self.assertRaises(SystemExit) as error: matches.main()
                        self.assertEqual(error.exception.code, 2)
                        play.assert_not_called()
                self.assertEqual(output.read_bytes(), original)

    def test_schedule_is_repeatable_complete_balanced_and_does_not_mutate_openings(self):
        openings = [{"id": name} for name in ("a", "b", "c")]
        plan = matches.build_schedule(openings, 4, 123)
        self.assertEqual(plan, matches.build_schedule(openings, 4, 123))
        self.assertEqual(openings, [{"id": name} for name in ("a", "b", "c")])
        self.assertEqual(len(plan), 12)
        for round_number in range(1, 5):
            self.assertEqual(sorted(pair["opening"] for pair in plan if pair["round"] == round_number), ["a", "b", "c"])
        balance = 0
        for index, pair in enumerate(plan, 1):
            self.assertEqual(pair["pair"], index)
            self.assertEqual(set(pair["white_order"]), {"a", "b"})
            balance += 1 if pair["white_order"][0] == "a" else -1
            self.assertLessEqual(abs(balance), 1)

    def test_schedule_rejects_invalid_seed_rounds_and_opening_identity(self):
        for rounds, seed in ((0, 0), (True, 0), (1, -1), (1, 1 << 64), (1, True)):
            with self.subTest(rounds=rounds, seed=seed), self.assertRaises(ValueError):
                matches.build_schedule([{"id": "one"}], rounds, seed)
        for openings in ([], [{"id": "same"}, {"id": "same"}], [{"id": ""}]):
            with self.subTest(openings=openings), self.assertRaises(ValueError):
                matches.build_schedule(openings, 1, 0)

    def test_protocol_error_and_eof_are_not_bestmoves(self):
        for event in ["info string error: invalid command", None]:
            engine = matches.Engine("fake", 1)
            engine.events.put(event)
            with self.assertRaises(RuntimeError):
                engine.until("bestmove")
        engine = matches.Engine("fake", 0)
        with self.assertRaisesRegex(RuntimeError, "timeout"):
            engine.until("uciok")

    def profile_engine(self, profile):
        engine = matches.Engine("fake", 1, profile)
        for line in ["option name Experimental LMR type check default false",
            "option name Check Extension Limit type spin default 1 min 0 max 4", "uciok"]:
            engine.events.put(line)
        engine.until("uciok")
        engine.send = Mock()
        return engine

    def test_profiles_use_advertised_types_bounds_and_canonical_names(self):
        engine = self.profile_engine({"experimental lmr": True, "Check Extension Limit": 2})
        engine.apply_profile()
        self.assertEqual([call.args[0] for call in engine.send.call_args_list],
            ["setoption name Experimental LMR value true", "setoption name Check Extension Limit value 2"])
        self.assertEqual(engine.applied_options, {"Experimental LMR": True, "Check Extension Limit": 2})

    def test_invalid_profiles_send_no_partial_option_changes(self):
        for profile in [{"Experimental LMR": 1}, {"Check Extension Limit": True},
            {"Experimental LMR": True, "Check Extension Limit": 5}, {"Unknown": False}]:
            engine = self.profile_engine(profile)
            with self.subTest(profile=profile), self.assertRaises(ValueError): engine.apply_profile()
            engine.send.assert_not_called()

    def test_duplicate_profile_names_and_json_keys_are_rejected(self):
        with self.assertRaises(ValueError): matches.validate_profile({"Foo": True, "foo": False})
        path = Mock()
        path.read_text.return_value = '{"version":1,"engines":{"a":{"Foo":true,"Foo":false}}}'
        with self.assertRaises(ValueError): matches.load_profiles(path)
        path.read_text.return_value = json.dumps({"version": 1, "engines": {"c": {}}})
        with self.assertRaises(ValueError): matches.load_profiles(path)

    def test_profile_names_cannot_add_protocol_lines_or_ambiguous_padding(self):
        for name in ("", " ", " Foo", "Foo ", "Foo\nquit", "Foo\rBar", "Foo\tBar", "Foo\x7f"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                matches.validate_profile({name: True})

    def test_game_records_each_engine_profile(self):
        profiles = {"a": {"Experimental LMR": True}, "b": {"Experimental LMR": False}}
        game = matches.play_game({"id": "start", "fen": INITIAL}, {"a": "A", "b": "B"},
            "a", "go depth 1", 1, 5, FakeEngine, profiles)
        self.assertEqual(game["applied_options"], profiles)

    def test_invalid_duplicate_and_finished_openings_are_rejected(self):
        path = Mock()
        start = {"id": "start", "fen": INITIAL}
        for openings in [[start, start], [{"id": "bad", "fen": INITIAL, "moves": ["e2e5"]}],
            [{"id": "ended", "fen": "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"}]]:
            path.read_text.return_value = json.dumps({"version": 1, "openings": openings})
            with self.assertRaises(ValueError):
                matches.load_openings(path)


if __name__ == "__main__":
    unittest.main()
