import json
import pathlib
import unittest
from unittest.mock import patch

from trickfish.position import Position, STARTING_FEN
from trickfish.practical_cli import RecordedReplyModel


class RecordedReplyTests(unittest.TestCase):
    def load(self, data):
        with patch.object(pathlib.Path, "read_bytes", return_value=json.dumps(data).encode()):
            return RecordedReplyModel("replies.json", 1500)

    def test_rating_position_and_provenance_are_bound_to_supplied_bytes(self):
        data = {"schema": "trickfish.reply-distributions.v1", "rating": 1500,
                "source": "synthetic fixture", "positions": {STARTING_FEN: {"e2e4": 1}}}
        model = self.load(data)
        self.assertEqual(model(Position.from_fen(STARTING_FEN), 1500), {"e2e4": 1})
        receipt = model.provenance()
        self.assertEqual(receipt["positions"], data["positions"])
        self.assertEqual(len(receipt["sha256"]), 64)
        with self.assertRaises(ValueError):
            model(Position.from_fen(STARTING_FEN), 1600)
        with self.assertRaises(ValueError):
            model(Position.from_fen(STARTING_FEN.replace(" w ", " b ")), 1500)

    def test_rejects_wrong_schema_rating_and_missing_source(self):
        valid = {"schema": "trickfish.reply-distributions.v1", "rating": 1500,
                 "source": "fixture", "positions": {}}
        for data in ([], {**valid, "schema": "unknown"}, {**valid, "rating": 1400},
                     {**valid, "source": ""}, {**valid, "positions": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)


if __name__ == "__main__":
    unittest.main()
