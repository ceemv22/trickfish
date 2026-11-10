import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

try:
    import chess
    from PIL import Image
except ImportError:  # optional dependencies
    chess = None


def playwright_available():
    if shutil.which("node") is None:
        return False
    return subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode == 0



def record():
    board = chess.Board()
    moves = []
    for san in "e4 e5 Bc4 Bc5 Qh5".split():
        move = board.parse_san(san)
        moves.append(move.uci())
        board.push(move)
    return {"moves": moves, "fen": board.fen(), "games": 1572, "best_cp": -18, "best_reply_san": "Qe7",
            "error_share": 0.2, "expected_gain_cp": 128, "score": 408, "maia_error": None,
            "replies": [{"san": "g6", "uci": "g7g6", "games": 157, "share": 0.1, "our_cp": 672,
                         "gain_cp": 690, "our_score": 0.85, "maia": None},
                        {"san": "Qe7", "uci": "d8e7", "games": 900, "share": 0.57, "our_cp": -18,
                         "gain_cp": 0, "our_score": 0.5, "maia": None}],
            "punish": {"after": "g6", "line": ["Qxe5+", "Qe7", "Qxh8"], "uci": ["h5e5", "d8e7", "e5h8"],
                       "our_cp": 672}}


@unittest.skipIf(chess is None or not playwright_available(), "studio needs python-chess, node and playwright")
class StudioTests(unittest.TestCase):
    def test_question_and_answer_frames_render_at_2x(self):
        from trickfish import studio
        from trickfish.trappack_render import load

        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            source = directory / "traps.json"
            source.write_text(json.dumps({"color": "white", "band": "1200-1599", "sample_games": 902003,
                                          "traps": [record()]}))
            data, meta, traps = load(source)
            studio.render([(studio.question(data, traps[0], 1), directory / "q.png", 1080, 1350),
                           (studio.answer(data, traps[0], 1), directory / "a.png", 1080, 1350)])
            self.assertEqual(Image.open(directory / "q.png").size, (2160, 2700))
            self.assertEqual(Image.open(directory / "a.png").size, (2160, 2700))

    def test_markup_uses_typographic_ellipsis_and_real_numbers(self):
        from trickfish import studio
        from trickfish.trappack_render import Trap

        trap = Trap(record(), "white", 1)
        data = {"color": "white", "band": "1200-1599"}
        self.assertIn("20<span", studio.question(data, trap, 1))
        markup = studio.answer(data, trap, 1)
        self.assertIn("3…g6", markup)
        self.assertIn("85%", markup)


if __name__ == "__main__":
    unittest.main()
