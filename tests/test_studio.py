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


    def test_pdf_mode_writes_a_text_pdf_and_pgn_from_notes(self):
        from trickfish import studio

        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            rec = record()
            key = " ".join(rec["moves"])
            (directory / "traps.json").write_text(json.dumps({"color": "white", "band": "1200-1599",
                                                              "sample_games": 902003, "engine": "Stockfish 16",
                                                              "traps": [rec]}))
            (directory / "notes.json").write_text(json.dumps({
                "_order": [key],
                "_meta": {"slug": "test-pack", "title": "Test Pack Title", "subtitle": "A subtitle from notes",
                          "tagline": "A tagline from notes", "method": ["Method paragraph from notes."],
                          "usage": ["Usage step from notes."], "fineprint": ["Fine print from notes."],
                          "drills_intro": "Drills intro from notes."},
                key: {"name": "Bishop's Opening: the queen on h5", "idea": "Idea text from notes.",
                      "defence": "Defence text from notes.", "plain": "4.Qxe5+ forks the king and the rook."}}))
            studio.main([str(directory / "traps.json"), "--notes", str(directory / "notes.json"),
                         "--output", str(directory / "out"), "--only", "pdf"])
            pdf = directory / "out" / "pdf" / "test-pack.pdf"
            self.assertTrue(pdf.exists())
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
            self.assertIn("Test Pack Title", (directory / "out" / "pdf" / "test-pack.pgn").read_text())
            if shutil.which("pdftotext"):
                text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
                for phrase in ("Test Pack Title", "Method paragraph from notes.", "Usage step from notes.",
                               "Fine print from notes.", "Drills intro from notes.", "Idea text from notes.",
                               "Defence text from notes.", "A tagline from notes", "1,572"):
                    self.assertIn(phrase, text)
            if shutil.which("pdfimages"):
                images = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True).stdout
                self.assertEqual(len(images.strip().splitlines()), 2)   # header only: diagrams are vector

    def test_sampler_mode_keeps_original_numbers_and_adds_closing_page(self):
        from trickfish import studio

        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            rec = record()
            key = " ".join(rec["moves"])
            other = dict(rec, moves=rec["moves"][:4] + ["d8f6"])   # a second, distinct key
            okey = " ".join(other["moves"])
            (directory / "traps.json").write_text(json.dumps({"color": "white", "band": "1200-1599",
                                                              "sample_games": 902003, "engine": "Stockfish 16",
                                                              "traps": [other, rec]}))
            (directory / "notes.json").write_text(json.dumps({
                "_order": [okey, key],
                "_meta": {"title": "Full", "method": ["m"], "usage": ["u"], "fineprint": ["f"]},
                okey: {"name": "Elsewhere: left out trap"},
                key: {"name": "Bishop's Opening: the queen on h5", "plain": "Plain text."}}))
            (directory / "sampler.json").write_text(json.dumps({
                "traps": [2], "_meta": {"slug": "free", "title": "Free Sampler Title", "cta": "CTA paragraph.",
                                        "price": "USD 14", "url": "https://example.com/pack"}}))
            studio.main([str(directory / "traps.json"), "--notes", str(directory / "notes.json"),
                         "--sampler", str(directory / "sampler.json"),
                         "--output", str(directory / "out"), "--only", "pdf"])
            pdf = directory / "out" / "pdf" / "free.pdf"
            self.assertTrue(pdf.exists())
            if shutil.which("pdftotext"):
                text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
                for phrase in ("Free Sampler Title", "Trap 02 / 2", "The other 1", "Elsewhere: left out trap",
                               "CTA paragraph.", "https://example.com/pack"):
                    self.assertIn(phrase, text)
                self.assertNotIn("The traps at a glance", text)
            self.assertIn("Trap 2", (directory / "out" / "pdf" / "free.pgn").read_text())
            self.assertNotIn("Trap 1\"", (directory / "out" / "pdf" / "free.pgn").read_text())

    @unittest.skipIf(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, "needs ffmpeg")
    def test_video_mode_writes_a_vertical_mp4(self):
        from trickfish import studio

        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            source = directory / "traps.json"
            source.write_text(json.dumps({"color": "white", "band": "1200-1599", "sample_games": 902003,
                                          "traps": [record()]}))
            studio.main([str(source), "--output", str(directory / "out"), "--only", "video", "--video-traps", "1"])
            video = directory / "out" / "video" / "trap-01.mp4"
            self.assertTrue(video.exists())
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height,pix_fmt,r_frame_rate:format=duration", "-of", "json", str(video)],
                                   capture_output=True, text=True, check=True)
            info = json.loads(probe.stdout)
            stream = info["streams"][0]
            self.assertEqual((stream["width"], stream["height"], stream["pix_fmt"]), (1080, 1920, "yuv420p"))
            self.assertEqual(stream["r_frame_rate"], "30/1")
            self.assertTrue(14 <= float(info["format"]["duration"]) <= 22)


if __name__ == "__main__":
    unittest.main()
