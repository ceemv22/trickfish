"""Trickfish studio, route A: "Line & Hook".

The idea: in chess a *line* is a sequence of moves; in fishing it is what the
hook hangs from. Every trap is drawn as one red fishing line, laid by hand
across a printed book diagram, that ends in a hook on the square where the
opponent is caught.

System (see docs/design/route-a.md):
* Paper #EEEAE0, ink #15130F, hook red #C4161C (only ever the line and the
  hook), water #1F3A44 (store and avatar grounds). No gradients, no shadows.
* Young Serif for the one big number, Schibsted Grotesk for text, Martian
  Mono for notation and data. Three sizes per card. Figurines are drawn
  with the same Merida pieces as the diagram.
* Boards are printed diagrams: paper light squares, ink-hatched dark
  squares, a ruled ink frame, mono coordinates.

Everything is laid out in HTML/CSS/SVG and rendered by Chromium (render.mjs)
at deviceScaleFactor 2.
"""

import html
import json
import math
import pathlib
import random
import re
import shutil
import subprocess
import tempfile

import chess

from trickfish.trappack_render import pawns

PAPER = "#EEEAE0"
INK = "#15130F"
HOOK = "#C4161C"
WATER = "#1F3A44"
BOBBER = "#FFFFFF"
FADED = "#6F6A5F"        # ink printed at ~60%: secondary text, coordinates
WATER_FADED = "#9DB0B4"  # paper printed at ~60% on water

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FONTS = ROOT / "assets" / "fonts"

# Card type scale: exactly three sizes per card.
L, M, S = 226, 34, 19


# ---------------------------------------------------------------- art direction
#
# Which piece's path the red line follows, and where the hook lands, is an
# editorial decision: the hook goes on the square where the opponent is
# actually caught (the piece that is won, or the square that is attacked).
# Keys are the trap names from notes.json. Traps not listed here fall back to the
# automatic rule in `catch()`.
CATCH = {
    "Fried Liver: the pinned knight": (["c4", "d5"], "d5", 1),
    "Fried Liver: grabbing on d5": (["f3", "d5"], "d5", 1),
    "Traxler: the greedy knight": (["d1", "h5", "g6", "g8", "e8"], "e8", 9),
    "Two Knights: the bishop check on f7": (["e1", "f2"], "f2", 1),
    "Two Knights: the double attack on d5": (["d1", "d5", "e4"], "e4", 5),
    "Giuoco Piano: the b7/f7 queen": (["d1", "b3", "b7"], "b7", 5),
    "Scotch: the hanging bishop on c5": (["e3", "c5"], "c5", 3),
    "Scotch: the knight on the rim": (["g2", "g4"], "h5", 1),
    "Scotch: the knight on the rim, part two": (["g2", "g4", "h5"], "h5", 3),
    "Scotch: the queen fork on d5": (["d4", "d5", "a8"], "a8", 3),
    "Scotch: the wrong recapture": (["f3", "e5"], "e5", 1),
    "Ruy Lopez: the automatic recapture": (["f3", "e5", "c6"], "c6", 7),
    "Ruy Lopez: the pinned knight": (["d2", "d4", "d5", "c6"], "c6", 9),
    "Ruy Lopez: the same pin again": (["d2", "d4", "d5", "c6"], "c6", 5),
    "Ruy Lopez: the e-file": (["d2", "d3"], "e4", 1),
    "Three Knights: the fork trick": (["d4", "g7"], "h8", 1),
    "Petrov: the discovered check": (["e5", "c6"], "d8", 3),
    "Petrov: the wrong recapture": (["f3", "e5"], "f7", 3),
    "Bishop's Opening: the queen on h5": (["h5", "e5", "h8"], "h8", 3),
    "Bishop's Opening: queen trade with a sting": (["h5", "e5"], "h8", 1),
    "Bishop's Opening: the f7 check": (["c4", "f7"], "f7", 1),
    "Vienna Gambit: pawns with tempo": (["f4", "e5"], "e5", 1),
    "Vienna Gambit: the e-file pin that doesn't work": (["d1", "e2", "e4"], "e4", 7),
}


def catch(trap):
    """Return (route squares, hook square, plies of the punishment to print)."""
    if trap.name in CATCH:
        route, hook, plies = CATCH[trap.name]
        return [chess.parse_square(s) for s in route], chess.parse_square(hook), plies
    # Fallback: follow the first punishing piece while it keeps moving, until
    # it wins material or is taken.
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
    board = trap.after.copy()
    route, current, plies = None, None, 1
    for index, uci in enumerate(trap.punish_uci[:9]):
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            break
        ours = index % 2 == 0
        captured = board.piece_at(move.to_square)
        if ours and route is None:
            route, current, plies = [move.from_square, move.to_square], move.to_square, 1
        elif ours and move.from_square == current:
            route.append(move.to_square)
            current, plies = move.to_square, index + 1
        elif not ours and move.to_square == current:
            break
        board.push(move)
        if ours and move.to_square == current and captured and values[captured.piece_type] >= 3:
            break
    if not route:
        move = trap.board.peek()
        route = [move.from_square, move.to_square]
    return route, route[-1], plies


# ---------------------------------------------------------------- type and text

def font_css():
    faces = [("Young Serif", "young-serif/young-serif-latin-400-normal.woff2", 400, "normal")]
    faces += [("Schibsted Grotesk", "schibsted-grotesk/schibsted-grotesk-latin-%d-normal.woff2" % w, w, "normal")
              for w in (400, 500, 600, 700, 800, 900)]
    faces += [("Schibsted Grotesk", "schibsted-grotesk/schibsted-grotesk-latin-400-italic.woff2", 400, "italic")]
    faces += [("Martian Mono", "martian-mono/martian-mono-latin-%d-normal.woff2" % w, w, "normal")
              for w in (300, 400, 500, 600, 700)]
    return "".join("@font-face{font-family:'%s';src:url('file://%s') format('woff2');font-weight:%d;font-style:%s}"
                   % (family, FONTS / path, weight, style) for family, path, weight, style in faces)


BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: %(w)dpx; height: %(h)dpx; overflow: hidden; }
body { position: relative; background: %(bg)s; color: %(fg)s; font-family: 'Schibsted Grotesk';
       font-kerning: normal; text-rendering: geometricPrecision; -webkit-font-smoothing: antialiased; }
.abs { position: absolute; }
.num { font-family: 'Young Serif'; font-weight: 400; line-height: .9; letter-spacing: -0.035em;
       font-feature-settings: 'kern' 1; }
.serif { font-family: 'Young Serif'; font-weight: 400; letter-spacing: -0.01em; }
.txt { font-family: 'Schibsted Grotesk'; }
.mono { font-family: 'Martian Mono'; font-weight: 400; letter-spacing: 0; font-variant-numeric: tabular-nums; }
.faded { color: %(faded)s; }
.fig { display: inline-block; width: .92em; height: .92em; vertical-align: -0.14em; margin: 0 -0.04em 0 -0.02em; }
svg { display: block; overflow: visible; }
.fig svg { width: 100%%; height: 100%%; }
"""


def page(width, height, body, bg=PAPER, fg=INK, faded=FADED, extra=""):
    css = BASE_CSS % {"w": width, "h": height, "bg": bg, "fg": fg, "faded": faded}
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s%s%s</style></head><body>%s</body></html>'
            % (font_css(), css, extra, body))


def esc(text):
    """Escape for HTML and set typographic apostrophes."""
    return html.escape(str(text), quote=False).replace("'", "\u2019")


def ellipsis(text):
    return text.replace("...", "…")


def band(data):
    return data.get("band", "").replace("-", "–")


def thousands(n):
    return format(n, ",")


def percent(x):
    return "%d" % round(x * 100)


def opening_of(trap):
    return trap.name.split(":")[0].strip()


def title_of(trap):
    rest = trap.name.split(":", 1)[1].strip() if ":" in trap.name else trap.name
    return rest[:1].upper() + rest[1:]


def side_name(color):
    return "White" if color == chess.WHITE else "Black"


# ---------------------------------------------------------------- pieces

_PIECES = {}


def piece_inner(code):
    if code not in _PIECES:
        text = (HERE / "pieces" / ("%s.svg" % code)).read_text(encoding="utf-8")
        _PIECES[code] = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S).group(1)
    return _PIECES[code]


def piece_svg(code, x, y, size, ink=INK, paper=PAPER):
    inner = piece_inner(code).replace("#1f1a17", ink).replace("#fff", paper)
    return ('<svg x="%.2f" y="%.2f" width="%.2f" height="%.2f" viewBox="0 0 50 50" fill-rule="evenodd" '
            'clip-rule="evenodd">%s</svg>' % (x, y, size, size, inner))


def figurine(letter, ink=INK, paper=PAPER):
    inner = piece_inner("b" + letter).replace("#1f1a17", ink).replace("#fff", paper)
    return ('<span class="fig"><svg viewBox="2 2 46 46" fill-rule="evenodd">%s</svg></span>' % inner)


def notation(text, ink=INK, paper=PAPER):
    """Escape SAN text and set piece letters as Merida figurines."""
    text = esc(ellipsis(text))
    return re.sub(r"[KQRBN]", lambda m: figurine(m.group(0), ink, paper), text)


# ---------------------------------------------------------------- the hand-drawn line

def _bezier(points, t):
    while len(points) > 1:
        points = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(points, points[1:])]
    return points[0]


def _line_samples(stops, sq, rng):
    """Centre-line of a hand-laid line through `stops` (bowing a little between them)."""
    samples = []
    for index, (a, b) in enumerate(zip(stops, stops[1:])):
        length = math.dist(a, b)
        nx, ny = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length) if length else (0, 0)
        bow = rng.uniform(0.04, 0.08) * length * rng.choice((-1, 1))
        mid = ((a[0] + b[0]) / 2 + nx * bow, (a[1] + b[1]) / 2 + ny * bow)
        steps = max(10, int(length / (sq * 0.04)))
        last = index == len(stops) - 2
        for step in range(steps + (1 if last else 0)):
            samples.append(_bezier([a, mid, b], step / steps))
    return samples


def hand_line(stops, sq, seed, color=HOOK, halo=PAPER, width=0.12, halo_width=0.05):
    """A red line drawn as a nib would: width swells and thins, the path bows a
    little between stops, and a paper knockout keeps it legible over hatching."""
    rng = random.Random(seed)
    pts = _line_samples(stops, sq, rng)
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1
    phase = [rng.uniform(0, 1) for _ in range(4)]
    run, under, over = 0.0, [], []
    for a, b in zip(pts, pts[1:]):
        t = run / total
        run += math.dist(a, b)
        swell = 1 + 0.15 * math.sin(2 * math.pi * (1.2 * t + phase[0])) + 0.07 * math.sin(2 * math.pi * (3.7 * t + phase[1]))
        taper = min(1.0, 0.5 + t / 0.08 * 0.5)
        w = sq * width * swell * taper
        d = "M%.2f %.2fL%.2f %.2f" % (a[0], a[1], b[0], b[1])
        under.append('<path d="%s" stroke-width="%.2f"/>' % (d, w + 2 * sq * halo_width))
        over.append('<path d="%s" stroke-width="%.2f"/>' % (d, w))
    return ('<g fill="none" stroke-linecap="round" stroke="%s">%s</g><g fill="none" stroke-linecap="round" stroke="%s">%s</g>'
            % (halo, "".join(under), color, "".join(over)))


def hook_path(u, shank=0.95, bend=0.38, point=0.62, weight=0.12, eye=0.075):
    """Geometry of a J-hook in local units of `u` (one diagram square): eye
    at the origin, shank running down +y, bend opening towards +x."""
    w = u * weight
    r = u * eye
    by = u * shank
    br = u * bend
    px = 2 * br
    tip = u * point
    ring = (0, r, r, w * 0.62)
    body = "M0 %.2f L0 %.2f A%.2f %.2f 0 0 0 %.2f %.2f L%.2f %.2f" % (2 * r, by, br, br, px, by, px, by - u * 0.1)
    taper = "M%.2f %.2f L%.2f %.2f L%.2f %.2f Z" % (px - w / 2, by - u * 0.1, px + w * 0.06, tip, px + w / 2, by - u * 0.1)
    barb = "M%.2f %.2f L%.2f %.2f L%.2f %.2f Z" % (px - w * 0.1, tip + u * 0.03, px - w * 0.45, tip + u * 0.2,
                                                   px - w * 1.35, tip + u * 0.22)
    return ring, body, taper, barb, w


def hook_shape(x, y, u, color=HOOK, halo=None, halo_width=0.0, transform="", **geometry):
    """A J-hook: ring eye, straight shank, round bend, tapered point, barb.
    (x, y) is the eye; `transform` (SVG) is applied about the eye."""
    (cx, cy, r, ring_w), body, taper, barb, w = hook_path(u, **geometry)

    def draw(colour, extra):
        return ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" stroke-width="%.2f"/>'
                '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>'
                '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
                '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
                % (cx, cy, r, colour, ring_w + extra, body, colour, w + extra, taper, colour, colour, extra or 0.01,
                   barb, colour, colour, extra or 0.01))

    inner = (draw(halo, 2 * halo_width) if halo else "") + draw(color, 0)
    return '<g transform="translate(%.2f %.2f) %s">%s</g>' % (x, y, transform, inner)


# ---------------------------------------------------------------- the diagram

def square_xy(square, sq):
    return chess.square_file(square) * sq, (7 - chess.square_rank(square)) * sq


def centre(square, sq):
    x, y = square_xy(square, sq)
    return x + sq / 2, y + sq / 2


def board_svg(board, sq, *, catch_=None, trail=None, coords=True, coord_size=S, seed=1, uid="d",
              ink=INK, paper=PAPER, line_color=HOOK, coord_color=FADED, frame=True, hatch=None):
    """A printed book diagram. `catch_` = (route squares, hook square) draws the
    red line; `trail` = chess.Move draws the opponent's move as an ink dotted wake."""
    n = 8 * sq
    period = hatch or max(3.4, sq / 11.5)
    out = ['<svg width="%.2f" height="%.2f" viewBox="0 0 %.2f %.2f" xmlns="http://www.w3.org/2000/svg">' % (n, n, n, n),
           '<defs><pattern id="h-%s" patternUnits="userSpaceOnUse" width="%.3f" height="%.3f" patternTransform="rotate(-45)">'
           '<rect width="%.3f" height="%.3f" fill="%s"/></pattern></defs>' % (uid, period, period, period * 0.30, period, ink),
           '<rect width="%.2f" height="%.2f" fill="%s"/>' % (n, n, paper)]
    for square in chess.SQUARES:
        if (chess.square_file(square) + chess.square_rank(square)) % 2 == 0:
            x, y = square_xy(square, sq)
            out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="url(#h-%s)"/>' % (x, y, sq, sq, uid))
    if frame:
        inner = max(1.0, sq * 0.012)
        outer = max(2.0, sq * 0.05)
        gap = sq * 0.07
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="%.2f"/>'
                   % (-inner / 2, -inner / 2, n + inner, n + inner, ink, inner))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="%.2f"/>'
                   % (-gap - outer / 2, -gap - outer / 2, n + 2 * gap + outer, n + 2 * gap + outer, ink, outer))
    if trail is not None:
        out.append(_trail(trail, sq, ink, paper))
    for square, p in board.piece_map().items():
        x, y = square_xy(square, sq)
        code = ("w" if p.color else "b") + p.symbol().upper()
        out.append(piece_svg(code, x, y, sq, ink, paper))
    if catch_ is not None:
        out.append(draw_catch(catch_, sq, seed, line_color, paper))
    if coords:
        gap = sq * 0.07 + max(2.0, sq * 0.05)
        for i in range(8):
            out.append('<text x="%.2f" y="%.2f" font-family="Martian Mono" font-size="%.2f" fill="%s" text-anchor="middle">%s</text>'
                       % (i * sq + sq / 2, n + gap + coord_size * 1.25, coord_size, coord_color, "abcdefgh"[i]))
            out.append('<text x="%.2f" y="%.2f" font-family="Martian Mono" font-size="%.2f" fill="%s" text-anchor="end">%d</text>'
                       % (-gap - coord_size * 0.55, i * sq + sq / 2 + coord_size * 0.36, coord_size, coord_color, 8 - i))
    out.append("</svg>")
    return "".join(out)


def draw_catch(catch_, sq, seed, color=HOOK, paper=PAPER):
    """The red line through the route, tied to the eye of a hook that hangs
    over the hook square: the caught piece sits inside the bend, like the fish
    in the mark. The hook always hangs (a hook only reads as a hook when it
    hangs from its eye)."""
    route, hook = catch_
    stops = [centre(s, sq) for s in route]
    if route[-1] == hook:
        stops = stops[:-1]
    tx, ty = centre(hook, sq)
    bend = 0.47
    bottom = ty + sq * 0.5                         # bend bottom on the square's lower edge
    eye_y = max(ty - sq * 0.86, sq * 0.04)         # top rank: shorter shank, stays on the board
    shank = (bottom - sq * bend - eye_y) / sq
    geometry = dict(shank=shank, bend=bend, point=shank - 0.38, weight=0.11, eye=0.08)
    ex = tx - sq * bend
    out = [hand_line(stops + [(ex, eye_y)], sq, seed, color, paper)]
    for stop in route[1:]:
        if stop != hook:
            x, y = centre(stop, sq)
            out.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/><circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                       % (x, y, sq * 0.125, paper, x, y, sq * 0.08, color))
    out.append(hook_shape(ex, eye_y, sq, color, paper, sq * 0.04, **geometry))
    return "".join(out)


def _trail(move, sq, ink, paper):
    (ax, ay), (bx, by) = centre(move.from_square, sq), centre(move.to_square, sq)
    length = math.dist((ax, ay), (bx, by))
    ux, uy = (bx - ax) / length, (by - ay) / length
    dots = []
    d = sq * 0.2
    while d < length - sq * 0.42:
        dots.append('<circle cx="%.2f" cy="%.2f" r="%.2f"/>' % (ax + ux * d, ay + uy * d, sq * 0.032))
        d += sq * 0.13
    ring = ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>'
            % (ax, ay, sq * 0.11, paper, ink, sq * 0.028))
    halo = "".join(dot.replace('r="%.2f"' % (sq * 0.032), 'r="%.2f"' % (sq * 0.062)) for dot in dots)
    return '<g fill="%s">%s</g><g fill="%s">%s</g>%s' % (paper, halo, ink, "".join(dots), ring)


# ---------------------------------------------------------------- shared pieces of layout

def score_rows(sans, start_ply=0, blank=False):
    """Full-move rows (number, white, black) for a score column."""
    rows = []
    for offset, san in enumerate(sans):
        ply = start_ply + offset
        if ply % 2 == 0:
            rows.append([str(ply // 2 + 1), san, ""])
        else:
            if not rows:
                rows.append([str(ply // 2 + 1), "…", ""])
            rows[-1][2] = san
    if blank and rows and rows[-1][2] == "":
        rows[-1][2] = "?"
    return rows


def score_column(rows, size, row_height, highlight_from=None):
    """Mono score sheet on a fixed row pitch (half a diagram square), so the
    rows keep time with the ranks beside them. Rows from `highlight_from` on
    (the punishment) are set heavier; the rows before it are faded."""
    out = ['<div class="mono" style="font-size:%dpx;line-height:%dpx">' % (size, row_height)]
    for index, (num, white, black) in enumerate(rows):
        strong = highlight_from is not None and index >= highlight_from
        faded = highlight_from is not None and index < highlight_from - 1
        black_html = '<span style="font-weight:700">?</span>' if black == "?" else notation(black)
        out.append('<div class="%s" style="display:grid;grid-template-columns:3.1ch 6.9ch auto;font-weight:%d">'
                   '<span style="text-align:right;padding-right:.4ch">%s.</span><span>%s</span><span>%s</span></div>'
                   % ("faded" if faded else "", 600 if strong else 400, num, notation(white), black_html))
    out.append("</div>")
    return "".join(out)


def lockup(x, top, size, color=INK, hook=HOOK, drop=None):
    """Wordmark lockup: a red line dropping from the top edge into a hook,
    beside the name set in Young Serif."""
    h = size * 1.3
    drop = top if drop is None else drop
    line = ('<svg class="abs" style="left:%.1fpx;top:0" width="%.1f" height="%.1f">'
            '<path d="M%.2f 0 L%.2f %.2f" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>%s</svg>'
            % (x, h, drop + h, h * 0.1, h * 0.1, drop, hook, h * 0.055, hook_shape(h * 0.1, drop, h, hook, shank=0.62, bend=0.21, point=0.4, weight=0.11)))
    word = ('<div class="abs serif" style="left:%.1fpx;top:%.1fpx;font-size:%dpx;line-height:1;color:%s">Trickfish</div>'
            % (x + h * 0.62, drop + h * 0.18, size, color))
    return line + word


# ---------------------------------------------------------------- cards (1080 x 1350)
#
# Grid: 64 px margins. A score column (64-250) and a main column (296-1016)
# that holds the diagram; text blocks hang from the d-file line (566).
# Everything that matters sits inside the centred 1080 x 1080 safe zone
# (y 135-1215).

CARD_W, CARD_H = 1080, 1350
SQ = 90
BX, BY = 296, 372
TEXT_X = BX + 2 * SQ


def card_frame(data, trap, total, answer):
    side = "Answer" if answer else "Trap"
    return (lockup(64, 58, M) +
            '<div class="abs mono faded" style="right:64px;top:%dpx;font-size:%dpx">%s %02d<span style="opacity:.6"> / %d</span></div>'
            % (78, S, side, trap.number, total))


def engine_name(data):
    return str(data.get("engine", "Stockfish 16"))


def big_number(value):
    return ('<div class="abs num" style="left:50px;top:122px;font-size:%dpx">%s<span style="font-size:.6em;'
            'letter-spacing:0;margin-left:.04em">%%</span></div>' % (L, value))


def head_text(first, second):
    return ('<div class="abs" style="left:%dpx;top:166px;width:%dpx">'
            '<div class="txt" style="font-size:%dpx;line-height:1.24">%s</div>'
            '<div class="serif" style="font-size:%dpx;line-height:1.2;margin-top:14px">%s</div></div>'
            % (TEXT_X, 1016 - TEXT_X, M, first, M, second))


def score_block(rows, highlight_from=None):
    pitch = SQ // 2
    top = BY + SQ if len(rows) <= 14 else BY
    return ('<div class="abs" style="left:52px;top:%dpx;width:236px">%s</div>'
            % (top + 2, score_column(rows, S, pitch, highlight_from)))


def footer(data):
    """Outside the safe zone: the handle, and the pack the trap comes from."""
    title = data.get("title") or ""
    return ('<div class="abs mono faded" style="left:64px;right:64px;top:1262px;font-size:%dpx;display:flex;'
            'justify-content:space-between"><span>@trickfishchess</span><span>%s</span></div>'
            % (S, esc("From " + title) if title else ""))


def caption(lines):
    return ('<div class="abs mono" style="left:%dpx;top:%dpx;width:%dpx;font-size:%dpx;line-height:1.42">%s</div>'
            % (BX, BY + 8 * SQ + 58, 8 * SQ + 40, S, "<br>".join(lines)))


def question(data, trap, total):
    mover = side_name(trap.board.turn)
    rows = score_rows(trap.sans, blank=True)
    last = notation(trap.line_text().split()[-1])
    body = (card_frame(data, trap, total, False) + big_number(percent(trap.record["error_share"])) +
            head_text("of %s players<br>bite here. <span style=\"font-weight:600\">%s to move.</span>"
                      % (esc(band(data)), mover), "%s." % esc(opening_of(trap))) +
            '<div class="abs" style="left:%dpx;top:%dpx">%s</div>' % (BX, BY, board_svg(trap.board, SQ, uid="q")) +
            score_block(rows) +
            caption(['<span class="faded">n = %s games reached this position.</span>' % thousands(trap.record["games"]),
                     '<span class="faded">Lichess, both players %s. %s.</span>' % (esc(band(data)), esc(engine_name(data)))]) +
            footer(data))
    return page(CARD_W, CARD_H, body)


def answer(data, trap, total):
    route, hook, plies = catch(trap)
    mistake = trap.top
    move = chess.Move.from_uci(mistake["uci"])
    us = side_name(trap.color)
    rows = score_rows(trap.sans + [mistake["san"] + "?"] + trap.punish[:plies])
    split = len(score_rows(trap.sans + [mistake["san"]]))
    mistake_txt = notation(trap.mistake_text() + "?")
    body = (card_frame(data, trap, total, True) + big_number(percent(mistake["our_score"])) +
            head_text("%s\u2019s real score<br>after <span class=\"mono\" style=\"font-size:.86em;font-weight:600;"
                      "white-space:nowrap\">%s</span>" % (us, mistake_txt),
                      "%s." % esc(title_of(trap))) +
            '<div class="abs" style="left:%dpx;top:%dpx">%s</div>'
            % (BX, BY, board_svg(trap.after, SQ, catch_=(route, hook), trail=move, seed=trap.number * 7 + 3, uid="a")) +
            score_block(rows, highlight_from=split) +
            caption(['<span style="font-weight:600">Best defence %s</span> <span class="faded">(Stockfish %s)</span>'
                     % (notation(trap.best_text()), esc(pawns(trap.record["best_cp"]))),
                     '<span class="faded">After %s %s \u00b7 n = %s Lichess games, %s</span>'
                     % (mistake_txt, esc(pawns(mistake["our_cp"])), thousands(mistake["games"]), esc(band(data)))]) +
            footer(data))
    return page(CARD_W, CARD_H, body)


# ---------------------------------------------------------------- X

def profile():
    """Avatar: the board device on its own. A red line drops from the top of
    the frame into a hook whose bend holds a knight, on water. Built to read
    inside X's circle crop at 48 px."""
    size, sq = 800, 430
    tx, ty = 404, 436                       # where the caught piece sits
    bend = 0.47
    eye_y = 128
    shank = (ty + sq * 0.5 - sq * bend - eye_y) / sq
    ex = tx - sq * bend
    knight = piece_svg("wN", tx - sq * 0.5, ty - sq * 0.5, sq, ink=WATER, paper=PAPER)
    body = f"""<svg class="abs" style="left:0;top:0" width="{size}" height="{size}">
{knight}
<path d="M{ex:.1f} -20 L{ex:.1f} {eye_y + 8:.1f}" stroke="{HOOK}" stroke-width="{sq * 0.075:.1f}" stroke-linecap="round"/>
{hook_shape(ex, eye_y, sq, HOOK, WATER, sq * 0.035, shank=shank, bend=bend, point=shank - 0.36, weight=0.135, eye=0.07)}
</svg>"""
    return page(size, size, body, bg=WATER, fg=PAPER)


def banner(data, traps):
    trap = pick(traps, "Bishop's Opening: the queen on h5")
    route, hook, _ = catch(trap)
    sq = 47
    board = board_svg(trap.after, sq, catch_=(route, hook), trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=16, seed=19 * 7 + 3, uid="bn")
    body = f"""
{lockup(64, 46, 30)}
<div class="abs serif" style="left:60px;top:132px;font-size:62px;line-height:1.08;letter-spacing:-0.02em">Stockfish finds the best move.<br>We find the one they miss.</div>
<div class="abs mono faded" style="left:340px;top:380px;font-size:16px;line-height:1.65;white-space:nowrap">Opening traps that real {esc(band(data))} players fall for,<br>found in {thousands(data.get('sample_games') or 0)} Lichess games, checked by {esc(engine_name(data))}.</div>
<div class="abs" style="left:1052px;top:52px">{board}</div>
"""
    return page(1500, 500, body)


# ---------------------------------------------------------------- store

def pick(traps, name):
    for trap in traps:
        if trap.name == name:
            return trap
    return traps[0]


def plate(board, pad_x, pad_top, pad_bottom):
    """A paper plate (flat, square-cornered) carrying a diagram on water."""
    return ('<div style="background:%s;padding:%dpx %dpx %dpx %dpx">%s</div>'
            % (PAPER, pad_top, pad_x, pad_bottom, pad_x, board))


def specs(data, traps):
    return [("%d" % len(traps), "traps, each checked by %s" % engine_name(data)),
            (thousands(data.get("sample_games") or 0), "real Lichess games"),
            (band(data), "rating band of both players"),
            ("PDF", "guide, drills, answer key and PGN")]


def thumbnail(data, traps):
    trap = pick(traps, "Bishop's Opening: the queen on h5")
    route, hook, _ = catch(trap)
    sq = 62
    board = board_svg(trap.after, sq, catch_=(route, hook), trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=19, coord_color=FADED, seed=19 * 7 + 3, uid="th")
    lines = ["%d traps" % len(traps), "%s Lichess games" % thousands(data.get("sample_games") or 0),
             "Both players %s" % band(data), "Checked by %s" % engine_name(data), "PDF, drills, PGN"]
    rows = "".join('<div style="padding:13px 0;border-top:1px solid %s">%s</div>' % (WATER_FADED, esc(t)) for t in lines)
    body = f"""
{lockup(72, 58, 48, color=PAPER)}
<div class="abs num" style="left:62px;top:178px;font-size:172px;line-height:.9;color:{PAPER};letter-spacing:-0.03em">1.e4 e5<br>Traps</div>
<div class="abs serif" style="left:72px;top:500px;font-size:48px;color:{PAPER}">for White</div>
<div class="abs mono" style="left:72px;top:660px;width:330px;white-space:nowrap;font-size:19px;line-height:1.35;color:{PAPER}">{rows}</div>
<div class="abs" style="left:512px;top:534px">{plate(board, 60, 36, 58)}</div>
"""
    return page(1200, 1200, body, bg=WATER, fg=PAPER, faded=WATER_FADED)


def cover_hero(data, traps):
    """Plate I: the pack as a catalogue plate, on water."""
    trap = pick(traps, "Traxler: the greedy knight")
    route, hook, _ = catch(trap)
    sq = 78
    board = board_svg(trap.after, sq, catch_=(route, hook), trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=17, seed=3 * 7 + 3, uid="c1")
    cap = ('<div class="mono" style="font-size:17px;line-height:1.5;margin-top:58px;color:%s">'
           'Plate %d. %s, after %s<br><span style="color:%s">White scores %s%% in %s games. Best defence %s.</span></div>'
           % (INK, trap.number, esc(trap.name), notation(trap.mistake_text() + "?"), FADED,
              percent(trap.top["our_score"]), thousands(trap.top["games"]), notation(trap.best_text())))
    rows = "".join('<div style="display:grid;grid-template-columns:150px auto;padding:9px 0"><span style="color:%s">%s</span>'
                   '<span style="color:%s">%s</span></div>' % (PAPER, esc(v), WATER_FADED, esc(k))
                   for v, k in specs(data, traps))
    body = f"""
{lockup(80, 62, 44, color=PAPER)}
<div class="abs num" style="left:72px;top:188px;font-size:150px;line-height:.92;color:{PAPER};letter-spacing:-0.03em">1.e4 e5<br>Traps</div>
<div class="abs serif" style="left:80px;top:482px;font-size:44px;color:{PAPER}">for White</div>
<div class="abs mono" style="left:80px;top:620px;width:620px;font-size:17px;line-height:1.4">{rows}</div>
<div class="abs" style="left:826px;top:0px;right:0;height:900px;background:{PAPER}"></div>
<div class="abs" style="left:892px;top:70px">{board}{cap}</div>
"""
    return page(1600, 900, body, bg=WATER, fg=PAPER, faded=WATER_FADED)


def cover_inside(data, traps):
    """The catalogue: every trap in the pack as a numbered specimen plate."""
    sq = 20
    cells = []
    for trap in traps:
        route, hook, _ = catch(trap)
        board = board_svg(trap.after, sq, catch_=(route, hook), coords=False, seed=trap.number * 7 + 3,
                          uid="ci%d" % trap.number, hatch=3.3)
        cells.append('<div><div style="padding:3px">%s</div>'
                     '<div class="mono" style="font-size:13px;line-height:1.4;margin-top:13px;white-space:nowrap;letter-spacing:-0.02em">'
                     '<span style="font-weight:600">%02d</span>&nbsp;%s<br><span class="faded">%s%% bite</span></div></div>'
                     % (board, trap.number, esc(opening_of(trap)), percent(trap.record["error_share"])))
    cells.append('<div class="txt" style="font-size:13px;line-height:1.45;padding-top:4px">Each board shows the position '
                 'after the most common mistake. The red line is the punishment. The hook marks what it catches.</div>')
    body = f"""
{lockup(64, 44, 32)}
<div class="abs serif" style="left:437px;top:54px;font-size:32px;line-height:1">{len(traps)} traps that {esc(band(data))} players really fall for</div>
<div class="abs mono faded" style="right:64px;top:64px;font-size:13px">Contents</div>
<div class="abs" style="left:64px;top:144px;width:1472px;display:grid;grid-template-columns:repeat(8, 166px);justify-content:space-between;row-gap:30px">{"".join(cells)}</div>
"""
    return page(1600, 900, body)


def cover_method(data, traps):
    """Anatomy of a trap: one plate with a numbered key, as in a field guide."""
    trap = pick(traps, "Bishop's Opening: the queen on h5")
    route, hook, plies = catch(trap)
    sq = 86
    bx, by = 112, 92
    last = trap.board.peek()
    mistake = chess.Move.from_uci(trap.top["uci"])
    best = trap.board.parse_san(trap.record["best_reply_san"]) if trap.record["best_reply_san"] else None
    punish = " ".join(trap.punish_text().split()[:plies])
    notes = [
        (last.to_square, "The bait", "%s. Every move White plays in the pack stays within half a pawn of %s's best."
         % (notation(trap.line_text().split()[-1]), esc(engine_name(data).split()[0]))),
        (mistake.to_square, "The bite", "%s, played in %s%% of %s games. In all, %s%% of players went wrong here."
         % (notation(trap.mistake_text() + "?"), percent(trap.top["share"]), thousands(trap.record["games"]),
            percent(trap.record["error_share"]))),
        (hook, "The hook", "%s. White then scored %s%% in %s real games."
         % (notation(punish), percent(trap.top["our_score"]), thousands(trap.top["games"]))),
    ]
    if best is not None:
        notes.append((best.to_square, "The escape", "%s holds the balance (%s %s)."
                      % (notation(trap.best_text()), esc(engine_name(data).split()[0]), esc(pawns(trap.record["best_cp"])))))
    keys, blocks = [], []
    for index, (square, label, text) in enumerate(notes):
        x, y = square_xy(square, sq)
        kx, ky = x + sq * 0.17, y + sq * 0.17
        if square == hook:   # the hook fills its square: key it from outside the frame
            file = chess.square_file(square)
            kx = 8 * sq + sq * 0.42 if file >= 4 else -sq * 0.62
            ky = y + sq * 0.5
        keys.append('<circle cx="%.1f" cy="%.1f" r="15" fill="%s" stroke="%s" stroke-width="3"/>'
                    '<text x="%.1f" y="%.1f" font-family="Martian Mono" font-weight="600" font-size="17" fill="%s" '
                    'text-anchor="middle">%d</text>' % (kx, ky, INK, PAPER, kx, ky + 6, PAPER, index + 1))
        blocks.append('<div style="display:grid;grid-template-columns:52px auto;margin-bottom:34px">'
                      '<div class="mono" style="font-size:17px;font-weight:600;padding-top:9px">%d</div><div>'
                      '<div class="serif" style="font-size:32px;line-height:1">%s</div>'
                      '<div class="mono" style="font-size:17px;line-height:1.55;margin-top:12px">%s</div></div></div>'
                      % (index + 1, label, text))
    board = board_svg(trap.after, sq, catch_=(route, hook), trail=mistake, coords=True, coord_size=17,
                      seed=19 * 7 + 3, uid="c3")
    board = board[:-len("</svg>")] + "".join(keys) + "</svg>"
    body = f"""
<div class="abs" style="left:{bx}px;top:{by}px">{board}</div>
<div class="abs mono faded" style="left:{bx}px;top:{by + 8 * sq + 54}px;font-size:17px">Plate {trap.number}. {esc(trap.name)}.</div>
{lockup(940, 44, 32)}
<div class="abs mono faded" style="right:64px;top:62px;font-size:17px">Anatomy of a trap</div>
<div class="abs" style="left:940px;top:170px;width:600px">{"".join(blocks)}</div>
"""
    return page(1600, 900, body)


# ---------------------------------------------------------------- contact sheet

def contact_sheet(out):
    """Everything at reduced size on one paper sheet, for review."""
    out = pathlib.Path(out)
    cards = sorted((out / "cards").glob("trap-*.png"), key=lambda p: (p.stem[:7], p.stem.endswith("answer")))
    def img(path, w, h, label):
        return ('<figure style="margin:0"><img src="file://%s" style="width:%dpx;height:%dpx;display:block;'
                'outline:1px solid #d6d1c4"><figcaption class="mono faded" style="font-size:11px;margin-top:6px">%s</figcaption></figure>'
                % (path.resolve(), w, h, esc(label)))
    pairs = "".join(img(p, 144, 180, p.stem) for p in cards)
    body = f"""
<div class="abs" style="left:40px;top:28px">{lockup(0, 0, 26).replace('class="abs"', 'class="abs" data-x')}</div>
<div class="abs mono faded" style="right:40px;top:40px;font-size:12px">Route A, Line &amp; Hook · studio-v3 contact sheet</div>
<div class="abs" style="left:40px;top:100px;width:1900px;display:grid;grid-template-columns:repeat(12, 144px);gap:18px 14px">{pairs}</div>
<div class="abs" style="left:40px;top:1030px;display:flex;gap:28px;align-items:flex-start">
  {img(out / "x" / "profile.png", 200, 200, "x/profile 800")}
  <div style="width:60px">{img(out / "x" / "profile.png", 48, 48, "48 px").replace('outline:1px solid #d6d1c4', 'clip-path:circle(50%)')}</div>
  {img(out / "x" / "banner.png", 750, 250, "x/banner 1500x500")}
  {img(out / "store" / "thumbnail.png", 250, 250, "store/thumbnail 1200")}
</div>
<div class="abs" style="left:40px;top:1345px;display:flex;gap:28px">
  {img(out / "store" / "cover-1.png", 600, 338, "store/cover-1")}
  {img(out / "store" / "cover-2.png", 600, 338, "store/cover-2")}
  {img(out / "store" / "cover-3.png", 600, 338, "store/cover-3")}
</div>
"""
    return page(1980, 1740, body)


# ---------------------------------------------------------------- rendering

def render(jobs):
    """jobs: list of (html, out_path, width, height)."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="trickfish-studio-"))
    try:
        manifest = []
        for index, (markup, out, width, height) in enumerate(jobs):
            path = work / ("frame-%03d.html" % index)
            path.write_text(markup, encoding="utf-8")
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            manifest.append({"html": str(path), "out": str(pathlib.Path(out).resolve()), "width": width,
                             "height": height, "scale": 2})
        (work / "manifest.json").write_text(json.dumps(manifest))
        subprocess.run(["node", str(HERE / "render.mjs"), str(work / "manifest.json")], check=True,
                       cwd=str(HERE))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    import argparse

    from trickfish.trappack_render import load

    parser = argparse.ArgumentParser(description="Render Trickfish brand visuals with Chromium")
    parser.add_argument("traps")
    parser.add_argument("--notes")
    parser.add_argument("--output", required=True)
    parser.add_argument("--only", help="comma list: cards,x,store,sheet")
    parser.add_argument("--traps-only", help="comma list of trap numbers to render (cards only)")
    args = parser.parse_args(argv)
    data, meta, traps = load(args.traps, args.notes)
    data = dict(data, title=meta.get("title", ""))
    out = pathlib.Path(args.output)
    only = set((args.only or "cards,x,store,sheet").split(","))
    pick = {int(n) for n in args.traps_only.split(",")} if args.traps_only else None
    jobs = []
    if "cards" in only:
        for trap in traps:
            if pick and trap.number not in pick:
                continue
            jobs.append((question(data, trap, len(traps)), out / "cards" / ("trap-%02d.png" % trap.number), CARD_W, CARD_H))
            jobs.append((answer(data, trap, len(traps)), out / "cards" / ("trap-%02d-answer.png" % trap.number), CARD_W, CARD_H))
    if "x" in only:
        jobs.append((profile(), out / "x" / "profile.png", 800, 800))
        jobs.append((banner(data, traps), out / "x" / "banner.png", 1500, 500))
    if "store" in only:
        jobs.append((thumbnail(data, traps), out / "store" / "thumbnail.png", 1200, 1200))
        jobs.append((cover_hero(data, traps), out / "store" / "cover-1.png", 1600, 900))
        jobs.append((cover_inside(data, traps), out / "store" / "cover-2.png", 1600, 900))
        jobs.append((cover_method(data, traps), out / "store" / "cover-3.png", 1600, 900))
    if jobs:
        render(jobs)
    if "sheet" in only:
        render([(contact_sheet(out), out / "contact-sheet.png", 1980, 1740)])
    print("rendered %d frames into %s" % (len(jobs), out))


if __name__ == "__main__":
    main()
