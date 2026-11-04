import math
import types
import unittest
from unittest.mock import Mock, patch

from trickfish.maia_reply import MaiaReplyModel, normalize_maia_replies
from trickfish.position import Position, STARTING_FEN


class MaiaReplyTests(unittest.TestCase):
    def test_rounding_mass_is_corrected_and_recorded_without_losing_zeroes(self):
        probabilities, mass = normalize_maia_replies({"a": 0.3333, "b": 0.6666, "c": 0.0}, {"a", "b", "c"})
        self.assertAlmostEqual(mass, 0.9999)
        self.assertTrue(math.isclose(math.fsum(probabilities.values()), 1.0))
        self.assertEqual(probabilities["c"], 0)

    def test_bad_coverage_and_non_rounding_mass_fail(self):
        for raw in ({"a": 1}, {"a": 0.2, "b": 0.2}, {"a": float("nan"), "b": 0},
                    {"a": -0.1, "b": 1.1}, {"a": True, "b": 0}, {"a": 0, "b": 0}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                normalize_maia_replies(raw, {"a", "b"})

    def test_predicting_black_uses_opponent_rating_as_active_and_original_player_as_other(self):
        position = Position.from_fen(STARTING_FEN.replace(" w ", " b "))
        legal = {move.to_uci(): 0.05 for move in position.legal_moves()}
        inference = types.SimpleNamespace(prepare=Mock(return_value="prepared"),
                                          inference_each=Mock(return_value=(legal, 0.7)))
        model = types.SimpleNamespace(from_pretrained=Mock(return_value="network"))
        module = types.SimpleNamespace(inference=inference, model=model)
        with patch.dict("sys.modules", {"maia2": module}), \
             patch("importlib.metadata.version", return_value="0.11.0"), \
             patch("pathlib.Path.read_bytes", return_value=b"synthetic checkpoint"):
            adapter = MaiaReplyModel("rapid", "cache", 1800)
        probabilities = adapter(position, 1400)
        self.assertEqual(set(probabilities), set(legal))
        inference.inference_each.assert_called_once_with("network", "prepared", position.to_fen(), 1400, 1800)
        probabilities.clear()
        self.assertEqual(len(adapter(position, 1400)), 20)
        self.assertEqual(len(adapter.provenance()["positions"]), 1)
        self.assertEqual(adapter.provenance()["positions"][0]["active_rating"], 1400)


if __name__ == "__main__":
    unittest.main()
