import gzip
import io
import tempfile
import unittest
import pathlib

try:
    import chess
except ImportError:  # optional dependency
    chess = None

if chess is not None:
    from trickfish.lichess_db import LocalExplorer, extract, movetext_sans
    from trickfish.trappack import TrapFinder


PGN = """[Event "Rated Blitz game"]
[Result "1-0"]
[WhiteElo "1300"]
[BlackElo "1350"]

1. e4 { [%clk 0:05:00] } 1... e5 { [%clk 0:05:00] } 2. Nf3 2... Nc6 3. Bc4 3... Nd4?! 4. Nxe5 1-0

[Event "Rated Bullet game"]
[Result "0-1"]
[WhiteElo "1300"]
[BlackElo "1350"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4 4. Nxe5 Qg5 0-1

[Event "Rated Rapid game"]
[Result "0-1"]
[WhiteElo "1900"]
[BlackElo "1350"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 0-1
"""


@unittest.skipIf(chess is None, "python-chess not installed")
class LichessExtractTests(unittest.TestCase):
    def test_movetext_strips_clocks_numbers_and_annotations(self):
        self.assertEqual(movetext_sans("1. e4 { [%clk 0:05:00] } 1... e5 2. Nf3?! Nc6 1-0", 10),
                         ["e4", "e5", "Nf3", "Nc6"])
        self.assertEqual(movetext_sans("1. e4 e5 2. Nf3 Nc6", 3), ["e4", "e5", "Nf3"])

    def test_extract_keeps_only_rated_non_bullet_games_inside_band(self):
        output = io.StringIO()
        kept, seen = extract(io.StringIO(PGN), output, 1200, 1599, 30)
        self.assertEqual((kept, seen), (1, 3))
        self.assertEqual(output.getvalue(), "w\t1325\te4 e5 Nf3 Nc6 Bc4 Nd4 Nxe5\n")

    def test_local_explorer_counts_children_and_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "games.tsv.gz"
            with gzip.open(path, "wt") as handle:
                handle.write("w\t1300\te4 e5 Nf3 Nc6 Bc4 Nd4 Nxe5\n")
                handle.write("b\t1300\te4 e5 Nf3 Nc6 Bc4 Bc5 c3\n")
                handle.write("d\t1300\td4 d5 c4 e6 Nc3 Nf6\n")
            explorer = LocalExplorer(path, "e4 e5 Nf3 Nc6 Bc4".split())
            self.assertEqual(explorer.games, 2)
            board = chess.Board()
            for san in "e4 e5 Nf3 Nc6 Bc4".split():
                board.push_san(san)
            node = explorer(board)
            self.assertEqual((node["white"], node["draws"], node["black"]), (1, 0, 1))
            self.assertEqual({move["san"] for move in node["moves"]}, {"Nd4", "Bc5"})
            self.assertEqual({move["uci"] for move in node["moves"]}, {"c6d4", "f8c5"})


class FakeEvaluator:
    depth = 10

    def __init__(self, scores):
        self.scores = scores

    def analyse(self, board, depth=None):
        legal = list(board.legal_moves)
        return {"white_cp": self.scores.get(board.epd(), 0), "pv": [legal[0].uci()] if legal else []}

    def cp(self, board, color):
        value = self.scores.get(board.epd(), 0)
        return value if color == chess.WHITE else -value


@unittest.skipIf(chess is None, "python-chess not installed")
class TrapFinderTests(unittest.TestCase):
    def test_records_position_where_frequent_reply_loses(self):
        root = chess.Board()
        for san in "e4 e5 Nf3 Nc6 Bc4".split():
            root.push_san(san)
        blunder = root.copy()
        blunder.push_san("Nd4")
        blunder.push_san("Nxe5")
        after_blunder = root.copy()
        after_blunder.push_san("Nd4")
        sound = root.copy()
        sound.push_san("Bc5")
        scores = {after_blunder.epd(): 400, sound.epd(): 20, root.epd(): 20}

        def explorer(board):
            if board.epd() == root.epd():
                return {"white": 600, "draws": 100, "black": 300,
                        "moves": [{"san": "Bc5", "uci": "f8c5", "white": 300, "draws": 60, "black": 240},
                                  {"san": "Nd4", "uci": "c6d4", "white": 300, "draws": 40, "black": 60}]}
            return {"white": 0, "draws": 0, "black": 0, "moves": []}

        finder = TrapFinder(explorer, FakeEvaluator(scores), chess.WHITE, log=lambda *_: None)
        traps = finder.run(root)
        self.assertEqual(len(traps), 1)
        trap = traps[0]
        self.assertEqual(trap.games, 1000)
        self.assertAlmostEqual(trap.error_share, 0.4)
        mistake = next(reply for reply in trap.replies if reply.san == "Nd4")
        self.assertEqual(mistake.gain_cp, 380)
        self.assertAlmostEqual(mistake.our_score, 0.8)
        self.assertEqual(trap.punish["after"], "Nd4")

    def test_ignores_rare_mistakes(self):
        root = chess.Board()
        root.push_san("e4")
        after = root.copy()
        after.push_san("f6")
        scores = {after.epd(): 500}

        def explorer(board):
            if board.epd() == root.epd():
                return {"white": 900, "draws": 50, "black": 50,
                        "moves": [{"san": "e5", "uci": "e7e5", "white": 850, "draws": 40, "black": 30},
                                  {"san": "f6", "uci": "f7f6", "white": 50, "draws": 10, "black": 20}]}
            return {"white": 0, "draws": 0, "black": 0, "moves": []}

        finder = TrapFinder(explorer, FakeEvaluator(scores), chess.WHITE, log=lambda *_: None)
        self.assertEqual(finder.run(root), [])


if __name__ == "__main__":
    unittest.main()
