import copy
from decimal import Decimal
import itertools
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assess_match as assessor
from match_campaign import load_campaign
from test_analyze_matches import OUTCOMES
from test_export_matches import make_report
from trickfish.position import Position, STARTING_FEN
from uci_matches import build_schedule, DRAW_POLICY, score_games


def fixture(root, outcomes):
    candidate, baseline = root / "candidate", root / "baseline"
    candidate.write_text("candidate")
    baseline.write_text("baseline")
    openings = []
    variants = [None, (48, 40), (48, 32), (49, 41), (49, 33), (50, 42)]
    for index in range(len(outcomes)):
        board = list(Position.from_fen(STARTING_FEN).board)
        if variants[index] is not None:
            source, target = variants[index]
            board[target], board[source] = board[source], None
        fen = Position(tuple(board), "w", "KQkq", None, 0, 1).to_fen()
        openings.append({"id": str(index), "fen": fen})
    opening_path = root / "openings.json"
    opening_path.write_text(json.dumps({"version": 1, "openings": openings}))
    campaign_path = root / "campaign.json"
    campaign_path.write_text(json.dumps({"version": 1, "name": "synthetic validation only", "openings": "openings.json",
        "openings_sha256": assessor.digest(opening_path), "opening_ids": [item["id"] for item in openings],
        "profiles": None, "profiles_sha256": None, "search_budget": {"kind": "nodes", "value": 64},
        "rounds": 1, "seed": 42, "max_plies": 8, "timeout": 30}))
    plan_path = root / "sign-plan.json"
    plan = assessor.create_plan(candidate, baseline, campaign_path)
    plan_path.write_text(json.dumps(plan))
    campaign = load_campaign(campaign_path)
    schedule = build_schedule(openings, 1, 42)
    games = []
    for pair in schedule:
        opening = openings[int(pair["opening"])]
        for pair_game, white in enumerate(pair["white_order"], 1):
            kind = outcomes[int(pair["opening"])][0 if white == "a" else 1]
            moves, result, reason = OUTCOMES[kind]
            game = make_report(opening["fen"], moves, result, reason)["games"][0]
            if white == "b":
                game.update(white="b", black="a")
                for decision in game["decisions"]:
                    decision["engine"] = "b" if decision["engine"] == "a" else "a"
            game.update(opening=opening["id"], pair=pair["pair"], pair_game=pair_game, applied_options={"a": {}, "b": {}})
            games.append(game)
    report = {"schema_version": 1, "campaign": campaign["metadata"], "openings": {"path": str(opening_path),
        "sha256": assessor.digest(opening_path)}, "profiles": {"a": {}, "b": {}}, "profile_source": None,
        "engines": {"a": {"path": str(candidate), "sha256": assessor.digest(candidate)},
            "b": {"path": str(baseline), "sha256": assessor.digest(baseline)}},
        "policy": {"go": "go nodes 64", "search_budget": {"kind": "nodes", "value": 64}, "rounds": 1,
            "searched_ply_limit": 8, "watchdog_seconds": 30, "schedule_seed": 42, "pair_schedule": schedule,
            "draws": DRAW_POLICY, "errors": "abort run without assigning a game result", "ply_limit_result": "unfinished"},
        "games": games, "scores": score_games(games)}
    return report, plan_path, candidate, baseline, campaign_path


class SignTests(unittest.TestCase):
    def test_exact_tail_matches_exhaustive_fair_coin_sequences(self):
        for count in range(10):
            sums = [sum(bits) for bits in itertools.product((0, 1), repeat=count)]
            for wins in range(count + 1):
                self.assertEqual(assessor.exact_sign_tail(wins, count - wins),
                    (sum(value >= wins for value in sums), 2 ** count))

    def test_exact_alpha_boundary_ties_and_tiny_tail(self):
        self.assertTrue(assessor.sign_result(5, 0, 0, "0.03125")["null_rejected"])
        self.assertFalse(assessor.sign_result(5, 0, 0, "0.031249999999")["null_rejected"])
        self.assertEqual(assessor.sign_result(0, 0, 6, "0.05")["p_value_decimal"], "1")
        self.assertFalse(assessor.sign_result(0, 6, 0, "0.05")["null_rejected"])
        tiny = assessor.sign_result(4096, 0, 0, "0.05")
        self.assertGreater(Decimal(tiny["p_value_decimal"]), 0)
        self.assertTrue(tiny["null_rejected"])
        for counts in ((True, 0), (-1, 0), (4096, 1), (1.5, 2)):
            with self.assertRaises(ValueError): assessor.exact_sign_tail(*counts)
        for alpha in (0.05, "0", "0.5", "NaN", "1e-2", "0.0000000000001"):
            with self.assertRaises(ValueError): assessor.alpha_ratio(alpha)

    def test_replayed_five_bins_and_sign_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            report, plan, *_ = fixture(pathlib.Path(directory), [("L", "W"), ("L", "D"), ("W", "W"), ("W", "D"), ("W", "L")])
            before = copy.deepcopy(report)
            result = assessor.assess_report(report, plan)
            self.assertEqual(report, before)
            self.assertEqual(result["status"], "evaluated")
            self.assertEqual(result["campaign_audit"]["analysis"]["paired"]["bin_counts"], [1] * 5)
            self.assertEqual(result["statistic"]["wins"], 2)
            self.assertEqual(result["statistic"]["losses"], 2)
            self.assertEqual(result["statistic"]["ties"], 1)
            self.assertEqual(Decimal(result["statistic"]["p_value_decimal"]), Decimal("0.6875"))

    def test_decision_and_unfinished_or_identical_control_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            report, plan, *_ = fixture(pathlib.Path(directory), [("W", "L")] * 5)
            self.assertTrue(assessor.assess_report(report, plan)["statistic"]["null_rejected"])
            data = json.loads(plan.read_text())
            data["baseline_sha256"] = data["candidate_sha256"]
            plan.write_text(json.dumps(data))
            report["engines"]["b"]["sha256"] = data["candidate_sha256"]
            result = assessor.assess_report(report, plan)
            self.assertEqual(result["blockers"], ["identical_binary_bytes"])
            self.assertIsNone(result["statistic"])
        with tempfile.TemporaryDirectory() as directory:
            report, plan, *_ = fixture(pathlib.Path(directory), [("W", "U")])
            result = assessor.assess_report(report, plan)
            self.assertEqual(result["blockers"], ["unfinished_pairs"])
            self.assertIsNone(result["statistic"])

    def test_corrupt_plan_hash_controls_results_and_prefixes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            report, plan, *_ = fixture(pathlib.Path(directory), [("W", "L")])
            original = plan.read_text()
            for key, value in (("version", True), ("pairs", True), ("pairs", 2), ("candidate_label", "b"),
                    ("campaign_sha256", "0" * 64), ("extra", 1), ("alpha", "0.5")):
                data = json.loads(original)
                data[key] = value
                plan.write_text(json.dumps(data))
                with self.subTest(key=key), self.assertRaises(ValueError): assessor.assess_report(report, plan)
            plan.write_text('{"version":1,"version":1}')
            with self.assertRaisesRegex(ValueError, "duplicate"): assessor.load_plan(plan)
            plan.write_text(original)
            for corruption in ("engine", "game", "prefix", "controls"):
                changed = copy.deepcopy(report)
                if corruption == "engine": changed["engines"]["a"]["sha256"] = "0" * 64
                elif corruption == "game": changed["games"][-1]["final_fen"] = STARTING_FEN
                elif corruption == "prefix": changed["games"].pop()
                else: changed["policy"]["search_budget"]["value"] = 1
                with self.subTest(corruption=corruption), self.assertRaises(ValueError): assessor.assess_report(changed, plan)

    def test_cli_plan_and_evaluate_preserve_sources_and_refuse_plan_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            report, plan, candidate, baseline, campaign = fixture(root, [("W", "L")])
            source, output = root / "report.json", root / "assessment.json"
            source.write_text(json.dumps(report))
            tool = str(pathlib.Path(assessor.__file__).resolve())
            def run(*arguments):
                return subprocess.run([sys.executable, tool, *map(str, arguments)], capture_output=True, text=True, timeout=30)
            created = root / "created-plan.json"
            result = run("plan", candidate, baseline, "--campaign", campaign, "--output", created)
            self.assertEqual(result.returncode, 0, result.stderr)
            for protected in (candidate, baseline, campaign, root / "openings.json"):
                original = protected.read_bytes()
                self.assertNotEqual(run("plan", candidate, baseline, "--campaign", campaign, "--output", protected).returncode, 0)
                self.assertEqual(protected.read_bytes(), original)
            original = created.read_bytes()
            self.assertNotEqual(run("plan", candidate, baseline, "--campaign", campaign, "--output", created).returncode, 0)
            self.assertEqual(created.read_bytes(), original)
            result = run("evaluate", source, "--plan", created, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["source_report"]["sha256"], assessor.digest(source))
            for protected in (source, created, candidate, baseline, campaign, root / "openings.json"):
                original = protected.read_bytes()
                self.assertNotEqual(run("evaluate", source, "--plan", created, "--output", protected).returncode, 0)
                self.assertEqual(protected.read_bytes(), original)
            report["games"][-1]["moves"][0] = "a1a8"
            source.write_text(json.dumps(report))
            output.unlink()
            self.assertNotEqual(run("evaluate", source, "--plan", created, "--output", output).returncode, 0)
            self.assertFalse(output.exists())

    def test_repeated_opening_rounds_and_changed_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            report, plan, candidate, baseline, campaign = fixture(root, [("W", "L")])
            original = campaign.read_text()
            data = json.loads(original)
            data["rounds"] = 2
            campaign.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "one round"):
                assessor.create_plan(candidate, baseline, campaign)
            with self.assertRaises(ValueError): assessor.assess_report(report, plan)
            campaign.write_text(original)
            audit = assessor.audit_campaign
            def mutate(*args):
                result = audit(*args)
                plan.write_bytes(plan.read_bytes() + b"\n")
                return result
            with patch.object(assessor, "audit_campaign", side_effect=mutate):
                with self.assertRaisesRegex(ValueError, "plan changed"): assessor.assess_report(report, plan)


if __name__ == "__main__":
    unittest.main()
