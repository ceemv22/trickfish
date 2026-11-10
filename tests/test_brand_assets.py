import json
import pathlib
import tempfile
import unittest

try:
    import cairosvg  # noqa: F401
    import chess
    from PIL import Image
except ImportError:  # optional dependencies
    chess = None


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


@unittest.skipIf(chess is None, "brand dependencies not installed")
class BrandAssetTests(unittest.TestCase):
    def test_cards_and_store_images_render_at_expected_sizes(self):
        from trickfish import brand_assets
        from trickfish.trappack_render import load

        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            source = directory / "traps.json"
            source.write_text(json.dumps({"color": "white", "band": "1200-1599", "sample_games": 902003,
                                          "traps": [record()]}))
            data, meta, traps = load(source)
            brand_assets.question_card(data, traps[0], directory / "q.png")
            brand_assets.answer_card(data, traps[0], directory / "a.png")
            brand_assets.thumbnail(data, meta, traps, directory / "t.png")
            brand_assets.profile(directory / "p.png")
            self.assertEqual(Image.open(directory / "q.png").size, (1080, 1350))
            self.assertEqual(Image.open(directory / "a.png").size, (1080, 1350))
            self.assertEqual(Image.open(directory / "t.png").size, (1200, 1200))
            self.assertEqual(Image.open(directory / "p.png").size, (800, 800))


if __name__ == "__main__":
    unittest.main()
