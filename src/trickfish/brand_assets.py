"""Brand assets for a trap pack: social cards, profile picture, banner, store images."""

import argparse
import pathlib

import chess

from trickfish import brand
from trickfish.brand import ACCENT, CARD, ICE, INK, LINE, MUTED, SOFT, WHITE, Canvas
from trickfish.trappack_render import load, pawns

HERO = "InterDisplay-Black"
BOLD = "InterDisplay-Bold"
SEMI = "Inter-SemiBold"
MEDIUM = "Inter-Medium"
REGULAR = "Inter-Regular"


def band_label(data):
    return data.get("band", "").replace("-", "–")


def punished(trap, plies=5):
    end = trap.after.copy()
    for uci in trap.punish_uci[:plies]:
        move = chess.Move.from_uci(uci)
        if move not in end.legal_moves:
            break
        end.push(move)
    return end


def short_line(trap, limit=7):
    sans = trap.line_text().split()
    return ("… " if len(sans) > limit else "") + " ".join(sans[-limit:])


def header(canvas, data, right=None):
    brand.wordmark(canvas, (72, 64), size=34)
    label = right or band_label(data) + " rated"
    width = canvas.width_of(label, SEMI, 24) + 44
    canvas.pill((canvas.width - 72 - width, 62), label, SEMI, 24, dot=ACCENT)


def question_card(data, trap, path):
    canvas = Canvas(1080, 1350, glow=((0.92, 0.02, 0.5, 0.16), (0.0, 1.0, 0.35, 0.05)))
    header(canvas, data)
    share = "%.0f%%" % (trap.record["error_share"] * 100)
    canvas.text((68, 150), share, HERO, 210, ACCENT)
    canvas.text((76 + canvas.width_of(share, HERO, 210) + 14, 242), "of players", BOLD, 54, WHITE)
    canvas.text((76 + canvas.width_of(share, HERO, 210) + 14, 306), "go wrong here.", BOLD, 54, WHITE)
    size = 760
    x, y = (1080 - size) // 2, 418
    canvas.shadow((x, y, x + size, y + size), radius=26)
    canvas.paste(brand.board(trap.board, size, lastmove=trap.board.peek(),
                             flipped=data["color"] == "black"), (x, y), radius=26)
    side = "Black" if trap.board.turn == chess.BLACK else "White"
    bottom = 1212
    after = canvas.pill((72, bottom), "%s to move" % side, SEMI, 26, fill=WHITE, color=INK, outline=WHITE)
    canvas.pill((after + 14, bottom), "%s real games" % format(trap.record["games"], ","), SEMI, 26)
    canvas.text((72, 1300), short_line(trap), MEDIUM, 24, MUTED)
    canvas.text((1008, 1300), "Your move?", SEMI, 24, SOFT, anchor="ra")
    canvas.save(path)


def answer_card(data, trap, path):
    canvas = Canvas(1080, 1350, glow=((0.08, 0.02, 0.5, 0.14),))
    header(canvas, data, right="The answer")
    canvas.text((72, 160), "THE TRAP", SEMI, 26, MUTED)
    canvas.text((68, 196), trap.mistake_text() + "?", HERO, 150, ACCENT)
    canvas.text((72, 378), "%.0f%% of players chose it. Here's the punishment:" % (trap.top["share"] * 100),
                MEDIUM, 32, SOFT)
    size = 560
    x, y = 72, 448
    end = punished(trap)
    canvas.shadow((x, y, x + size, y + size), radius=24)
    canvas.paste(brand.board(end, size, lastmove=end.peek() if end.move_stack else None,
                             flipped=data["color"] == "black"), (x, y), radius=24)
    tx = x + size + 32
    tiles = [("%.0f%%" % (trap.top["our_score"] * 100), "real score after it"),
             (pawns(trap.top["our_cp"]), "engine eval"),
             (format(trap.record["games"], ","), "games reached it")]
    tile_h = (size - 2 * 20) / 3
    for index, (value, label) in enumerate(tiles):
        top = y + index * (tile_h + 20)
        canvas.card((tx, top, 1008, top + tile_h), radius=22)
        canvas.text((tx + 26, top + 26), value, HERO if index == 0 else BOLD, 64 if index == 0 else 52,
                    ACCENT if index == 0 else WHITE)
        canvas.text((tx + 26, top + tile_h - 44), label, MEDIUM, 24, MUTED)
    canvas.card((72, 1040, 1008, 1196), radius=22)
    canvas.text((100, 1066), "PUNISH IT", SEMI, 22, MUTED)
    punish = " ".join(trap.punish_text().split()[:6])
    canvas.text((100, 1102), punish, BOLD, 38, WHITE)
    canvas.text((100, 1152), "Best defence was %s" % trap.best_text(), MEDIUM, 26, SOFT)
    canvas.text((72, 1262), "All 23 traps, drills and PGN", SEMI, 28, WHITE)
    canvas.text((72, 1300), "Link in bio", MEDIUM, 24, MUTED)
    canvas.pill((1008 - canvas.width_of("Get the pack  →", SEMI, 28) - 44, 1252), "Get the pack  →", SEMI, 28,
                fill=ACCENT, color=WHITE, outline=ACCENT)
    canvas.save(path)


def profile(path):
    canvas = Canvas(800, 800, glow=((0.5, 0.45, 0.42, 0.10),))
    logo = brand.mark(560)
    canvas.paste(logo, ((800 - logo.width / brand.SCALE) / 2, (800 - logo.height / brand.SCALE) / 2))
    canvas.save(path)


def banner(data, trap, path):
    canvas = Canvas(1500, 500, glow=((0.78, 0.5, 0.42, 0.22), (0.05, 0.0, 0.3, 0.07)))
    canvas.text((96, 92), "Stockfish finds the best move.", BOLD, 58, WHITE)
    canvas.text((96, 166), "We find the one they miss.", BOLD, 58, ACCENT)
    canvas.text((98, 258), "Chess traps measured on 900,000+ real Lichess games.", MEDIUM, 26, SOFT)
    # floating stat card, app-style
    x0, y0, x1, y1 = 1010, 70, 1410, 440
    canvas.shadow((x0, y0, x1, y1), radius=30, blur=34)
    canvas.card((x0, y0, x1, y1), radius=30, fill=(17, 22, 31))
    size = 176
    canvas.paste(brand.board(trap.board, size, lastmove=trap.board.peek()), (x0 + 28, y0 + 28), radius=14)
    canvas.text((x0 + 28 + size + 24, y0 + 34), "%.0f%%" % (trap.record["error_share"] * 100), HERO, 84, ACCENT)
    canvas.text((x0 + 28 + size + 26, y0 + 132), "go wrong", SEMI, 26, WHITE)
    canvas.text((x0 + 28 + size + 26, y0 + 166), "here", SEMI, 26, WHITE)
    canvas.draw.line(canvas.s(x0 + 28, y0 + 236, x1 - 28, y0 + 236), fill=LINE, width=2 * brand.SCALE)
    canvas.text((x0 + 28, y0 + 260), "Fried Liver · 7.Qf3+", SEMI, 24, WHITE)
    canvas.text((x0 + 28, y0 + 298), "%s games · 1200–1599" % format(trap.record["games"], ","), MEDIUM, 22, MUTED)
    canvas.pill((x0 + 28, y0 + 330 - 2), "White scores %.0f%%" % (trap.top["our_score"] * 100), SEMI, 20,
                fill=(40, 22, 18), color=ACCENT, outline=(80, 36, 26), pad=(16, 7))
    canvas.save(path)


def thumbnail(data, meta, traps, path):
    canvas = Canvas(1200, 1200, glow=((0.95, 0.0, 0.55, 0.24), (0.0, 1.0, 0.4, 0.07)))
    brand.wordmark(canvas, (80, 76), size=38)
    canvas.text((76, 190), "1.e4 e5", HERO, 170, WHITE)
    canvas.text((76, 362), "Traps", HERO, 170, ACCENT)
    canvas.text((82, 604), "for White · %s" % band_label(data), SEMI, 40, SOFT)
    trap = traps[0]
    size = 430
    x, y = 1200 - 80 - size, 610
    canvas.shadow((x, y, x + size, y + size), radius=24)
    canvas.paste(brand.board(trap.board, size, lastmove=trap.board.peek()), (x, y), radius=24)
    stats = [(str(len(traps)), "traps"), ("902k", "real games"), ("32", "pages")]
    for index, (value, label) in enumerate(stats):
        top = 720 + index * 122
        canvas.text((80, top), value, HERO, 78, WHITE if index else ACCENT)
        canvas.text((84 + canvas.width_of(value, HERO, 78) + 14, top + 44), label, MEDIUM, 28, MUTED)
    canvas.save(path)


def cover_hero(data, meta, traps, path):
    canvas = Canvas(1600, 900, glow=((0.9, 0.1, 0.5, 0.22), (0.0, 1.0, 0.35, 0.06)))
    brand.wordmark(canvas, (96, 84), size=34)
    canvas.text((92, 190), "1.e4 e5 Traps", HERO, 120, WHITE)
    canvas.text((92, 320), "for White.", HERO, 120, ACCENT)
    canvas.wrap((98, 482), "The moves real %s players get wrong, found in %s Lichess games and checked by Stockfish."
                % (band_label(data), format(data.get("sample_games") or 0, ",")), MEDIUM, 32, 700, SOFT, 1.4)
    x = 98
    for label in ("%d traps" % len(traps), "PDF + drills", "PGN"):
        x = canvas.pill((x, 660), label, SEMI, 28) + 14
    # two stacked app-style cards
    for offset, trap in ((0, traps[0]), (1, traps[18] if len(traps) > 18 else traps[-1])):
        x0 = 930 + offset * 60
        y0 = 120 + offset * 330
        size = 260
        canvas.shadow((x0, y0, x0 + 520, y0 + size + 56), radius=28, blur=30)
        canvas.card((x0, y0, x0 + 520, y0 + size + 56), radius=28, fill=(17, 22, 31))
        canvas.paste(brand.board(trap.board, size, lastmove=trap.board.peek()), (x0 + 28, y0 + 28), radius=14)
        canvas.text((x0 + size + 52, y0 + 40), "%.0f%%" % (trap.record["error_share"] * 100), HERO, 80, ACCENT)
        canvas.text((x0 + size + 54, y0 + 136), "go wrong", SEMI, 26, WHITE)
        canvas.wrap((x0 + size + 54, y0 + 186), trap.name.split(":")[0], MEDIUM, 22, 180, MUTED)
    canvas.save(path)


def cover_inside(data, meta, traps, path):
    canvas = Canvas(1600, 900, glow=((0.1, 0.0, 0.45, 0.18),))
    brand.wordmark(canvas, (96, 84), size=34)
    canvas.text((92, 180), "What's inside", HERO, 92, WHITE)
    openings = []
    for trap in traps:
        name = trap.name.split(":")[0]
        if name not in openings:
            openings.append(name)
    x, y = 96, 330
    for name in openings:
        width = canvas.width_of(name, SEMI, 30) + 48
        if x + width > 1504:
            x, y = 96, y + 82
        x = canvas.pill((x, y), name, SEMI, 30, pad=(24, 16)) + 16
    tiles = [(str(len(traps)), "sound traps"), (format(data.get("sample_games") or 0, ","), "real games analysed"),
             ("0.5", "max pawns you risk per move"), ("60%+", "your real score after each trap")]
    tile_w = (1504 - 96 - 3 * 24) / 4
    for index, (value, label) in enumerate(tiles):
        left = 96 + index * (tile_w + 24)
        canvas.card((left, 610, left + tile_w, 800), radius=24)
        canvas.text((left + 28, 636), value, HERO, 60, ACCENT if index == 0 else WHITE)
        canvas.wrap((left + 28, 726), label, MEDIUM, 24, tile_w - 56, MUTED, 1.3)
    canvas.save(path)


def cover_method(data, meta, traps, path):
    canvas = Canvas(1600, 900, glow=((0.95, 1.0, 0.45, 0.18),))
    brand.wordmark(canvas, (96, 84), size=34)
    canvas.text((92, 180), "How we find traps", HERO, 92, WHITE)
    steps = [("01", "Real games", "%s rated Lichess games where both players are %s."
              % (format(data.get("sample_games") or 0, ","), band_label(data))),
             ("02", "Sound moves only", "Every move you play is within half a pawn of Stockfish's best. "
              "Nothing to refute."),
             ("03", "Proven mistakes", "15%+ of opponents go wrong, and you really scored 60%+ "
              "after the most common mistake.")]
    width = (1504 - 96 - 2 * 28) / 3
    for index, (number, title, body) in enumerate(steps):
        left = 96 + index * (width + 28)
        canvas.card((left, 340, left + width, 780), radius=28)
        canvas.text((left + 36, 380), number, HERO, 64, ACCENT)
        canvas.text((left + 36, 500), title, BOLD, 40, WHITE)
        canvas.wrap((left + 36, 566), body, MEDIUM, 28, width - 72, SOFT, 1.4)
    canvas.save(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render Trickfish brand assets for a pack")
    parser.add_argument("traps")
    parser.add_argument("--notes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    data, meta, traps = load(args.traps, args.notes)
    out = pathlib.Path(args.output)
    (out / "cards").mkdir(parents=True, exist_ok=True)
    (out / "store").mkdir(parents=True, exist_ok=True)
    (out / "x").mkdir(parents=True, exist_ok=True)
    for trap in traps:
        question_card(data, trap, out / "cards" / ("trap-%02d.png" % trap.number))
        answer_card(data, trap, out / "cards" / ("trap-%02d-answer.png" % trap.number))
    profile(out / "x" / "profile.png")
    banner(data, traps[0], out / "x" / "banner.png")
    thumbnail(data, meta, traps, out / "store" / "thumbnail.png")
    cover_hero(data, meta, traps, out / "store" / "cover-1-hero.png")
    cover_inside(data, meta, traps, out / "store" / "cover-2-inside.png")
    cover_method(data, meta, traps, out / "store" / "cover-3-method.png")
    print("brand assets written to", out)


if __name__ == "__main__":
    main()
