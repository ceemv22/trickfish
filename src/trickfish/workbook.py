import argparse
from dataclasses import dataclass
from hashlib import sha256
import io
import json
import pathlib
from uuid import uuid4
import shutil

import chess
import chess.pgn


DEFAULT_PROMPT = "Choose a move and explain your plan. What reply should you check?"


@dataclass(frozen=True)
class Entry:
    number: int
    label: str
    fen: str
    comment: str
    continuation: str


@dataclass(frozen=True)
class Workbook:
    digest: str
    entries: tuple[Entry, ...]


def load_pgn(path):
    raw = pathlib.Path(path).read_bytes()
    if len(raw) > 5_000_000:
        raise ValueError("PGN exceeds the 5 MB limit")
    stream = io.StringIO(raw.decode("utf-8-sig"))
    entries = []
    game_number = 0
    while (game := chess.pgn.read_game(stream)) is not None:
        game_number += 1
        if game.errors:
            raise ValueError(f"Game {game_number}: illegal or malformed PGN")
        board = game.board()
        if not board.is_valid():
            raise ValueError(f"Game {game_number}: invalid starting position")
        stack = [(game, board, "main")]
        while stack:
            node, board, branch = stack.pop()
            if len(entries) >= 2000:
                raise ValueError("PGN exceeds the 2000 position limit")
            line = []
            next_node = node
            for _ in range(8):
                if not next_node.variations:
                    break
                next_node = next_node.variations[0]
                line.append(next_node.move)
            continuation = board.variation_san(line) if line else "No continuation supplied."
            move_number = f"{board.fullmove_number}{'.' if board.turn else '...'}"
            label = f"Game {game_number} / {branch} / {move_number} / {'White' if board.turn else 'Black'} to move"
            entries.append(Entry(len(entries) + 1, label, board.fen(), node.comment, continuation))
            for index in range(len(node.variations) - 1, -1, -1):
                child = node.variations[index]
                if child.move not in board.legal_moves:
                    raise ValueError(f"Game {game_number}: illegal variation")
                successor = board.copy()
                successor.push(child.move)
                stack.append((child, successor, branch + f".{index + 1}"))
    if not entries:
        raise ValueError("No games found in PGN")
    return Workbook(sha256(raw).hexdigest(), tuple(entries))


def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab

    options = [pathlib.Path("C:/Windows/Fonts/seguisym.ttf"),
               pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
               pathlib.Path("/System/Library/Fonts/Apple Symbols.ttf")]
    font = next((path for path in options if path.exists()), None)
    if font is None:
        raise ValueError("Chess font unavailable. Install DejaVu Sans or use Windows Segoe UI Symbol.")
    pdfmetrics.registerFont(TTFont("WorkbookChess", str(font)))
    text_font = pathlib.Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    pdfmetrics.registerFont(TTFont("WorkbookText", str(text_font)))


def draw_board(canvas, fen, x, y, size=256):
    board = chess.Board(fen)
    square_size = size / 8
    for rank in range(8):
        for file in range(8):
            square = chess.square(file, rank)
            canvas.setFillColorRGB(*( (0.91, 0.93, 0.94) if (file + rank) % 2 else (0.40, 0.51, 0.56)))
            canvas.rect(x + file * square_size, y + rank * square_size, square_size, square_size, fill=1, stroke=0)
            piece = board.piece_at(square)
            if piece:
                canvas.setFillColorRGB(0.04, 0.06, 0.08)
                canvas.setFont("WorkbookChess", square_size * 0.83)
                canvas.drawCentredString(x + (file + 0.5) * square_size, y + rank * square_size + square_size * 0.18, piece.unicode_symbol())
    canvas.setFont("WorkbookText", 9)
    canvas.setFillColorRGB(0.18, 0.24, 0.29)
    for index in range(8):
        canvas.drawCentredString(x + (index + 0.5) * square_size, y - 13, "abcdefgh"[index])
        canvas.drawRightString(x - 7, y + (index + 0.40) * square_size, str(index + 1))


def _paragraph(canvas, text, x, y, width, height, limit=4000):
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from xml.sax.saxutils import escape

    if len(text) > limit:
        raise ValueError("Text is too long for a worksheet page; shorten it before export")
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), ParagraphStyle("body", fontName="WorkbookText", fontSize=10, leading=15))
    _, actual_height = paragraph.wrap(width, height)
    if actual_height > height:
        raise ValueError("Text does not fit the PDF page; shorten the comment or prompt")
    paragraph.drawOn(canvas, x, y - actual_height)


def _pdf(path, entries, title, prompt, answers):
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.pagesizes import A4

    canvas = pdfcanvas.Canvas(str(path), pagesize=A4)
    canvas.setTitle(title + (" - coach key" if answers else " - student worksheet"))
    for index, entry in enumerate(entries, 1):
        canvas.setFillColorRGB(0.10, 0.18, 0.24)
        canvas.setFont("WorkbookText", 11)
        canvas.drawString(44, 803, "TRICKFISH  /  PGN WORKBOOK")
        _paragraph(canvas, title, 44, 780, 507, 45, 120)
        canvas.setFont("WorkbookText", 10)
        canvas.drawString(44, 719, f"{'Coach key' if answers else 'Student worksheet'}  /  Position {index}")
        _paragraph(canvas, entry.label, 44, 701, 507, 32)
        draw_board(canvas, entry.fen, 170, 390)
        if answers:
            _paragraph(canvas, "Supplied continuation (first 8 plies):\n" + entry.continuation, 44, 354, 507, 75)
            _paragraph(canvas, "Author comment at this position:\n" + (entry.comment or "No comment supplied."), 44, 265, 507, 170)
        else:
            question = prompt
            if prompt == DEFAULT_PROMPT and not any(chess.Board(entry.fen).legal_moves):
                question = "Assess this position. Does the side to move have a legal move? Is its king in check? Explain your conclusion."
            _paragraph(canvas, question, 44, 354, 507, 90, 600)
            canvas.setStrokeColorRGB(0.70, 0.75, 0.78)
            for y in (225, 193, 161, 129):
                canvas.line(44, y, 551, y)
        canvas.setFillColorRGB(0.30, 0.35, 0.39)
        canvas.setFont("WorkbookText", 8)
        canvas.drawString(44, 63, "Source lines are author material, not engine-certified answers.")
        canvas.drawString(44, 49, "Comments and continuations are hidden in the student PDF.")
        canvas.drawRightString(551, 49, f"{index} / {len(entries)}")
        canvas.showPage()
    canvas.save()


def export_workbook(book, numbers, output, title="Chess workbook", prompt=DEFAULT_PROMPT):
    numbers = list(numbers)
    if not numbers or len(numbers) != len(set(numbers)) or len(numbers) > 50:
        raise ValueError("Select 1 to 50 distinct positions")
    if any(type(n) is not int or n < 1 or n > len(book.entries) for n in numbers):
        raise ValueError("Unknown position number")
    if not title.strip() or not prompt.strip():
        raise ValueError("Title and prompt must not be empty")
    entries = [book.entries[n - 1] for n in numbers]
    output = pathlib.Path(output)
    if output.exists():
        raise ValueError("Output folder already exists; choose a new folder")
    _fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / (".workbook-" + uuid4().hex)
    temporary.mkdir()
    try:
        _pdf(temporary / "student.pdf", entries, title, prompt, False)
        _pdf(temporary / "coach.pdf", entries, title, prompt, True)
        receipt = {"schema": "trickfish.workbook.v1", "source_sha256": book.digest,
                   "positions": [{"number": e.number, "fen": e.fen} for e in entries],
                   "answer_policy": "supplied main continuation, at most 8 plies; not engine-certified",
                   "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in temporary.iterdir()}}
        (temporary / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return output


def main():
    parser = argparse.ArgumentParser(description="Create student and coach PDFs from supplied PGN lines")
    parser.add_argument("pgn")
    parser.add_argument("--positions", help="Comma-separated position numbers; omit to list positions")
    parser.add_argument("--output")
    parser.add_argument("--title", default="Chess workbook")
    args = parser.parse_args()
    try:
        book = load_pgn(args.pgn)
        if args.positions is None:
            for entry in book.entries:
                print(entry.number, entry.label)
        else:
            if not args.output:
                parser.error("--output is required for export")
            print(export_workbook(book, [int(n) for n in args.positions.split(",")], args.output, args.title))
    except (ValueError, OSError, UnicodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
