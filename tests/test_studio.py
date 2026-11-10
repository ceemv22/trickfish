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
        data = {"color": "white", "band": "1200-1599", "title": "1.e4 e5 Traps for White"}
        question = studio.question(data, trap, 1)
        self.assertIn(">10<", question)               # 157 of 1,572 games chose a losing reply that paid off for White
        self.assertIn("1,572 games", question)        # sample size in the main sentence
        self.assertIn("go wrong here", question)
        self.assertNotIn("bite", question)
        self.assertNotIn("g6?", question)             # the question card never gives the answer away
        markup = studio.answer(data, trap, 1)
        self.assertIn("3\u2026g6?", markup)            # typographic ellipsis, annotated mistake
        self.assertIn(">85<", markup)                 # White's real score after 3...g6
        self.assertIn("10% of 1,572 games", markup)   # the revealed move's own share
        self.assertIn("Best defence", markup)
        self.assertIn("1200\u20131599", markup)        # source line on every card
        self.assertIn(studio.TAGLINE.split(". ")[1], studio.banner(data, [trap]))

    def test_small_samples_are_shown_as_counts(self):
        from trickfish import studio
        from trickfish.trappack_render import Trap

        small = record()
        small["replies"][0]["games"] = 40
        trap = Trap(small, "white", 1)
        markup = studio.answer({"color": "white", "band": "1200-1599"}, trap, 1)
        self.assertIn(">34<", markup)                 # 0.85 x 40 games = 34 points
        self.assertIn("34 points<br>from 40 games", markup)
        self.assertNotIn("/40", markup)               # n is in the sentence, not under the hero
        self.assertEqual(studio.points(0.5, 3), "1\u00bd")

    def test_hero_share_leaves_out_mistakes_that_did_not_pay(self):
        from trickfish import studio
        from trickfish.trappack_render import Trap

        rec = record()
        rec["replies"].append({"san": "Nf6", "uci": "g8f6", "games": 300, "share": 0.19, "our_cp": 900,
                               "gain_cp": 900, "our_score": 0.4, "maia": None})
        trap = Trap(rec, "white", 1)
        self.assertAlmostEqual(studio.wrong_share(trap), 157 / 1572)

    def test_route_typefaces_only(self):
        from trickfish import studio
        from trickfish.trappack_render import Trap

        trap = Trap(record(), "white", 1)
        data = {"color": "white", "band": "1200-1599"}
        for markup in (studio.question(data, trap, 1), studio.answer(data, trap, 1), studio.profile()):
            self.assertNotIn("Inter", markup)
            self.assertNotIn("gradient", markup.lower())
            self.assertNotIn("box-shadow", markup)
            for family in ("young-serif", "schibsted-grotesk", "martian-mono"):
                self.assertIn(family, markup)
        for path in studio.FONTS.glob("*/*.woff2"):
            self.assertTrue((path.parent / "OFL.txt").exists())
        note = studio.prose("Only 7...Ke6 holds the d5 knight.")
        self.assertIn("white-space:nowrap\">7\u2026", note)  # move number kept with its move
        self.assertEqual(note.count('class="mono"'), 1)    # the bare square d5 stays in the text face

    def test_answer_draws_the_line_and_hook_in_red_only(self):
        from trickfish import studio
        from trickfish.trappack_render import Trap

        trap = Trap(record(), "white", 1)
        strokes, hook, plies = studio.catch(trap)
        self.assertEqual(strokes[0][0][0], chess.H5)  # automatic fallback: the queen's route ...
        self.assertEqual(hook, chess.H8)              # ... ending on the rook it wins
        board = studio.board_svg(trap.after, 90, catch_=(strokes, hook))
        self.assertIn(studio.HOOK, board)
        self.assertNotIn(studio.HOOK, studio.board_svg(trap.board, 90))

    def test_hero_superscript_is_one_lockup(self):
        from trickfish import studio

        hero = studio.big_number("64%")
        self.assertIn(">64<", hero)
        self.assertIn("font-size:%dpx" % round(studio.L * studio.SUPER), hero)
        self.assertIn(">\u00bd<", studio.big_number("19\u00bd"))
        self.assertNotIn("<span class=\"num\" style=\"font-size:%dpx" % round(studio.L * studio.SUPER), studio.big_number("47"))

    def test_every_hook_in_the_pack_is_on_a_piece(self):
        from trickfish import studio
        from trickfish.trappack_render import load

        root = pathlib.Path(__file__).resolve().parents[1] / "packs" / "e4e5-white-1200"
        if not (root / "traps.json").exists():
            self.skipTest("pack data not present")
        data, meta, traps = load(root / "traps.json", root / "notes.json")
        listed = 0
        for trap in traps:
            if trap.line_text() in studio.CATCH:
                listed += 1
                strokes, hook, plies = studio.catch(trap)
                self.assertIsNotNone(trap.after.piece_at(hook), trap.name)
                self.assertTrue(1 <= plies <= len(trap.punish), trap.name)
        self.assertEqual(listed, len(traps))


if __name__ == "__main__":
    unittest.main()
