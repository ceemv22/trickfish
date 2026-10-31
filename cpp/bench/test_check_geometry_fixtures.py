import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
from check_geometry_parity import fixtures, expected_checks, parse_checks
from trickfish.position import Position


class CheckGeometryFixtureTests(unittest.TestCase):
    def test_fixture_domains_and_reference_special_cases(self):
        positions = fixtures()
        self.assertGreaterEqual(len(positions), 200)
        self.assertEqual(len({position.to_fen() for position in positions}), len(positions))
        values = [expected_checks(position) for position in positions]
        for field in ("white_check", "black_check"):
            self.assertTrue(any(value[field] for value in values))
            self.assertTrue(any(not value[field] for value in values))
        mate = Position.from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        self.assertEqual(expected_checks(mate), {"white_check": False, "black_check": True})
        exposed = Position.from_fen("4k3/8/5P2/r6K/8/8/8/8 w - - 0 1")
        self.assertTrue(expected_checks(exposed)["white_check"])

    def test_diagnostic_parser_rejects_ambiguous_or_missing_data(self):
        self.assertEqual(parse_checks("white_check true\nblack_check false\n"), {"white_check": True, "black_check": False})
        for output in ("white_check true", "white_check true\nwhite_check false\nblack_check false",
                "white_check 1\nblack_check false", "white_check false\nblack_check false\nextra true"):
            with self.assertRaises(ValueError): parse_checks(output)


if __name__ == "__main__":
    unittest.main()
