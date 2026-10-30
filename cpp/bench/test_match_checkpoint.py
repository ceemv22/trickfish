import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import match_checkpoint as checkpoints
import uci_matches as matches
from export_matches import export_report, render_game
from trickfish.position import Position
from test_uci_matches import FakeEngine


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        FakeEngine.closed = []
        FakeEngine.choice = None
        self.original_play = matches.play_game

    def arguments(self, root):
        a, b = root / "a", root / "b"
        a.write_text("engine a")
        b.write_text("engine b")
        profiles = root / "profiles.json"
        profiles.write_text('{"version":1,"engines":{"a":{"Experimental Pawn Cache":true},"b":{}}}')
        return ["runner", str(a), str(b), "--nodes", "16", "--max-plies", "1", "--seed", "12",
            "--profiles", str(profiles), "--checkpoint", str(root / "checkpoint.json"), "--output", str(root / "report.json")]

    def fake_game(self, opening, binaries, white, go, max_plies, timeout, profiles=None):
        return self.original_play(opening, binaries, white, go, max_plies, timeout,
            engine_factory=FakeEngine, profiles=profiles)

    def run_main(self, arguments, side_effect=None):
        with patch.object(matches.sys, "argv", arguments):
            with patch.object(matches, "play_game", side_effect=side_effect or self.fake_game) as play:
                matches.main()
                return play.call_count

    def test_interrupted_pair_resumes_without_replaying_completed_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments = self.arguments(root)
            calls = 0
            def interrupted(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 4: raise RuntimeError("simulated engine failure")
                return self.fake_game(*args, **kwargs)
            with self.assertRaisesRegex(RuntimeError, "simulated engine failure"):
                self.run_main(arguments, interrupted)
            checkpoint = json.loads((root / "checkpoint.json").read_text())
            self.assertEqual(len(checkpoint["games"]), 2)
            self.assertFalse((root / "report.json").exists())
            self.assertEqual(self.run_main(arguments + ["--resume"]), 4)
            report = json.loads((root / "report.json").read_text())
            self.assertEqual(report["games"][:2], checkpoint["games"])
            self.assertEqual(len(report["games"]), 6)
            self.assertEqual(report["scores"]["a"]["unfinished"], 6)
            self.assertIn('[PairGame "2"]', export_report(report))

    def test_completed_resume_starts_no_engines_and_preserves_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments = self.arguments(root)
            self.assertEqual(self.run_main(arguments), 6)
            original = json.loads((root / "report.json").read_text())
            self.assertEqual(self.run_main(arguments + ["--resume"]), 0)
            resumed = json.loads((root / "report.json").read_text())
            self.assertEqual(original["games"], resumed["games"])
            self.assertEqual(original["scores"], resumed["scores"])

    def test_completed_resume_works_through_standalone_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments = self.arguments(root)
            self.run_main(arguments)
            original = json.loads((root / "report.json").read_text())
            result = subprocess.run([sys.executable, str(pathlib.Path(matches.__file__).resolve()),
                *arguments[1:], "--resume"], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            resumed = json.loads((root / "report.json").read_text())
            self.assertEqual(original["games"], resumed["games"])
            self.assertEqual(original["scores"], resumed["scores"])

    def test_configuration_changes_are_rejected_before_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.run_main(self.arguments(root))
            path = root / "checkpoint.json"
            configuration = json.loads(path.read_text())["configuration"]
            for field in ("binary", "openings", "profile", "budget", "seed", "type"):
                changed = copy.deepcopy(configuration)
                if field == "binary": changed["engines"]["a"]["sha256"] = "0" * 64
                elif field == "openings": changed["openings"]["sha256"] = "0" * 64
                elif field == "profile": changed["profiles"]["a"]["Experimental Pawn Cache"] = False
                elif field == "budget": changed["policy"]["go"] = "go nodes 17"
                elif field == "seed": changed["policy"]["schedule_seed"] = 13
                else: changed["policy"]["rounds"] = True
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "configuration differs"):
                    checkpoints.load_checkpoint(path, changed)

    def test_corrupted_games_and_checkpoint_shape_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.run_main(self.arguments(root))
            path = root / "checkpoint.json"
            original = json.loads(path.read_text())
            for field in ("version", "odd", "move", "result", "pair", "root", "profile"):
                damaged = copy.deepcopy(original)
                if field == "version": damaged["checkpoint_version"] = True
                elif field == "odd": damaged["games"].pop()
                elif field == "move": damaged["games"][0]["moves"][-1] = "a1a8"
                elif field == "result": damaged["games"][0]["result"] = "1-0"
                elif field == "pair": damaged["games"][0]["pair_game"] = 2
                elif field == "root": damaged["games"][0]["root_fen"] = damaged["games"][0]["final_fen"]
                else: damaged["games"][0]["applied_options"]["a"] = {}
                path.write_text(json.dumps(damaged))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    checkpoints.load_checkpoint(path, original["configuration"])

    def test_legal_replay_from_a_different_opening_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self.run_main(self.arguments(root))
            path = root / "checkpoint.json"
            data = json.loads(path.read_text())
            configuration = data["configuration"]
            first = data["games"][0]
            position = Position.from_fen(first["root_fen"])
            move = next(move for move in position.legal_moves() if move.to_uci() == first["moves"][0])
            new_root = position.make_move(move).to_fen()
            for game in data["games"][:2]:
                game["root_fen"] = new_root
                game["moves"] = game["moves"][1:]
                game["opening_plies"] -= 1
                render_game(game, configuration["engines"], configuration["policy"])
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "differs from source opening"):
                checkpoints.load_checkpoint(path, configuration)

    def test_atomic_replace_failure_preserves_previous_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            path = root / "checkpoint.json"
            checkpoints.save_checkpoint(path, {"sentinel": 1}, [])
            original = path.read_bytes()
            with patch.object(checkpoints.os, "replace", side_effect=OSError("simulated write failure")):
                with self.assertRaises(OSError): checkpoints.save_checkpoint(path, {"sentinel": 2}, [])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_existing_temporary_name_is_not_deleted_on_create_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            path = root / "checkpoint.json"
            temporary = root / ".checkpoint.json.occupied.tmp"
            temporary.write_text("unrelated content")
            with patch.object(checkpoints.uuid, "uuid4", return_value=Mock(hex="occupied")):
                with self.assertRaises(FileExistsError): checkpoints.save_checkpoint(path, {}, [])
            self.assertEqual(temporary.read_text(), "unrelated content")
            self.assertFalse(path.exists())

    def test_checkpoint_paths_and_fresh_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            arguments = self.arguments(root)
            self.run_main(arguments)
            checkpoint = root / "checkpoint.json"
            original = checkpoint.read_bytes()
            variants = [arguments, arguments + ["--output", str(checkpoint)],
                arguments + ["--checkpoint", str(root / "a")]]
            for flags in variants:
                with self.subTest(flags=flags), patch.object(matches.sys, "argv", flags):
                    with patch.object(matches.sys, "stderr", io.StringIO()), patch.object(matches, "play_game") as play:
                        with self.assertRaises(SystemExit): matches.main()
                        play.assert_not_called()
            self.assertEqual(checkpoint.read_bytes(), original)
        with patch.object(matches.sys, "argv", ["runner", "a", "b", "--resume"]):
            with patch.object(matches.sys, "stderr", io.StringIO()), self.assertRaises(SystemExit): matches.main()


if __name__ == "__main__":
    unittest.main()
