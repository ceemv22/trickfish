import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

try:
    from trickfish.workbook import export_workbook, load_pgn
    from pypdf import PdfReader
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "Install workbook dependencies and pypdf")
class WorkbookTests(unittest.TestCase):
    def load(self, text):
        with patch.object(pathlib.Path, "read_bytes", return_value=text.encode()):
            return load_pgn("input.pgn")

    def test_variation_and_black_move_roots(self):
        book = self.load('[Result "*"]\n\n1. e4 {SECRET_COACH_COMMENT} (1. d4 d5) e5 *')
        self.assertEqual(len(book.entries), 5)
        self.assertIn("1...", book.entries[1].label)
        self.assertIn("d5", book.entries[3].continuation)
        self.assertEqual(book.entries[3].fen.split()[1], "b")

    def test_illegal_tail_and_invalid_root_rejected(self):
        for text in ('1. e4 e5 2. Bh6 *', '[SetUp "1"]\n[FEN "8/8/8/8/8/8/8/8 w - - 0 1"]\n\n*', ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load(text)

    def test_special_moves_replayed(self):
        book = self.load('[SetUp "1"]\n[FEN "4k3/P7/8/3pP3/8/8/8/4K3 w - d6 0 1"]\n\n1. exd6 Kd7 2. a8=Q *')
        self.assertIn("Q", book.entries[-1].fen.split()[0])
        self.assertNotIn("p", book.entries[1].fen.split()[0])

    def test_export_hides_answers_and_hashes_files(self):
        book = self.load('1. e4 {SECRET_COACH_COMMENT} e5 2. Nf3 *')
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "new"
            export_workbook(book, [2], output)
            student = PdfReader(output / "student.pdf")
            coach = PdfReader(output / "coach.pdf")
            self.assertEqual(len(student.pages), 1)
            self.assertNotIn("SECRET_COACH_COMMENT", student.pages[0].extract_text())
            self.assertNotIn("1... e5", student.pages[0].extract_text())
            self.assertIn("SECRET_COACH_COMMENT", coach.pages[0].extract_text())
            self.assertIn("e5", coach.pages[0].extract_text())
            receipt = json.loads((output / "receipt.json").read_text())
            for name, digest in receipt["files"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(ValueError):
                export_workbook(book, [2], output)

    def test_failed_layout_leaves_no_partial_package(self):
        book = self.load('1. e4 {' + 'long comment ' * 1000 + '} *')
        with tempfile.TemporaryDirectory() as folder:
            output = pathlib.Path(folder) / "new"
            with self.assertRaises(ValueError):
                export_workbook(book, [2], output)
            self.assertFalse(output.exists())
            self.assertEqual(list(pathlib.Path(folder).iterdir()), [])

    def test_terminal_questions_and_custom_prompt_preservation(self):
        roots = ["r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
                 "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1"]
        with tempfile.TemporaryDirectory() as folder:
            for index, fen in enumerate(roots):
                book = self.load(f'[SetUp "1"]\n[FEN "{fen}"]\n\n*')
                output = pathlib.Path(folder) / str(index)
                export_workbook(book, [1], output)
                text = PdfReader(output / "student.pdf").pages[0].extract_text()
                self.assertIn("Assess this position.", text)
                self.assertNotIn("Choose a move", text)
                custom = pathlib.Path(folder) / (str(index) + "-custom")
                export_workbook(book, [1], custom, prompt="Discuss the last move.")
                text = PdfReader(custom / "student.pdf").pages[0].extract_text()
                self.assertIn("Discuss the last move.", text)
                self.assertNotIn("Assess this position.", text)
