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
import match_campaign as campaign
import uci_matches as matches
from search_benchmark import digest
from test_uci_matches import FakeEngine, INITIAL


class CampaignTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.closed = []
        FakeEngine.choice = None
        self.original_play = matches.play_game

    def prepare(self, root):
        a, b = root / "a", root / "b"
        a.write_text("candidate")
        b.write_text("reference")
        openings = root / "openings.json"
        openings.write_text(json.dumps({"version": 1, "openings": [
            {"id": "e4", "fen": INITIAL, "moves": ["e2e4", "e7e5"]},
            {"id": "d4", "fen": INITIAL, "moves": ["d2d4", "d7d5"]}]}))
        plan = root / "plan.json"
        data = {"version": 1, "name": "test campaign", "openings": "openings.json", "openings_sha256": digest(openings),
            "opening_ids": ["e4", "d4"], "profiles": None, "profiles_sha256": None,
            "search_budget": {"kind": "nodes", "value": 64}, "rounds": 1, "seed": 42, "max_plies": 2, "timeout": 10}
        plan.write_text(json.dumps(data))
        return ["runner", str(a), str(b), "--campaign", str(plan), "--output", str(root / "report.json")], plan, data

    def fake_game(self, opening, binaries, white, go, max_plies, timeout, profiles=None):
        return self.original_play(opening, binaries, white, go, max_plies, timeout,
            engine_factory=FakeEngine, profiles=profiles)

    def run_match(self, arguments, effect=None):
        with patch.object(matches.sys, "argv", arguments), patch.object(matches, "play_game", side_effect=effect or self.fake_game) as play:
            matches.main()
            return play.call_count

    def test_campaign_controls_report_replay_and_completed_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments, plan, _ = self.prepare(root)
            arguments += ["--checkpoint", str(root / "checkpoint.json")]
            self.assertEqual(self.run_match(arguments), 4)
            report = json.loads((root / "report.json").read_text())
            audit = campaign.audit_campaign(report, plan)
            self.assertTrue(audit["completed_schedule_replayed"])
            self.assertEqual(audit["analysis"]["paired"]["pairs"], 2)
            self.assertEqual(audit["analysis"]["overall"]["games"], 4)
            self.assertEqual(self.run_match(arguments + ["--resume"]), 0)
            self.assertEqual(json.loads((root / "report.json").read_text())["games"], report["games"])
            completed = subprocess.run([sys.executable, str(pathlib.Path(campaign.__file__)), str(root / "report.json"),
                "--campaign", str(plan)], capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["plan_controls_match"])

    def test_invalid_plan_types_ranges_hashes_and_opening_identity_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            _, plan, original = self.prepare(pathlib.Path(directory))
            for key, value in (("version", True), ("rounds", True), ("seed", -1), ("max_plies", 0), ("timeout", 0),
                    ("openings_sha256", "0" * 64), ("opening_ids", ["d4", "e4"]),
                    ("search_budget", {"kind": "nodes", "value": True}), ("extra", 1)):
                data = copy.deepcopy(original)
                data[key] = value
                plan.write_text(json.dumps(data))
                with self.assertRaises(ValueError): campaign.load_campaign(plan)
            plan.write_text('{"version":1,"version":1}')
            with self.assertRaisesRegex(ValueError, "duplicate"): campaign.load_campaign(plan)

    def test_override_controls_are_rejected_before_starting_engines(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments, _, _ = self.prepare(pathlib.Path(directory))
            for option, value in (("--nodes", "64"), ("--depth", "1"), ("--seed", "42"), ("--rounds", "1"),
                    ("--max-plies", "2"), ("--timeout", "10"), ("--openings", "missing"), ("--profiles", "missing")):
                with patch.object(matches.sys, "stderr", io.StringIO()):
                    with self.assertRaises(SystemExit): self.run_match(arguments + [option, value])

    def test_source_aliases_and_source_mutation_do_not_produce_a_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments, plan, _ = self.prepare(root)
            original = plan.read_bytes()
            with patch.object(matches.sys, "stderr", io.StringIO()):
                with self.assertRaises(SystemExit): self.run_match(arguments[:-1] + [str(plan)])
            self.assertEqual(plan.read_bytes(), original)
            calls = 0
            def changed(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1: plan.write_bytes(original + b"\n")
                return self.fake_game(*args, **kwargs)
            with self.assertRaisesRegex(RuntimeError, "changed"):
                self.run_match(arguments, changed)
            self.assertFalse((root / "report.json").exists())

    def test_audit_rejects_changed_controls_even_when_python_values_compare_equal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments, plan, _ = self.prepare(root)
            self.run_match(arguments)
            report = json.loads((root / "report.json").read_text())
            for key, value in (("rounds", True), ("schedule_seed", 43), ("go", "go depth 1"), ("searched_ply_limit", 3)):
                changed = copy.deepcopy(report)
                changed["policy"][key] = value
                with self.assertRaisesRegex(ValueError, "controls"): campaign.audit_campaign(changed, plan)
            changed = copy.deepcopy(report)
            changed["campaign"]["specification"]["version"] = True
            with self.assertRaisesRegex(ValueError, "provenance"): campaign.audit_campaign(changed, plan)
            report["games"][-1]["moves"][-1] = "a1a8"
            with self.assertRaises(ValueError): campaign.audit_campaign(report, plan)

    def test_duplicate_final_openings_and_changed_plan_on_resume_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments, plan, data = self.prepare(root)
            self.run_match(arguments + ["--checkpoint", str(root / "checkpoint.json")])
            data["seed"] += 1
            plan.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "configuration"):
                self.run_match(arguments + ["--checkpoint", str(root / "checkpoint.json"), "--resume"])
            openings = root / "openings.json"
            values = json.loads(openings.read_text())
            values["openings"][1]["moves"] = values["openings"][0]["moves"]
            openings.write_text(json.dumps(values))
            data["openings_sha256"] = digest(openings)
            plan.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "duplicate final"): campaign.load_campaign(plan)

    def test_versioned_campaigns_have_twelve_distinct_legal_roots(self):
        for name in ("campaign_smoke.json", "campaign_fixed_nodes.json"):
            loaded = campaign.load_campaign(pathlib.Path(__file__).with_name(name))
            self.assertEqual(len(loaded["openings"]), 12)

    def test_profile_bytes_are_bound_and_audit_output_cannot_replace_the_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments, plan, data = self.prepare(root)
            profiles = root / "profiles.json"
            profiles.write_text(json.dumps({"version": 1, "engines": {"a": {"Experimental Pawn Cache": True}, "b": {}}}))
            data.update(profiles=profiles.name, profiles_sha256=digest(profiles))
            plan.write_text(json.dumps(data))
            self.run_match(arguments)
            report = root / "report.json"
            campaign.audit_campaign(json.loads(report.read_text()), plan)
            original = plan.read_bytes()
            with patch.object(campaign.sys, "argv", ["audit", str(report), "--campaign", str(plan), "--output", str(plan)]):
                with self.assertRaisesRegex(ValueError, "output must differ"): campaign.main()
            self.assertEqual(plan.read_bytes(), original)
            profiles.write_text('{"version":1,"engines":{}}')
            with self.assertRaisesRegex(ValueError, "hash mismatch"): campaign.load_campaign(plan)


if __name__ == "__main__":
    unittest.main()
