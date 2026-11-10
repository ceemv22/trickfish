"""Render a trap-pack JSON (from :mod:`trickfish.trappack`) into sellable files.

Outputs a PDF guide with drills and an answer key, a PGN for import into any
chess app, and square PNG cards suitable for social posts.
"""

import argparse
import io
import json
import pathlib
import textwrap

import chess
import chess.pgn
import chess.svg

NAVY = "#1b2a47"
SLATE = "#5f7a8f"
CORAL = "#e4572e"
LIGHT_SQ = "#e9eef3"
DARK_SQ = "#8aa1b4"
LOGO = pathlib.Path(__file__).resolve().parents[2] / "assets" / "trickfish-logo.png"


def board_png(board, size=720, lastmove=None, arrows=(), flipped=False):
    import cairosvg

    svg = chess.svg.board(board, size=size, lastmove=lastmove, arrows=list(arrows), flipped=flipped,
                          coordinates=True,
                          colors={"square light": LIGHT_SQ, "square dark": DARK_SQ,
                                  "square light lastmove": "#f3d9a4", "square dark lastmove": "#d9b56e",
                                  "margin": NAVY, "coord": "#dfe6ec"})
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"))


def numbered(sans, start_ply=0):
    parts = []
    for offset, san in enumerate(sans):
        ply = start_ply + offset
        if ply % 2 == 0:
            parts.append("%d.%s" % (ply // 2 + 1, san))
        elif offset == 0:
            parts.append("%d...%s" % (ply // 2 + 1, san))
        else:
            parts.append(san)
    return " ".join(parts)


def line_sans(ucis):
    board = chess.Board()
    sans = []
    for uci in ucis:
        move = chess.Move.from_uci(uci)
        sans.append(board.san(move))
        board.push(move)
    return sans, board


def pawns(cp):
    if abs(cp) >= 1500:
        return "mating" if cp > 0 else "getting mated"
    return "%+.1f" % (cp / 100)


class Trap:
    """Convenience view over one trap record."""

    def __init__(self, record, color, number, note=None):
        self.record = record
        self.number = number
        self.color = chess.WHITE if color == "white" else chess.BLACK
        self.sans, self.board = line_sans(record["moves"])
        replies = sorted(record["replies"], key=lambda reply: reply["games"], reverse=True)
        self.replies = replies
        self.mistakes = [reply for reply in replies if reply["gain_cp"] >= 120]
        self.top = max(self.mistakes, key=lambda reply: reply["share"])
        self.after = self.board.copy()
        self.after.push(chess.Move.from_uci(self.top["uci"]))
        self.punish = record["punish"]["line"]
        self.punish_uci = record["punish"]["uci"]
        note = note or {}
        self.name = note.get("name") or "The %s mistake" % self.top["san"]
        self.idea = note.get("idea", "")
        self.defence = note.get("defence", "")

    @property
    def ply(self):
        return len(self.sans)

    def line_text(self):
        return numbered(self.sans)

    def mistake_text(self):
        return numbered([self.top["san"]], self.ply)

    def punish_text(self):
        return numbered(self.punish, self.ply + 1)

    def best_text(self):
        return numbered([self.record["best_reply_san"]], self.ply) if self.record["best_reply_san"] else "-"


def load(path, notes_path=None):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    notes = json.loads(pathlib.Path(notes_path).read_text(encoding="utf-8")) if notes_path else {}
    selected = notes.get("_order") or [" ".join(trap["moves"]) for trap in data["traps"]]
    by_key = {" ".join(trap["moves"]): trap for trap in data["traps"]}
    traps = [Trap(by_key[key], data["color"], index + 1, notes.get(key))
             for index, key in enumerate(selected) if key in by_key]
    return data, notes.get("_meta", {}), traps


def write_pgn(data, traps, path, event):
    with open(path, "w", encoding="utf-8") as handle:
        for trap in traps:
            game = chess.pgn.Game()
            game.headers["Event"] = event
            game.headers["Site"] = "Trickfish trap pack"
            game.headers["White"] = "Trap %d" % trap.number
            game.headers["Black"] = trap.name
            game.headers["Result"] = "*"
            node = game
            for uci in trap.record["moves"]:
                node = node.add_variation(chess.Move.from_uci(uci))
            games = trap.record["games"]
            wrong = sum(r["games"] for r in trap.mistakes if r["our_score"] >= 0.5) / (games or 1)
            side = "White" if trap.color == chess.WHITE else "Black"
            mover = "Black" if trap.color == chess.WHITE else "White"
            node.comment = ("%s to move. Reached in %s Lichess games between %s players; %.0f%% went wrong here."
                            % (mover, format(games, ","), data.get("band", "").replace("-", "–"), wrong * 100))
            mistake = node.add_main_variation(chess.Move.from_uci(trap.top["uci"]))
            mistake.nags.add(chess.pgn.NAG_MISTAKE)
            if trap.top["games"] < 50:
                halves = round(trap.top["our_score"] * trap.top["games"] * 2)
                score = "%s scored %d%s points from %d games afterwards." % (
                    side, halves // 2, "½" if halves % 2 else "", trap.top["games"])
            else:
                score = "%s scored %.0f%% afterwards." % (side, trap.top["our_score"] * 100)
            mistake.comment = "Played in %.0f%% of games. %s" % (trap.top["share"] * 100, score)
            if trap.record["best_reply_san"]:
                best = node.add_variation(node.board().parse_san(trap.record["best_reply_san"]))
                best.comment = "Best defence (Stockfish %s)." % pawns(trap.record["best_cp"])
            cursor = mistake
            for uci in trap.punish_uci:
                move = chess.Move.from_uci(uci)
                if move not in cursor.board().legal_moves:
                    break
                cursor = cursor.add_main_variation(move)
            if trap.idea:
                mistake.comment += " " + trap.idea
            print(game, file=handle, end="\n\n")


def write_cards(data, meta, traps, directory):
    from PIL import Image, ImageDraw, ImageFont

    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    flipped = data["color"] == "black"
    for trap in traps:
        card = Image.new("RGB", (1080, 1350), NAVY)
        draw = ImageDraw.Draw(card)
        title = ImageFont.truetype(bold_path, 54)
        body = ImageFont.truetype(font_path, 34)
        small = ImageFont.truetype(font_path, 28)
        draw.text((60, 50), "%.0f%% of %s players" % (trap.record["error_share"] * 100, data.get("band", "")),
                  font=title, fill="white")
        draw.text((60, 120), "go wrong here. Do you?", font=title, fill=CORAL)
        png = board_png(trap.board, 860, lastmove=trap.board.peek(), flipped=flipped)
        board = Image.open(io.BytesIO(png)).convert("RGB").resize((860, 860))
        card.paste(board, (110, 215))
        lines = textwrap.wrap(trap.line_text(), 52)[:2]
        for row, text in enumerate(lines):
            draw.text((60, 1092 + row * 44), text, font=body, fill="white")
        draw.text((60, 1100 + 44 * len(lines)), "%s to move. %s games on Lichess." % (
            "Black" if trap.board.turn == chess.BLACK else "White", format(trap.record["games"], ",")),
                  font=small, fill="#c9d4de")
        draw.text((60, 1260), "trickfish - Stockfish finds the best move. We find the one they miss.",
                  font=ImageFont.truetype(font_path, 24), fill="#9fb2c3")
        card.save(directory / ("trap-%02d.png" % trap.number))
        answer = Image.new("RGB", (1080, 1350), NAVY)
        draw = ImageDraw.Draw(answer)
        draw.text((60, 50), "The trap: %s" % trap.mistake_text(), font=title, fill=CORAL)
        draw.text((60, 120), "Punish it: %s" % (trap.punish_text()[:40]), font=body, fill="white")
        end = trap.after.copy()
        for uci in trap.punish_uci[:5]:
            move = chess.Move.from_uci(uci)
            if move in end.legal_moves:
                end.push(move)
        png = board_png(end, 860, lastmove=end.peek() if end.move_stack else None, flipped=flipped)
        answer.paste(Image.open(io.BytesIO(png)).convert("RGB").resize((860, 860)), (110, 215))
        draw.text((60, 1100), "Your real score after %s: %.0f%%" % (trap.top["san"], trap.top["our_score"] * 100),
                  font=body, fill="white")
        draw.text((60, 1160), "Best defence: %s. Engine eval after the mistake: %s" % (
            trap.record["best_reply_san"], pawns(trap.top["our_cp"])), font=small, fill="#c9d4de")
        draw.text((60, 1260), "trickfish - Stockfish finds the best move. We find the one they miss.",
                  font=ImageFont.truetype(font_path, 24), fill="#9fb2c3")
        answer.save(directory / ("trap-%02d-answer.png" % trap.number))


def write_pdf(data, meta, traps, path):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    navy, slate, coral = colors.HexColor(NAVY), colors.HexColor(SLATE), colors.HexColor(CORAL)
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=26, leading=31, textColor=navy)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=navy, spaceAfter=4)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=colors.HexColor("#222b38"))
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11.5, textColor=slate)
    line = ParagraphStyle("line", fontName="Helvetica-Bold", fontSize=11.5, leading=16, textColor=navy)
    centre = ParagraphStyle("centre", parent=body, alignment=TA_CENTER)
    flipped = data["color"] == "black"
    side = "White" if data["color"] == "white" else "Black"
    band = data.get("band", "")
    sample = data.get("sample_games")
    title = meta.get("title", "Trap Pack")
    subtitle = meta.get("subtitle", "")

    def image(board, width, lastmove=None, arrows=()):
        return Image(io.BytesIO(board_png(board, 640, lastmove=lastmove, arrows=arrows, flipped=flipped)),
                     width=width, height=width)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(slate)
        canvas.drawString(18 * mm, 10 * mm, "Trickfish - %s" % title)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(document.page))
        canvas.restoreState()

    story = []
    if LOGO.exists():
        story += [Spacer(1, 18 * mm), Image(str(LOGO), width=70 * mm, height=70 * mm)]
    story += [Spacer(1, 8 * mm), Paragraph(title, ParagraphStyle("t", parent=h1, alignment=TA_CENTER, fontSize=30, leading=36)),
              Spacer(1, 4 * mm), Paragraph(subtitle, ParagraphStyle("s", parent=centre, fontSize=13, leading=18, textColor=slate)),
              Spacer(1, 14 * mm)]
    facts = [["%d" % len(traps), "%s" % format(sample or 0, ","), "%s" % band],
             ["traps", "real Lichess games", "rating band"]]
    table = Table(facts, colWidths=[52 * mm] * 3)
    table.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 22), ("TEXTCOLOR", (0, 0), (-1, 0), navy),
                               ("FONT", (0, 1), (-1, 1), "Helvetica", 9), ("TEXTCOLOR", (0, 1), (-1, 1), slate),
                               ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story += [table, Spacer(1, 16 * mm),
              Paragraph("Stockfish finds the best move. Trickfish finds the move your opponent will get wrong.", centre),
              PageBreak()]

    story += [Paragraph("How this pack was made", h2), Spacer(1, 2 * mm)]
    for text in meta.get("method", []):
        story += [Paragraph(text, body), Spacer(1, 2.5 * mm)]
    story += [Spacer(1, 4 * mm), Paragraph("How to use it", h2)]
    for text in meta.get("usage", []):
        story += [Paragraph("&bull; " + text, body), Spacer(1, 1.5 * mm)]
    story += [Spacer(1, 6 * mm), Paragraph("The traps at a glance", h2)]
    rows = [["#", "Line", "Wrong", "Your score"]]
    for trap in traps:
        rows.append([str(trap.number), Paragraph(trap.line_text() + " &nbsp;<b>" + trap.mistake_text() + "?</b>", small),
                     "%.0f%%" % (trap.record["error_share"] * 100), "%.0f%%" % (trap.top["our_score"] * 100)])
    table = Table(rows, colWidths=[9 * mm, 125 * mm, 18 * mm, 22 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9), ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f4f7")]),
                               ("ALIGN", (2, 0), (-1, -1), "CENTER")]))
    story += [table, PageBreak()]

    for trap in traps:
        record = trap.record
        stats = [["Games reaching this position", format(record["games"], ",")],
                 ["Opponents who went wrong", "%.0f%%" % (record["error_share"] * 100)],
                 ["Most common mistake", "%s  (%.0f%%)" % (trap.mistake_text(), trap.top["share"] * 100)],
                 ["%s's real score after it" % side, "%.0f%%" % (trap.top["our_score"] * 100)],
                 ["Engine eval after the mistake", pawns(trap.top["our_cp"])],
                 ["Best defence", "%s  (eval %s)" % (trap.best_text(), pawns(record["best_cp"]))]]
        table = Table(stats, colWidths=[52 * mm, 38 * mm])
        table.setStyle(TableStyle([("FONT", (0, 0), (0, -1), "Helvetica", 8.5), ("FONT", (1, 0), (1, -1), "Helvetica-Bold", 9),
                                   ("TEXTCOLOR", (0, 0), (0, -1), slate), ("TEXTCOLOR", (1, 1), (1, 2), coral),
                                   ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#d5dde5")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        top = Table([[image(trap.board, 82 * mm, lastmove=trap.board.peek()), table]], colWidths=[88 * mm, 92 * mm])
        top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        end = trap.after.copy()
        for uci in trap.punish_uci[:5]:
            move = chess.Move.from_uci(uci)
            if move in end.legal_moves:
                end.push(move)
        block = [Paragraph("Trap %d &middot; %s" % (trap.number, trap.name), h2),
                 Paragraph(trap.line_text(), line), Spacer(1, 3 * mm), top, Spacer(1, 4 * mm)]
        if trap.idea:
            block += [Paragraph("<b>Why it works.</b> " + trap.idea, body), Spacer(1, 2.5 * mm)]
        block += [Paragraph("<b>The punishment.</b> After <font color='%s'><b>%s?</b></font> play %s" % (
            CORAL, trap.mistake_text(), trap.punish_text()), body), Spacer(1, 2.5 * mm)]
        if trap.defence:
            block += [Paragraph("<b>If they defend correctly.</b> " + trap.defence, body), Spacer(1, 2.5 * mm)]
        other = [reply for reply in trap.mistakes if reply is not trap.top]
        if other:
            block += [Paragraph("Other losing replies seen: " + ", ".join(
                "%s (%.0f%%, eval %s)" % (numbered([reply["san"]], trap.ply), reply["share"] * 100, pawns(reply["our_cp"]))
                for reply in other), small), Spacer(1, 2 * mm)]
        block += [Table([[image(end, 58 * mm, lastmove=end.peek() if end.move_stack else None),
                          Paragraph("Position after the first moves of the punishment. Engine eval: %s." % pawns(trap.top["our_cp"]), small)]],
                        colWidths=[64 * mm, 110 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")])]
        story += [KeepTogether(block), PageBreak()]

    story += [Paragraph("Drills: punish the mistake", h1), Spacer(1, 3 * mm),
              Paragraph("Each diagram shows the position right after your opponent fell for the trap. Find the punishment "
                        "without looking back. Answers are at the end.", body), Spacer(1, 5 * mm)]
    cells = []
    for trap in traps:
        cells.append([image(trap.after, 74 * mm, lastmove=trap.after.peek()),
                      Paragraph("<b>Drill %d.</b> %s to move." % (trap.number, side), small)])
    grid = []
    for index in range(0, len(cells), 2):
        pair = cells[index:index + 2]
        grid.append([pair[0][0], pair[1][0] if len(pair) > 1 else ""])
        grid.append([pair[0][1], pair[1][1] if len(pair) > 1 else ""])
    drills = Table(grid, colWidths=[86 * mm, 86 * mm])
    drills.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [drills, PageBreak(), Paragraph("Answer key", h1), Spacer(1, 4 * mm)]
    for trap in traps:
        story += [Paragraph("<b>Drill %d.</b> %s" % (trap.number, trap.punish_text()), body), Spacer(1, 2 * mm)]
    story += [Spacer(1, 8 * mm), Paragraph("About the numbers", h2)]
    for text in meta.get("fineprint", []):
        story += [Paragraph(text, small), Spacer(1, 2 * mm)]

    document = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                                 bottomMargin=18 * mm, title=title, author="Trickfish")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render a Trickfish trap pack")
    parser.add_argument("traps")
    parser.add_argument("--notes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    data, meta, traps = load(args.traps, args.notes)
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    slug = meta.get("slug", "trap-pack")
    write_pdf(data, meta, traps, output / (slug + ".pdf"))
    write_pgn(data, traps, output / (slug + ".pgn"), meta.get("title", "Trickfish trap pack"))
    write_cards(data, meta, traps, output / "cards")
    print("rendered %d traps into %s" % (len(traps), output))


if __name__ == "__main__":
    main()
