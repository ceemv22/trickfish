import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ponder_validation as validator
from uci_matches import Engine, parse_bestmove, validate_prediction
from trickfish.position import Position, STARTING_FEN


def completed_records(hint=True):
    return ["info depth 1 nodes 21 time 0 nps 0 score cp 30 pv e2e4",
        "info depth 2 nodes 120 time 1 nps 120000 score cp 0 pv e2e4 e7e5",
        "bestmove e2e4" + (" ponder e7e5" if hint else "")]


class PonderValidationTests(unittest.TestCase):
    def test_search_error_aborts_a_client_wait_without_needing_bestmove(self):
        engine = Engine("synthetic fixture", 1)
        engine.events.put("info string search error: injected failure")
        with self.assertRaisesRegex(RuntimeError, "search failed"):
            engine.until("bestmove")

    def test_bestmove_and_prediction_shapes_are_strict(self):
        self.assertEqual(parse_bestmove("bestmove e2e4 ponder e7e5"), ("e2e4", "e7e5"))
        self.assertEqual(parse_bestmove("bestmove a7b8n"), ("a7b8n", None))
        self.assertEqual(parse_bestmove("bestmove 0000"), ("0000", None))
        for line in (None, "", "bestmove", "bestmove e2e4 extra", "bestmove e2e4 other e7e5",
                "bestmove 0000 ponder e7e5", "bestmove e2e9", "bestmove e2e4 ponder e7e9", "bestmove e2e4 ponder e7e5 extra"):
            with self.subTest(line=line), self.assertRaises(RuntimeError): parse_bestmove(line)

    def test_legal_reply_validation_handles_specials_and_rejects_wrong_sides(self):
        validate_prediction(Position.from_fen(STARTING_FEN), "e2e4", "e7e5")
        validate_prediction(Position.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"), "e1g1", "e8c8")
        validate_prediction(Position.from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1"), "a7a8n", "e8d7")
        for best, prediction in (("e2e5", "e7e5"), ("e2e4", "e2e3"), ("e2e4", "e7e4")):
            with self.subTest(best=best, prediction=prediction), self.assertRaises(RuntimeError):
                validate_prediction(Position.from_fen(STARTING_FEN), best, prediction)

    def test_match_client_replays_prefix_and_clears_stale_predictions(self):
        engine = Engine("synthetic fixture", 1)
        engine.send = Mock()
        engine.until = Mock(side_effect=[("readyok", None), ("bestmove e7e5 ponder g1f3", "info depth 2")])
        best, info, _ = engine.choose(STARTING_FEN, iter(["e2e4"]), "go depth 2")
        self.assertEqual((best, info, engine.last_ponder), ("e7e5", "info depth 2", "g1f3"))
        engine.send.assert_any_call("position fen " + STARTING_FEN + " moves e2e4")
        engine.until = Mock(side_effect=[("readyok", None), ("bestmove e7e5", "info depth 1")])
        engine.choose(STARTING_FEN, ["e2e4"], "go depth 1")
        self.assertIsNone(engine.last_ponder)
        engine.until = Mock(side_effect=[("readyok", None), ("bestmove e7e5 ponder e7e6", "info depth 2")])
        with self.assertRaises(RuntimeError): engine.choose(STARTING_FEN, ["e2e4"], "go depth 2")
        self.assertIsNone(engine.last_ponder)

    def test_reply_replay_binds_one_bestmove_to_primary_pv_and_option_snapshot(self):
        records = completed_records()
        original = copy.deepcopy(records)
        summary = validator.validate_reply(records, STARTING_FEN, 1, True)
        self.assertEqual(records, original)
        self.assertEqual(summary["ponder_move"], "e7e5")
        self.assertEqual(summary["nodes"], 120)
        for changed, enabled in ((records, False), (completed_records(False), True),
                (records + [records[-1]], True), (records[:-1] + ["bestmove d2d4 ponder d7d5"], True),
                (records[:-1] + ["bestmove e2e4 ponder e7e6"], True)):
            with self.subTest(changed=changed, enabled=enabled), self.assertRaises(ValueError):
                validator.validate_reply(changed, STARTING_FEN, 1, enabled)

    def test_pending_barriers_and_recorded_queue_detect_early_reply(self):
        validator.require_pending(completed_records()[:-1])
        with self.assertRaises(ValueError): validator.require_pending(completed_records())
        records = []
        events = validator.RecordedQueue(records)
        events.put("info depth 1")
        events.put(None)
        self.assertEqual(events.get(), "info depth 1")
        self.assertIsNone(events.get())
        self.assertEqual(records, ["info depth 1"])

    def test_cli_output_protection_and_failed_probe_do_not_publish_success(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / "engine"
            binary.write_bytes(b"synthetic ponder engine")
            output = binary.with_name("ponder.json")
            argv = ["validator", str(binary), "--output", str(output)]
            with patch.object(validator.sys, "argv", argv), patch.object(validator, "run_probes", return_value=[{"id": "fixture"}]):
                validator.main()
            report = json.loads(output.read_text())
            self.assertEqual(report["binary_sha256"], validator.digest(binary))
            original = binary.read_bytes()
            with patch.object(validator.sys, "argv", ["validator", str(binary), "--output", str(binary)]), patch.object(validator, "run_probes") as run:
                with self.assertRaises(ValueError): validator.main()
                run.assert_not_called()
            self.assertEqual(binary.read_bytes(), original)
            output.unlink()
            with patch.object(validator.sys, "argv", argv), patch.object(validator, "run_probes", side_effect=RuntimeError("synthetic probe failure")):
                with self.assertRaises(RuntimeError): validator.main()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
