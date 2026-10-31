import pathlib
import queue
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from uci_matches import Engine, primary_information


def receive(lines):
    engine = Engine("synthetic queue fixture", 1)
    for line in lines: engine.events.put(line)
    return engine.until("bestmove")


class MultiPVInformationTests(unittest.TestCase):
    def test_match_client_keeps_rank_one_information(self):
        primary = "info depth 2 multipv 1 score cp 30 pv e2e4"
        line, information = receive(["info depth 1 multipv 1 score cp 0 pv b1c3", "info depth 1 multipv 2 score cp -10 pv d2d4",
            primary, "info depth 2 multipv 2 score cp 20 pv d2d4",
            "info depth 2 multipv 3 score cp 10 pv b1c3", "bestmove e2e4"])
        self.assertEqual(line, "bestmove e2e4")
        self.assertEqual(information, primary)
        _, information = receive(["info depth 1 multipv 2 score cp 20 pv d2d4", "bestmove e2e4"])
        self.assertIsNone(information)

    def test_single_pv_updates_and_numeric_rank_one_remain_supported(self):
        latest = "info depth 2 score cp 10 pv e2e4"
        _, information = receive(["info depth 1 score cp 0 pv d2d4", latest, "bestmove e2e4"])
        self.assertEqual(information, latest)
        self.assertTrue(primary_information("info depth 1 multipv 01 score cp 0 pv e2e4"))
        self.assertTrue(primary_information("info string multipv analysis is enabled"))
        self.assertFalse(primary_information("info depth 1 multipv 256 score cp 0 pv e2e4"))

    def test_malformed_ranks_abort_instead_of_misattributing_information(self):
        for text in ("info multipv", "info multipv 0", "info multipv -1", "info multipv true", "info multipv 1 multipv 2"):
            with self.subTest(text=text), self.assertRaisesRegex(RuntimeError, "multipv rank"):
                receive([text, "bestmove e2e4"])


if __name__ == "__main__":
    unittest.main()
