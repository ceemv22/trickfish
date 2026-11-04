import pathlib
import sys
import unittest

from trickfish.objective_uci import UciObjective
from trickfish.position import Position, STARTING_FEN


FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "objective_engine.py"


class ObjectiveUciTests(unittest.TestCase):
    def engine(self, mode="cp", timeout=2):
        return UciObjective([sys.executable, str(FIXTURE), mode], depth=3, timeout=timeout)

    def test_real_process_handshake_orientation_cache_and_receipt(self):
        with self.engine() as engine:
            position = Position.from_fen(STARTING_FEN)
            self.assertEqual(engine(position, "w"), 35)
            self.assertEqual(engine(position, "b"), -35)
            receipt = engine.provenance()
            self.assertEqual(len(receipt["evaluations"]), 1)
            self.assertEqual(len(receipt["executable_sha256"]), 64)
            self.assertIn("Synthetic Objective Fixture", receipt["identity"][0])
            self.assertEqual(engine.continuation(position), ("e2e4",))
            self.assertEqual(receipt["evaluations"][0]["pv"], ["e2e4"])
            self.assertNotEqual(receipt["evaluations"][0]["pv_final_fen"], STARTING_FEN)
        self.assertIsNotNone(engine.process.poll())

    def test_rejects_bound_mate_shallow_illegal_and_eof(self):
        for mode in ("bound", "mate", "shallow", "illegal", "eof"):
            with self.subTest(mode=mode), self.engine(mode) as engine:
                with self.assertRaises((ValueError, RuntimeError)):
                    engine(Position.from_fen(STARTING_FEN), "w")
                self.assertIsNotNone(engine.process.poll())

    def test_timeout_cleans_up_process(self):
        with self.engine("timeout", timeout=1) as engine:
            with self.assertRaises(TimeoutError):
                engine(Position.from_fen(STARTING_FEN), "w")
            self.assertIsNotNone(engine.process.poll())

    def test_invalid_or_missing_pv_fails_with_process_cleanup(self):
        for mode in ("pv-missing", "pv-empty", "pv-mismatch", "pv-illegal-tail"):
            with self.subTest(mode=mode), self.engine(mode) as engine:
                with self.assertRaises(ValueError):
                    engine.evaluate(Position.from_fen(STARTING_FEN), "w")
                self.assertIsNotNone(engine.process.poll())

    def test_typed_mate_sign_distance_cache_and_terminal_zero(self):
        for mode, winning in (("mate", True), ("mate-loss", False)):
            with self.subTest(mode=mode), self.engine(mode) as engine:
                position = Position.from_fen(STARTING_FEN)
                score = engine.evaluate(position, "w")
                self.assertEqual((score.mate_moves, score.winning), (2, winning))
                self.assertIsNone(score.cp)
                self.assertEqual(engine.evaluate(position, "b").winning, not winning)
                self.assertEqual(len(engine.records), 1)
        with self.engine() as engine:
            mate = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
            self.assertFalse(engine.evaluate(mate, "b").winning)
            self.assertTrue(engine.evaluate(mate, "w").winning)
        with self.engine("mate-zero") as engine:
            with self.assertRaises(ValueError):
                engine.evaluate(Position.from_fen(STARTING_FEN), "w")

    def test_terminal_draw_and_mate_are_not_fake_centipawns(self):
        with self.engine() as engine:
            draw = Position.from_fen("7k/8/8/8/8/8/8/K7 w - - 0 1")
            self.assertEqual(engine(draw, "b"), 0)
            self.assertEqual(engine.continuation(draw), ())
            mate = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
            with self.assertRaises(ValueError):
                engine(mate, "b")


if __name__ == "__main__":
    unittest.main()
