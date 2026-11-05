import json
import pathlib
import unittest
from unittest.mock import patch

from trickfish.position import STARTING_FEN
from trickfish.repertoire import load_repertoire


class RepertoireTests(unittest.TestCase):
    def load(self, positions, **fields):
        data = {"schema": "trickfish.practical-cases.v1", "purpose": "synthetic fixture", "positions": positions, **fields}
        with patch.object(pathlib.Path, "read_bytes", return_value=json.dumps(data).encode()):
            return load_repertoire("fixture.json")

    def test_existing_manifest_retains_five_cases_and_initial_position(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "examples" / "practical-positions.json"
        result = load_repertoire(path)
        self.assertEqual(len(result.cases), 5)
        self.assertEqual(result.cases[0].position.to_fen(), STARTING_FEN)
        self.assertEqual(result.raw, path.read_bytes())

    def test_fen_root_and_en_passant_replay(self):
        result = self.load([{"name": "ep", "fen": "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "moves": ["e5d6"]}])
        self.assertEqual(result.cases[0].position.to_fen(), "4k3/8/3P4/8/8/8/8/4K3 b - - 0 1")

    def test_paths_reserved_names_duplicate_names_and_duplicate_positions_fail(self):
        for name in ("../escape", "x/y", "con", "aux", "COM1", "bad.name", "x" * 65):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.load([{"name": name, "moves": []}])
        for positions in ([{"name": "same", "moves": []}, {"name": "same", "moves": ["e2e4"]}],
                          [{"name": "first", "moves": []}, {"name": "second", "moves": []}]):
            with self.assertRaises(ValueError):
                self.load(positions)

    def test_illegal_move_and_nonmoving_king_check_fail(self):
        with self.assertRaises(ValueError):
            self.load([{"name": "illegal", "moves": ["e2e4", "e2e5"]}])
        with self.assertRaises(ValueError):
            self.load([{"name": "illegal-root", "fen": "7k/6Q1/6K1/8/8/8/8/8 w - - 0 1", "moves": []}])

    def test_empty_unknown_and_mistyped_input_fields_fail(self):
        for positions in ([], [{"name": "x", "moves": "e2e4"}], [{"name": "x", "moves": [], "ignored": True}]):
            with self.subTest(positions=positions), self.assertRaises(ValueError):
                self.load(positions)
        with self.assertRaises(ValueError):
            self.load([{"name": "x", "moves": []}], schema="unknown")

    def test_duplicate_json_keys_fail(self):
        raw = b'{"schema":"trickfish.practical-cases.v1","purpose":"x","positions":[],"positions":[]}'
        with patch.object(pathlib.Path, "read_bytes", return_value=raw), self.assertRaises(ValueError):
            load_repertoire("fixture.json")


if __name__ == "__main__":
    unittest.main()
