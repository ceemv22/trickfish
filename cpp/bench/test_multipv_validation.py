import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import multipv_validation as validator


def sample(depth=1, count=3):
    roots = ["b1c3", "d2d4", "e2e4"][:count]
    return {"schema_version": 1, "completed_depth": depth, "nodes": 2 * count, "stopped": False,
        "lines": [{"rank": index + 1, "score": 30 - index * 10, "completed_depth": depth, "nodes": 2,
            "bestmove": move, "pv": [move]} for index, move in enumerate(roots)]}


class MultiPVValidationTests(unittest.TestCase):
    def test_ranked_legal_pvs_and_special_moves_replay_independently(self):
        data = sample()
        original = copy.deepcopy(data)
        result = validator.validate_result(data, validator.STARTING_FEN, 1, 3)
        self.assertEqual(data, original)
        self.assertEqual(result["bestmoves"], ["b1c3", "d2d4", "e2e4"])
        for _, fen, depth, count in validator.cases()[1:4]:
            roots = sorted(move.to_uci() for move in validator.Position.from_fen(fen).legal_moves())[:count]
            data = {"schema_version": 1, "completed_depth": depth, "nodes": len(roots), "stopped": False,
                "lines": [{"rank": index + 1, "score": 0, "completed_depth": depth, "nodes": 1, "bestmove": move,
                    "pv": [move]} for index, move in enumerate(roots)]}
            self.assertEqual(validator.validate_result(data, fen, depth, count)["lines"], len(roots))

    def test_corrupt_schema_depth_rank_order_work_and_root_moves_are_rejected(self):
        for field in ("schema", "bool_rank", "bool_score", "bool_nodes", "depth", "count", "stopped_partial", "duplicate", "illegal", "pv", "rank", "order", "work"):
            data = sample(2)
            if field == "schema": data["extra"] = 0
            elif field == "bool_rank": data["lines"][0]["rank"] = True
            elif field == "bool_score": data["lines"][0]["score"] = True
            elif field == "bool_nodes": data["nodes"] = True
            elif field == "depth": data["lines"][1]["completed_depth"] = 1
            elif field == "count": data["lines"].pop()
            elif field == "stopped_partial":
                data["stopped"] = True
                data["lines"].pop()
            elif field == "duplicate": data["lines"][1]["bestmove"] = "b1c3"
            elif field == "illegal": data["lines"][0]["bestmove"] = "a1a8"
            elif field == "pv": data["lines"][0]["pv"] = ["b1c3", "e2e3"]
            elif field == "rank": data["lines"][0]["rank"] = 3
            elif field == "order": data["lines"][1]["score"] = 100
            else: data["nodes"] = 3
            with self.subTest(field=field), self.assertRaises(ValueError):
                validator.validate_result(data, validator.STARTING_FEN, 2, 3)

    def test_terminal_and_depth_zero_fallback_semantics(self):
        winning = "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"
        positive = {"schema_version": 1, "completed_depth": 1, "nodes": 1, "stopped": False,
            "lines": [{"rank": 1, "score": 99999, "completed_depth": 1, "nodes": 1, "bestmove": "g6g7", "pv": ["g6g7"]}]}
        self.assertEqual(validator.validate_result(positive, winning, 1, 1)["scores"], [99999])
        positive["lines"][0].update(bestmove="g6g5", pv=["g6g5"])
        with self.assertRaisesRegex(ValueError, "immediate mate"): validator.validate_result(positive, winning, 1, 1)
        mate = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"
        data = {"schema_version": 1, "completed_depth": 1, "nodes": 1, "stopped": False,
            "lines": [{"rank": 1, "score": -100000, "completed_depth": 1, "nodes": 1, "bestmove": None, "pv": []}]}
        self.assertEqual(validator.validate_result(data, mate, 2, 3)["scores"], [-100000])
        data["lines"][0]["score"] = 0
        with self.assertRaisesRegex(ValueError, "terminal"): validator.validate_result(data, mate, 2, 3)
        data = {"schema_version": 1, "completed_depth": 0, "nodes": 0, "stopped": True,
            "lines": [{"rank": 1, "score": 0, "completed_depth": 0, "nodes": 0, "bestmove": "e2e4", "pv": []}]}
        self.assertEqual(validator.validate_result(data, validator.STARTING_FEN, 4, 3)["depth"], 0)
        data["lines"][0]["bestmove"] = None
        with self.assertRaises(ValueError): validator.validate_result(data, validator.STARTING_FEN, 4, 3)

    def test_runner_single_pv_parity_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / "engine"
            binary.write_bytes(b"synthetic engine fixture")
            output = binary.with_name("validation.json")
            def run(command, **kwargs):
                if command[1] == "--search":
                    text = "bestmove e2e4\nscore 10\npv e2e4\ndepth 2\nstopped false\nnodes 42\n"
                elif command[3] == "1":
                    data = sample(2, 1)
                    data["nodes"] = data["lines"][0]["nodes"] = 42
                    data["lines"][0].update(score=10, bestmove="e2e4", pv=["e2e4"])
                    text = json.dumps(data)
                else: text = json.dumps(sample())
                return subprocess.CompletedProcess(command, 0, text, "")
            argv = ["validator", str(binary), "--output", str(output)]
            with patch.object(validator.sys, "argv", argv), patch.object(validator, "cases", return_value=[("fixture", validator.STARTING_FEN, 1, 3)]), patch.object(validator.subprocess, "run", side_effect=run):
                validator.main()
            report = json.loads(output.read_text())
            self.assertTrue(report["single_pv_trace_identical"])
            self.assertEqual(report["binary_sha256"], validator.digest(binary))
            original = binary.read_bytes()
            with patch.object(validator.sys, "argv", ["validator", str(binary), "--output", str(binary)]), patch.object(validator.subprocess, "run") as runner:
                with self.assertRaises(ValueError): validator.main()
                runner.assert_not_called()
            self.assertEqual(binary.read_bytes(), original)

    def test_malformed_native_result_leaves_no_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / "engine"
            binary.write_bytes(b"fixture")
            output = binary.with_name("validation.json")
            with patch.object(validator.sys, "argv", ["validator", str(binary), "--output", str(output)]), patch.object(validator.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")):
                with self.assertRaises(ValueError): validator.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
