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

# Card type scale: exactly three sizes per card. Nothing that matters is set
# below M (32 px, about 12 px on a phone).
L, M, S = 226, 32, 19


# ---------------------------------------------------------------- art direction
#
# Which piece's path the red line follows, and where the hook lands, is an
# editorial decision: the hook goes on the piece that is actually won, or on
# the piece the punishing move targets. Never on an empty square.
#
# Keys are the trap's move line (Trap.line_text()). Each value is
# (strokes, hook square, plies of the punishment to print).
# A stroke is a list of squares, drawn as one hand-laid line. Earlier
# strokes are drawn lighter and end in a split-shot (used for discoveries,
# where one piece moves out of another's way). "~sq:dx,dy" is a waypoint
# (offset in squares) that bends a line around a piece without marking a
# stop. When the hook square is not the last square of the last stroke, the
# final leg is the line of attack from that square to its target.
# Traps not listed here fall back to the automatic rule in `catch()`.
CATCH = {
    # 1  Fried Liver: 8.Bxd5 wins the pinned knight
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 d5 5.exd5 Nxd5 6.Nxf7 Kxf7 7.Qf3+": ([["c4", "d5"]], "d5", 1),
    # 2  10.Qxd5+ wins the queen
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 d5 5.exd5 Nxd5 6.Nxf7 Kxf7 7.Qf3+ Ke6 8.Nc3 Nd4 9.Bxd5+":
        ([["f3", "d5"]], "d5", 1),
    # 3  Traxler: the queen tour bows round g7 (that pawn is still on g7 in the diagram), runs
    #    along the back rank g8-f8 to the e8/f8 boundary and drops onto the black queen on e7,
    #    the piece forced to e8 (11...Qe8) and traded off by 12.Qxe8+
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 Bc5 5.Nxf7 Bxf2+ 6.Kf1 Qe7 7.Nxh8":
        ([["d1", "h5", "g6", "~g7:-0.5,0", "g8", "~f8:-0.5,0"]], "e7", 9),
    # 4  7.Kxf2 takes the bishop
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 Bc5 5.Bxf7+ Kf8 6.Bb3": ([["e1", "f2"]], "f2", 1),
    # 5  6.Qd5 (f7 and e4), 8.Qxe4
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.d4 Nxe4 5.dxe5": ([["d1", "d5", "e4"]], "e4", 5),
    # 6  9.Qb3, 11.Qxb7
    "1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 4.c3 d6 5.d4 exd4 6.cxd4 Bb4+ 7.Bd2 Bxd2+ 8.Nbxd2": ([["d1", "b3", "b7"]], "b7", 5),
    # 7  discovery: 6.Nxc6 clears d4, then 7.Bxc5
    "1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.Nxd4 Bc5 5.Be3": ([["d4", "c6"], ["e3", "c5"]], "c5", 3),
    # 8  7.g4 hits the knight (it survives after 7...Qh4, so this is a target, not a capture)
    "1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.Nxd4 Nxd4 5.Qxd4 Nf6 6.e5": ([["g2", "g4"]], "h5", 2),
    # 9  8.g4 f6 9.gxh5 wins it
    "1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.Nxd4 Nxd4 5.Qxd4 Nf6 6.e5 Qe7 7.Be3": ([["g2", "g4", "h5"]], "h5", 3),
    # 10 8.Qd5, 9.Qxa8
    "1.e4 e5 2.Nf3 Nc6 3.d4 exd4 4.Nxd4 Nxd4 5.Qxd4 Nf6 6.e5 Ng8 7.Bc4": ([["d4", "d5", "a8"]], "a8", 3),
    # 11 6.Nxe5
    "1.e4 e5 2.Nf3 Nc6 3.d4 d6 4.dxe5 dxe5 5.Qxd8+": ([["f3", "e5"]], "e5", 1),
    # 12 after the queen trade, 8.Nxe5 and 10.Nxc6
    "1.e4 e5 2.Nf3 Nc6 3.Bb5 d6 4.Bxc6+ bxc6 5.d4 Nf6 6.dxe5": ([["f3", "e5", "c6"]], "c6", 7),
    # 13 the d-pawn marches and takes the pinned knight: 10.dxc6
    "1.e4 e5 2.Nf3 Nc6 3.Bb5 Bc5 4.O-O d6 5.c3": ([["d2", "d4", "d5", "c6"]], "c6", 9),
    # 14 same pin, but drawn as the threat 7.d5 (a different picture from #13)
    "1.e4 e5 2.Nf3 Nc6 3.Bb5 Nf6 4.O-O Bc5 5.c3": ([["d2", "d4", "d5"]], "c6", 3),
    # 15 6.d3 hits the e4 knight; when it moves, 7.Rxe5+ comes with check
    "1.e4 e5 2.Nf3 Nc6 3.Bb5 Nf6 4.O-O Nxe4 5.Re1": ([["d2", "d3"]], "e4", 3),
    # 16 7.Qxg7 (the pawn actually taken; the rook is saved by 7...Qf6)
    "1.e4 e5 2.Nf3 Nc6 3.Nc3 Bc5 4.Nxe5 Nxe5 5.d4 Bxd4 6.Qxd4": ([["d4", "g7"]], "g7", 2),
    # 17 6.Nc6+ uncovers check and hits the queen on d8
    "1.e4 e5 2.Nf3 Nf6 3.Nxe5 Nxe4 4.Qe2 d5 5.d3": ([["e5", "c6"]], "d8", 3),
    # 18 after the queen trade, 6.Nxe5 and f7 is the next target
    "1.e4 e5 2.Nf3 Nf6 3.d4 d6 4.dxe5": ([["f3", "e5"]], "f7", 3),
    # 19 4.Qxe5+ and 5.Qxh8
    "1.e4 e5 2.Bc4 Bc5 3.Qh5": ([["h5", "e5", "h8"]], "h8", 3),
    # 20 5.Qxe5+ forces the queen trade a pawn up
    "1.e4 e5 2.Bc4 Bc5 3.Qh5 Qf6 4.Nf3": ([["h5", "e5"]], "e5", 3),
    # 21 5.Bxf7+
    "1.e4 e5 2.Bc4 Bc5 3.Nf3 Nf6 4.Nxe5": ([["c4", "f7"]], "f7", 1),
    # 22 4.fxe5, then the e-pawn arrives on e5 and sends the f6 knight home
    "1.e4 e5 2.Nc3 Nf6 3.f4": ([["f4", "e5"], ["e4", "e5"]], "f6", 6),
    # 23 5.Qe2 breaks the pin, so the e5 pawn now hits the f6 knight
    "1.e4 e5 2.Nc3 Nf6 3.f4 exf4 4.e5": ([["d1", "e2"], ["e5", "f6"]], "f6", 2),
}


def _point(token):
    if token.startswith("~"):
        name, offset = token[1:].split(":")
        dx, dy = (float(v) for v in offset.split(","))
        return (chess.parse_square(name), dx, dy, False)
    return (chess.parse_square(token), 0.0, 0.0, True)


def catch(trap):
    """Return (strokes, hook square, plies of the punishment to print).

    strokes: list of strokes; a stroke is a list of (square, dx, dy, is_stop)."""
    key = trap.line_text()
    if key in CATCH:
        strokes, hook, plies = CATCH[key]
        return [[_point(t) for t in stroke] for stroke in strokes], chess.parse_square(hook), plies
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
    return [[(s, 0.0, 0.0, True) for s in route]], route[-1], plies


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
.num { font-family: 'Young Serif'; font-weight: 400; line-height: 1; letter-spacing: -0.03em;
       font-feature-settings: 'kern' 1, 'lnum' 1; }
.serif { font-family: 'Young Serif'; font-weight: 400; letter-spacing: -0.01em; font-feature-settings: 'lnum' 1; }
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
    return html.escape(str(text), quote=False).replace("'", "’")


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


def engine_name(data):
    return str(data.get("engine", "Stockfish 16"))


SMALL_SAMPLE = 50


def wrong_share(trap):
    """Share of games at the position in which the side to move chose a reply
    that costs at least 1.2 pawns (Trap.mistakes) and after which we really
    scored at least 50%. Mistakes that did not pay off in practice are left out."""
    games = trap.record["games"] or 1
    return sum(r["games"] for r in trap.mistakes if r["our_score"] >= 0.5) / games


def points(score, games):
    """Points from `games` at `score` per game, as '47' or '42½'."""
    halves = round(score * games * 2)
    return "%d%s" % (halves // 2, "½" if halves % 2 else "")


def plain_of(trap):
    """One sentence that names the mistake in plain words: notes.json 'plain',
    or the first sentence of the idea."""
    text = getattr(trap, "plain", "") or ""
    if not text and trap.idea:
        text = re.split(r"(?<=[.!])\s", trap.idea, maxsplit=1)[0]
    return text


_SAN = re.compile(r"(?<![\w…])(\d+(?:\.|…))?((?:[KQRBN][a-h]?[1-8]?x?[a-h][1-8]|[a-h]x[a-h][1-8]|[a-h][1-8])"
                  r"(?:=[QRBN])?|O-O(?:-O)?)([+#]?[?!]*)(?![\w])")


def _full_move(token):
    """A full move has a move number or a piece letter (or is castling); a bare
    square ("f7") or a bare pawn capture stays in the text face."""
    return bool(re.match(r"\d|[KQRBN]|O-O", token))


def prose(text, weight=400):
    """Escape running text; set full moves in the mono with figurines, each as
    one unbreakable unit (move number kept with its move)."""
    text = ellipsis(text)
    out, last = [], 0
    for match in _SAN.finditer(text):
        if not _full_move(match.group(0)):
            continue
        out.append(esc(text[last:match.start()]))
        out.append('<span class="mono" style="font-weight:%d;white-space:nowrap">%s</span>'
                   % (weight, notation(match.group(0))))
        last = match.end()
    out.append(esc(text[last:]))
    return "".join(out)


# ---------------------------------------------------------------- pieces

_PIECES = {}


def piece_inner(code):
    if code not in _PIECES:
        text = (HERE / "pieces" / ("%s.svg" % code)).read_text(encoding="utf-8")
        _PIECES[code] = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S).group(1)
    return _PIECES[code]


def piece_svg(code, x, y, size, ink=INK, paper=PAPER, halo=0.0):
    """A Merida piece. `halo` (in 50-unit piece space) draws a thin paper edge
    under black pieces, as printed diagrams do, so they hold on hatching."""
    inner = piece_inner(code)
    if halo:
        inner = inner.replace('fill="#1f1a17"', 'fill="#1f1a17" stroke="#fff" stroke-width="%.2f" '
                              'stroke-linejoin="round" paint-order="stroke"' % halo, 1)
    inner = inner.replace("#1f1a17", ink).replace("#fff", paper)
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

def _bezier(points_, t):
    while len(points_) > 1:
        points_ = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(points_, points_[1:])]
    return points_[0]


def _line_samples(stops, sq, rng):
    """Centre-line of a hand-laid line through `stops` (bowing a little between them)."""
    samples = []
    for index, (a, b) in enumerate(zip(stops, stops[1:])):
        length = math.dist(a, b)
        nx, ny = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length) if length else (0, 0)
        bow = rng.uniform(0.03, 0.06) * length * rng.choice((-1, 1))
        mid = ((a[0] + b[0]) / 2 + nx * bow, (a[1] + b[1]) / 2 + ny * bow)
        steps = max(10, int(length / (sq * 0.03)))
        last = index == len(stops) - 2
        for step in range(steps + (1 if last else 0)):
            samples.append(_bezier([a, mid, b], step / steps))
    return samples


def _stroke_svg(pts, sq, seed, color, halo, width, halo_width):
    rng = random.Random(seed * 31 + 7)
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) or 1
    phase = [rng.uniform(0, 1) for _ in range(2)]
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
    return ('<g fill="none" stroke-linecap="round" stroke="%s">%s</g>' % (halo, "".join(under)),
            '<g fill="none" stroke-linecap="round" stroke="%s">%s</g>' % (color, "".join(over)))


def hand_line(stops, sq, seed, color=HOOK, halo=PAPER, width=0.11, halo_width=0.045, clip=None):
    """A red line drawn as a nib would: width swells and thins, the path bows a
    little between stops, and a paper knockout keeps it legible over hatching.
    `clip` = (x0, y0, x1, y1): the line stops where it first enters that box."""
    pts = _line_samples(stops, sq, random.Random(seed))
    if clip:
        x0, y0, x1, y1 = clip
        for index, (x, y) in enumerate(pts):
            if x0 <= x <= x1 and y0 <= y <= y1:
                pts = pts[:index + 1]
                break
    under, over = _stroke_svg(pts, sq, seed, color, halo, width, halo_width)
    return under + over, pts


def hook_glyph(ex, ey, u, color=HOOK, halo=None, halo_width=0.0, weight=0.085, bend=0.33, shank=0.48, rise=0.26):
    """An engraved J-hook hanging from its eye. (ex, ey) is the top of the eye;
    u is the unit (one diagram square on a board). Shank, bend and point are
    one stroke; the point and its barb are one filled shape, so there is no
    seam between them. Returns (svg, centre-line points)."""
    w = u * weight
    r = u * 0.05
    by = ey + u * shank                  # centre of the bend
    br = u * bend
    px = ex + 2 * br
    tip = by - u * rise
    body = "M%.2f %.2f L%.2f %.2f A%.2f %.2f 0 0 0 %.2f %.2f" % (ex, ey + 2 * r, ex, by, br, br, px, by)
    inner_t = (u * 0.13) / max(by - tip, 1e-6)
    inner_x = px - w / 2 + (1 - inner_t) * 0.55 * w
    barb = [(px + w / 2, by), (px + w * 0.05, tip), (px - w * 1.55, tip + u * 0.2), (inner_x, tip + u * 0.13),
            (px - w / 2, by)]
    point = "M" + " L".join("%.2f %.2f" % p for p in barb) + " Z"

    def draw(colour, extra):
        return ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="none" stroke="%s" stroke-width="%.2f"/>'
                '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
                '<path d="%s" fill="%s" stroke="%s" stroke-width="%.2f" stroke-linejoin="round"/>'
                % (ex, ey + r, r, colour, w * 0.62 + extra, body, colour, w + extra, point, colour, colour,
                   extra or 0.01))

    svg = (draw(halo, 2 * halo_width) if halo else "") + draw(color, 0)
    line = [(ex, ey + 2 * r + (by - ey - 2 * r) * k / 6) for k in range(7)]
    line += [(ex + br - br * math.cos(math.pi * k / 10), by + br * math.sin(math.pi * k / 10)) for k in range(11)]
    line += [(px, by - (by - tip) * k / 4) for k in range(5)]
    return svg, line


# ---------------------------------------------------------------- the diagram

def square_xy(square, sq):
    return chess.square_file(square) * sq, (7 - chess.square_rank(square)) * sq


def centre(square, sq):
    x, y = square_xy(square, sq)
    return x + sq / 2, y + sq / 2


HOOK_GEOMETRY = dict(eye_x=0.17, eye_y=0.12, piece=0.66, piece_y=0.555)


def draw_catch(catch_, sq, seed, color=HOOK, paper=PAPER):
    """The red line(s) and the hook. The hook hangs inside the catch square,
    eye on its top edge, tied up by a short snell; the caught piece sits in the
    bend. The last leg of the line runs along the real direction of the last
    move (or line of attack) and stops where it meets the hook, so nothing red
    crosses the caught piece.

    Drop mode: when the final stroke ends on a waypoint ("~sq:dx,dy") rather
    than a stop, the line runs to that waypoint and then drops vertically into
    the hook's eye, which hangs from that x. Used where the real path runs past
    the catch square (#3: along the back rank, then down onto the queen).
    Returns (line svg, hook svg, red points, x of the caught piece's centre)."""
    strokes, hook = catch_[0], catch_[1]
    x0, y0 = square_xy(hook, sq)
    hx, hy = x0 + sq / 2, y0 + sq / 2
    clip = (x0 + sq * 0.11, y0 + sq * 0.03, x0 + sq * 0.89, y0 + sq * 0.97)
    drop = strokes[-1][-1][3] is False
    ex, ey = x0 + sq * HOOK_GEOMETRY["eye_x"], y0 + sq * HOOK_GEOMETRY["eye_y"]
    mirror = False
    if drop:
        square, dx, dy, _ = strokes[-1][-1]
        ex = centre(square, sq)[0] + dx * sq
        mirror = ex > hx
    halos, inks, red, shots = [], [], [], []
    for index, stroke in enumerate(strokes):
        final = index == len(strokes) - 1
        stops = []
        for square, dx, dy, _ in stroke:
            cx, cy = centre(square, sq)
            stops.append((cx + dx * sq, cy + dy * sq))
        if final and drop:
            stops.append((ex, ey + 1))
        elif final:
            if stroke[-1][0] == hook:
                stops = stops[:-1]
            stops.append((hx, hy))
        svg, pts = hand_line(stops, sq, seed + index * 13, color, paper, width=0.11 if final else 0.085,
                             clip=clip if final and not drop else None)
        halos.append(svg)
        red += pts
        marks = stroke[1:] if final else stroke[1:]
        for square, dx, dy, is_stop in marks:
            if is_stop and square != hook:
                shots.append(centre(square, sq))
    for x, y in shots:
        inks.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/><circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                    % (x, y, sq * 0.115, paper, x, y, sq * 0.075, color))
        red.append((x, y))
    hook_svg, hook_line = hook_glyph(ex, ey, sq, color, paper, sq * 0.035)
    bend = 0.33 * sq
    if mirror:
        hook_svg = '<g transform="translate(%.2f 0) scale(-1 1) translate(%.2f 0)">%s</g>' % (ex, -ex, hook_svg)
        hook_line = [(2 * ex - x, y) for x, y in hook_line]
    piece_cx = ex - bend if mirror else ex + bend
    snell = ""
    if not drop:
        snell = ('<path d="M%.2f %.2f L%.2f %.2f" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
                 % (ex, y0 + sq * 0.035, ex, ey + 1, color, sq * 0.06))
        snell = snell.replace('stroke="%s"' % color, 'stroke="%s"' % paper).replace(
            'stroke-width="%.2f"' % (sq * 0.06), 'stroke-width="%.2f"' % (sq * 0.13)) + snell
    red += hook_line
    return "".join(halos) + "".join(inks), snell + hook_svg, red, piece_cx


def board_svg(board, sq, *, catch_=None, trail=None, coords=True, coord_size=S, seed=1, uid="d",
              ink=INK, paper=PAPER, line_color=HOOK, coord_color=FADED, frame=True, hatch=None):
    """A printed book diagram. `catch_` = (strokes, hook square) from catch()
    draws the red line and the hook; `trail` = chess.Move draws the opponent's
    move as an ink dotted wake that keeps clear of the red."""
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
    lines, hook_svg, red, caught = "", "", [], None
    if catch_ is not None:
        lines, hook_svg, red, piece_cx = draw_catch(catch_, sq, seed, line_color, paper)
        caught = catch_[1]
    if trail is not None:
        out.append(_trail(trail, sq, ink, paper, red))
    halo = 1.5 if sq >= 40 else 0.0
    for square, p in board.piece_map().items():
        if square == caught:
            continue
        x, y = square_xy(square, sq)
        code = ("w" if p.color else "b") + p.symbol().upper()
        out.append(piece_svg(code, x, y, sq, ink, paper, halo if not p.color else 0.0))
    out.append(lines)
    if caught is not None:
        p = board.piece_at(caught)
        if p is not None:
            x, y = square_xy(caught, sq)
            size = sq * HOOK_GEOMETRY["piece"]
            code = ("w" if p.color else "b") + p.symbol().upper()
            out.append(piece_svg(code, piece_cx - size / 2, y + sq * HOOK_GEOMETRY["piece_y"] - size / 2, size, ink, paper,
                                 halo if not p.color else 0.0))
        out.append(hook_svg)
    if coords:
        gap = sq * 0.07 + max(2.0, sq * 0.05)
        for i in range(8):
            out.append('<text x="%.2f" y="%.2f" font-family="Martian Mono" font-size="%.2f" fill="%s" text-anchor="middle">%s</text>'
                       % (i * sq + sq / 2, n + gap + coord_size * 1.25, coord_size, coord_color, "abcdefgh"[i]))
            out.append('<text x="%.2f" y="%.2f" font-family="Martian Mono" font-size="%.2f" fill="%s" text-anchor="end">%d</text>'
                       % (-gap - coord_size * 0.55, i * sq + sq / 2 + coord_size * 0.36, coord_size, coord_color, 8 - i))
    out.append("</svg>")
    return "".join(out)


def _clearance(point, red):
    return min((math.dist(point, r) for r in red), default=1e9)


def _trail(move, sq, ink, paper, red=()):
    """The opponent's move as a dotted ink wake from an empty ring. Dots end
    0.25 sq before any red; the ring keeps 0.12 sq of paper from the line."""
    (ax, ay), (bx, by) = centre(move.from_square, sq), centre(move.to_square, sq)
    length = math.dist((ax, ay), (bx, by))
    ux, uy = (bx - ax) / length, (by - ay) / length
    red_half = sq * 0.11 / 2
    dots = []
    d = sq * 0.2
    while d < length - sq * 0.42:
        p = (ax + ux * d, ay + uy * d)
        if _clearance(p, red) >= sq * 0.25 + red_half:
            dots.append('<circle cx="%.2f" cy="%.2f" r="%.2f"/>' % (p[0], p[1], sq * 0.032))
        d += sq * 0.13
    ring_r = sq * 0.11
    need = ring_r + sq * 0.12 + red_half
    candidates = [(ax, ay)] + [(ax + sq * 0.24 * math.cos(a), ay + sq * 0.24 * math.sin(a))
                               for a in [k * math.pi / 4 for k in range(8)]]
    ring_at = next((c for c in candidates if _clearance(c, red) >= need), None)
    if ring_at is None:
        ring_at = max(candidates, key=lambda c: _clearance(c, red))
    ring = ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>'
            % (ring_at[0], ring_at[1], ring_r, paper, ink, sq * 0.028))
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
        out.append('<div class="%s" style="display:grid;grid-template-columns:3.6ch 6.6ch auto;font-weight:%d">'
                   '<span style="text-align:right;padding-right:.5ch">%s.</span><span>%s</span><span>%s</span></div>'
                   % ("faded" if faded else "", 600 if strong else 400, num, notation(white), black_html))
    out.append("</div>")
    return "".join(out)


def lockup(x, top, size, color=INK, hook=HOOK, drop=None):
    """Wordmark lockup: a red line dropping from the top edge into a hook,
    beside the name set in Young Serif."""
    u = size * 1.05
    drop = top if drop is None else drop
    glyph, _ = hook_glyph(u * 0.06, drop, u, hook, weight=0.1, bend=0.2, shank=0.62, rise=0.3)
    line = ('<svg class="abs" style="left:%.1fpx;top:0" width="%.1f" height="%.1f">'
            '<path d="M%.2f 0 L%.2f %.2f" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>%s</svg>'
            % (x, u, drop + u, u * 0.06, u * 0.06, drop + 1, hook, u * 0.062, glyph))
    word = ('<div class="abs serif" style="left:%.1fpx;top:%.1fpx;font-size:%dpx;line-height:1;color:%s">Trickfish</div>'
            % (x + u * 0.62, drop + u * 0.18, size, color))
    return line + word


# ---------------------------------------------------------------- cards (1080 x 1350)
#
# Grid: 64 px margins. A score column (52-288) and a main column (296-1016)
# that holds the diagram; the text block hangs from the c-file line (476).
# The score sheet starts level with rank 8 on a half-square pitch. On answer
# cards the plain-words note sits at the foot of the score column, level
# with the board's bottom edge. Everything that matters sits inside the
# centred 1080 x 1080 safe zone (y 135-1215) and is at least 28 px.
# Three sizes: L (the number), M (all text), S (score sheet, coordinates,
# trap number and footer, which are details for people who open the image).

CARD_W, CARD_H = 1080, 1350
NOTE_W = 220   # x 42-262: the score column up to the rank coordinates
SQ = 90
BX, BY = 296, 372
TEXT_X = BX + 2 * SQ
HERO_TOP = 136          # puts the top of the lining figures at y ~150, inside the safe zone


def card_frame(data, trap, total, answer):
    side = "Answer" if answer else "Trap"
    return (lockup(64, 58, M) +
            '<div class="abs mono faded" style="right:64px;top:%dpx;font-size:%dpx">%s %02d<span style="opacity:.6"> / %d</span></div>'
            % (80, S, side, trap.number, total))


# Young Serif metrics (fraction of the em, measured at 1000 px): where the top of
# a lining figure, the "%" and the "\u00bd" sit below the top of a line-height:1 box.
CAP_TOP = {"fig": 0.078, "%": 0.105, "\u00bd": 0.022}
SUPER = 0.42                     # superscript size, as a fraction of the hero
# Space between the last figure and the superscript, in hero ems, per last
# figure: calibrated by measuring the ink gap on every rendered card so the
# visible gap is ~10 px everywhere (the 2's tail and the 4's foot serif reach
# right; the 1 and the 7 leave air). "\u00bd" has a smaller left bearing than "%".
SUPER_KERN = {"0": 0.0155, "1": 0.014, "2": 0.023, "3": 0.015, "4": 0.023, "5": 0.013, "6": 0.016,
              "7": 0.033, "8": 0.015, "9": 0.0155}
HALF_EXTRA = 0.02


def big_number(value, size=L, color=None):
    """The hero lockup: lining Young Serif figures, plus a "%" or "\u00bd" set in
    the same face at 0.42 of the size, top-aligned to the figures' cap height,
    as financial print sets a superscript. Number and superscript are one unit
    (the one documented exception to the three-size rule)."""
    if value.endswith("\u00bd"):
        whole, sup = value[:-1], "\u00bd"
    elif value.endswith("%"):
        whole, sup = value[:-1], "%"
    else:
        whole, sup = value, ""
    small = round(size * SUPER)
    style = ";color:%s" % color if color else ""
    out = ('<div class="abs" style="left:52px;top:%dpx;display:flex;align-items:flex-start%s">'
           '<span class="num" style="font-size:%dpx;letter-spacing:-0.03em">%s</span>' % (HERO_TOP, style, size, esc(whole)))
    if sup:
        drop = CAP_TOP["fig"] * size - CAP_TOP[sup] * small
        kern = (SUPER_KERN.get(whole[-1:], 0.016) + (HALF_EXTRA if sup == "\u00bd" else 0)) * size
        out += ('<span class="num" style="font-size:%dpx;letter-spacing:0;margin:%.1fpx 0 0 %.1fpx">%s</span>'
                % (small, drop, kern, esc(sup)))
    return out + "</div>"


def head_text(first, second):
    return ('<div class="abs" style="left:%dpx;top:146px;width:%dpx">'
            '<div class="txt" style="font-size:%dpx;line-height:1.25">%s</div>'
            '<div class="serif" style="font-size:%dpx;line-height:1.2;margin-top:12px">%s</div></div>'
            % (TEXT_X, 1016 - TEXT_X, M, first, M, second))


def _note_lines(text, width=NOTE_W):
    """Rough line count for the margin note at size M (moves set in the wide mono)."""
    words, lines, used = ellipsis(text).split(), 1, 0
    for word in words:
        mono = bool(_SAN.search(word)) and _full_move(word)
        w = len(word) * (M * (0.66 if mono else 0.5)) + M * 0.27
        if used + w > width and used:
            lines, used = lines + 1, w
        else:
            used += w
    return lines


def score_block(rows, highlight_from=None, reserve=0):
    """The score sheet, from rank 8 down. If the margin note needs the space
    at the foot of the column, the earliest opening moves are left off."""
    pitch = SQ // 2
    room = (8 * SQ - reserve) // pitch
    if len(rows) > room:
        cut = len(rows) - room
        rows = rows[cut:]
        if highlight_from is not None:
            highlight_from -= cut
    return ('<div class="abs" style="left:46px;top:%dpx;width:242px">%s</div>'
            % (BY + 2, score_column(rows, S, pitch, highlight_from)))


NOTE_LAYOUT = """<script>
// Line-break the plain-words notes with real measurements: no line holds a
// single word unless it is the move (which leads the note); otherwise lines
// are as even as possible. render.mjs calls this after fonts load.
window.__layout = () => {
  for (const el of document.querySelectorAll('.note')) {
    const ws = [...el.querySelectorAll('.w')];
    const W = el.clientWidth;
    const probe = document.createElement('span'), p2 = document.createElement('span');
    probe.textContent = 'a a'; p2.textContent = 'aa';
    for (const q of [probe, p2]) { q.style.position = 'absolute'; q.style.whiteSpace = 'pre'; el.appendChild(q); }
    const sp = probe.getBoundingClientRect().width - p2.getBoundingClientRect().width;
    probe.remove(); p2.remove();
    const wd = ws.map(w => w.getBoundingClientRect().width);
    const mv = ws.map(w => !!w.querySelector('.mono'));
    const n = ws.length, best = Array(n + 1).fill(Infinity), from = Array(n + 1).fill(0);
    best[0] = 0;
    for (let j = 1; j <= n; j++) {
      let width = -sp;
      for (let i = j - 1; i >= 0; i--) {
        width += wd[i] + sp;
        if (width > W + 0.5 && j - i > 1) break;
        const single = j - i === 1 && !mv[i];
        const cost = best[i] + (single ? 1e6 : 0) + (j === n ? 0 : (W - width) ** 2);
        if (cost < best[j]) { best[j] = cost; from[j] = i; }
      }
    }
    const lines = []; for (let j = n; j > 0; j = from[j]) lines.unshift(ws.slice(from[j], j));
    el.style.whiteSpace = 'nowrap';
    el.innerHTML = lines.map(l => l.map(w => w.outerHTML).join(' ')).join('<br>');
  }
};
</script>"""


def margin_note(text):
    """The plain-words line, at the foot of the score column (x 46-260),
    bottom-aligned with the board. Each word is a span so NOTE_LAYOUT can set
    the line breaks from real measurements."""
    words = ellipsis(text).split()
    # a hyphenated word ("d-pawn") must not break at its hyphen: use U+2011
    words = [w if _full_move(w) else w.replace("-", "\u2011") for w in words]
    html_ = " ".join('<span class="w">%s</span>' % prose(w) for w in words)
    lines = _note_lines(text) + 1      # measured breaks run a line longer than the estimate at most
    height = round(lines * M * 1.2)
    return ('<div class="abs txt note" style="left:42px;bottom:%dpx;width:%dpx;font-size:%dpx;line-height:1.2">%s</div>'
            % (CARD_H - (BY + 8 * SQ) - 4, NOTE_W, M, html_)) + NOTE_LAYOUT, height + 34


def footer(data):
    """Outside the safe zone: the handle, and the pack the trap comes from."""
    title = data.get("title") or ""
    return ('<div class="abs mono faded" style="left:64px;right:64px;top:1262px;font-size:%dpx;display:flex;'
            'justify-content:space-between"><span>@trickfishchess</span><span>%s</span></div>'
            % (S, esc("From " + title) if title else ""))


def caption(lines):
    return ('<div class="abs txt" style="left:%dpx;top:%dpx;width:%dpx;font-size:%dpx;line-height:1.18">%s</div>'
            % (BX, BY + 8 * SQ + 44, 8 * SQ + 40, M, "<br>".join(lines)))


def source_line(data):
    return '<span class="faded">%s · Lichess, both players %s</span>' % (esc(engine_name(data)), esc(band(data)))


def move_html(text):
    return '<span class="mono" style="font-weight:500;white-space:nowrap">%s</span>' % notation(text)


def question(data, trap, total):
    mover = side_name(trap.board.turn)
    rows = score_rows(trap.sans, blank=True)
    body = (card_frame(data, trap, total, False) + big_number(percent(wrong_share(trap)) + "%") +
            head_text("of %s games at %s<br>go wrong here. <span style=\"font-weight:600\">%s to move.</span>"
                      % (thousands(trap.record["games"]), esc(band(data)), mover), "%s." % esc(opening_of(trap))) +
            '<div class="abs" style="left:%dpx;top:%dpx">%s</div>' % (BX, BY, board_svg(trap.board, SQ, uid="q")) +
            score_block(rows) +
            caption([source_line(data)]) +
            footer(data))
    return page(CARD_W, CARD_H, body)


def answer(data, trap, total):
    strokes, hook, plies = catch(trap)
    mistake = trap.top
    move = chess.Move.from_uci(mistake["uci"])
    us = side_name(trap.color)
    rows = score_rows(trap.sans + [mistake["san"] + "?"] + trap.punish[:plies])
    split = len(score_rows(trap.sans + [mistake["san"]]))
    played = move_html(trap.mistake_text() + "?")
    share, games = percent(mistake["share"]), mistake["games"]
    if games < SMALL_SAMPLE:
        scored = points(mistake["our_score"], games)
        hero = big_number(scored)
        first = ("%s scored %s points<br>from %d games after %s<br>(%s%% of %s)."
                 % (us, scored, games, played, share, thousands(trap.record["games"])))
    else:
        hero = big_number(percent(mistake["our_score"]) + "%")
        first = ("%s’s score after %s<br>(played in %s%% of %s games)."
                 % (us, played, share, thousands(trap.record["games"])))
    note, reserve = margin_note(plain_of(trap))
    body = (card_frame(data, trap, total, True) + hero +
            head_text(first, "%s." % esc(title_of(trap))) +
            '<div class="abs" style="left:%dpx;top:%dpx">%s</div>'
            % (BX, BY, board_svg(trap.after, SQ, catch_=(strokes, hook), trail=move, seed=trap.number * 7 + 3, uid="a")) +
            score_block(rows, highlight_from=split, reserve=reserve) + note +
            caption(['<span style="font-weight:600">Best defence %s</span> <span class="faded">(Stockfish %s)</span>'
                     % (move_html(trap.best_text()), esc(pawns(trap.record["best_cp"]))),
                     source_line(data)]) +
            footer(data))
    return page(CARD_W, CARD_H, body)


TAGLINE = "Stockfish finds the best move. We find the one they get wrong."


# ---------------------------------------------------------------- X

def profile():
    """Avatar: the board device on its own, on paper. A thick red hook holds a
    small ink knight. Paper keeps the disc edge visible on X's black theme and
    gives the red real contrast; the hook, not the knight, carries the mark."""
    size = 800
    u = 560
    weight = 0.13
    ex = 400 - u * 0.33 - u * 0.012
    ey = 400 - u * 0.48 + u * 0.015
    glyph, _ = hook_glyph(ex, ey, u, HOOK, weight=weight, bend=0.33, shank=0.5, rise=0.27)
    piece = u * 0.52
    knight = piece_svg("bN", ex + u * 0.33 - piece / 2 + u * 0.01, ey + u * 0.5 - piece * 0.5 + u * 0.02, piece, INK, PAPER)
    snell = ('<path d="M%.1f %.1f L%.1f %.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>'
             % (ex, ey - u * 0.13, ex, ey + 2, HOOK, u * weight * 0.62))
    body = f"""<svg class="abs" style="left:0;top:0" width="{size}" height="{size}">{knight}{snell}{glyph}</svg>"""
    return page(size, size, body)


def banner(data, traps):
    trap = pick(traps, "1.e4 e5 2.Bc4 Bc5 3.Qh5")
    sq = 47
    board = board_svg(trap.after, sq, catch_=catch(trap)[:2], trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=16, seed=19 * 7 + 3, uid="bn")
    first, second = TAGLINE.split(". ", 1)
    body = f"""
{lockup(64, 46, 30)}
<div class="abs serif" style="left:60px;top:140px;font-size:62px;line-height:1.08;letter-spacing:-0.02em">{esc(first)}.<br>{esc(second)}</div>
<div class="abs" style="left:1060px;top:44px">{board}</div>
"""
    return page(1500, 500, body)


# ---------------------------------------------------------------- store

def pick(traps, line):
    for trap in traps:
        if trap.line_text() == line:
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
    """Gumroad tile: the title across the top, one plate filling the lower
    right, two facts. Built to read at 250, 160 and 100 px."""
    trap = pick(traps, "1.e4 e5 2.Bc4 Bc5 3.Qh5")
    sq = 76
    board = board_svg(trap.after, sq, catch_=catch(trap)[:2], trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=19, seed=19 * 7 + 3, uid="th")
    body = f"""
{lockup(72, 56, 48, color=PAPER)}
<div class="abs num" style="left:62px;top:150px;font-size:148px;line-height:1;color:{PAPER};white-space:nowrap">1.e4 e5 Traps</div>
<div class="abs serif" style="left:72px;top:318px;font-size:48px;color:{PAPER}">for White</div>
<div class="abs txt" style="left:72px;top:984px;font-size:48px;line-height:1.15;color:{WATER_FADED}">
{len(traps)} traps<br>{thousands(data.get('sample_games') or 0)} games</div>
<div class="abs" style="left:440px;top:420px">{plate(board, 52, 30, 50)}</div>
"""
    return page(1200, 1200, body, bg=WATER, fg=PAPER, faded=WATER_FADED)


def cover_hero(data, traps):
    """Plate 17: the pack as a catalogue plate, on water."""
    trap = pick(traps, "1.e4 e5 2.Nf3 Nf6 3.Nxe5 Nxe4 4.Qe2 d5 5.d3")
    sq = 78
    board = board_svg(trap.after, sq, catch_=catch(trap)[:2], trail=chess.Move.from_uci(trap.top["uci"]),
                      coords=True, coord_size=17, seed=trap.number * 7 + 3, uid="c1")
    top = trap.top
    if top["games"] < SMALL_SAMPLE:
        result = "White scored %s points from %d games" % (points(top["our_score"], top["games"]), top["games"])
    else:
        result = "White scored %s%% in %s games" % (percent(top["our_score"]), thousands(top["games"]))
    cap = ('<div class="mono" style="font-size:17px;line-height:1.5;margin-top:58px;color:%s">'
           'Plate %d. %s, after %s<br><span style="color:%s">%s. Best defence %s.</span></div>'
           % (INK, trap.number, esc(trap.name), notation(trap.mistake_text() + "?"), FADED, result,
              notation(trap.best_text())))
    rows = "".join('<div style="display:grid;grid-template-columns:150px auto;padding:9px 0"><span style="color:%s">%s</span>'
                   '<span style="color:%s">%s</span></div>' % (PAPER, esc(v), WATER_FADED, esc(k))
                   for v, k in specs(data, traps))
    body = f"""
{lockup(80, 62, 44, color=PAPER)}
<div class="abs num" style="left:72px;top:180px;font-size:150px;line-height:.92;color:{PAPER}">1.e4 e5<br>Traps</div>
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
        board = board_svg(trap.after, sq, catch_=catch(trap)[:2], coords=False, seed=trap.number * 7 + 3,
                          uid="ci%d" % trap.number, hatch=3.3)
        cells.append('<div><div style="padding:3px">%s</div>'
                     '<div class="mono" style="font-size:13px;line-height:1.4;margin-top:13px;white-space:nowrap;letter-spacing:-0.02em">'
                     '<span style="font-weight:600">%02d</span>&nbsp;%s<br><span class="faded">%s%% go wrong</span></div></div>'
                     % (board, trap.number, esc(opening_of(trap).split(",")[-1].strip()), percent(wrong_share(trap))))
    cells.append('<div class="txt" style="font-size:13px;line-height:1.45;padding-top:4px">Each board shows the position '
                 'after the most common mistake. The red line is the punishment. The hook marks the target.</div>')
    body = f"""
{lockup(64, 44, 32)}
<div class="abs serif" style="left:437px;top:54px;font-size:32px;line-height:1">{len(traps)} traps that {esc(band(data))} players fall for</div>
<div class="abs mono faded" style="right:64px;top:64px;font-size:13px">Contents</div>
<div class="abs" style="left:64px;top:144px;width:1472px;display:grid;grid-template-columns:repeat(8, 166px);justify-content:space-between;row-gap:30px">{"".join(cells)}</div>
"""
    return page(1600, 900, body)


def cover_method(data, traps):
    """Anatomy of a trap: one plate with a numbered key, as in a field guide."""
    trap = pick(traps, "1.e4 e5 2.Bc4 Bc5 3.Qh5")
    strokes, hook, plies = catch(trap)
    sq = 86
    bx, by = 112, 92
    last = trap.board.peek()
    mistake = chess.Move.from_uci(trap.top["uci"])
    best = trap.board.parse_san(trap.record["best_reply_san"]) if trap.record["best_reply_san"] else None
    punish = " ".join(trap.punish_text().split()[:plies])
    engine = engine_name(data).split()[0]
    notes = [
        (last.to_square, "The bait", "%s. Every move White plays in the pack stays within half a pawn of %s’s best."
         % (notation(trap.line_text().split()[-1]), esc(engine))),
        (mistake.to_square, "The bite", "%s was played in %s%% of %s games. In all, %s%% of games went wrong here."
         % (notation(trap.mistake_text() + "?"), percent(trap.top["share"]), thousands(trap.record["games"]),
            percent(wrong_share(trap)))),
        (hook, "The hook", "%s. White then scored %s%% in %s real games."
         % (notation(punish), percent(trap.top["our_score"]), thousands(trap.top["games"]))),
    ]
    if best is not None:
        notes.append((best.to_square, "The escape", "%s holds the balance (%s %s)."
                      % (notation(trap.best_text()), esc(engine), esc(pawns(trap.record["best_cp"])))))
    red = draw_catch((strokes, hook), sq, 19 * 7 + 3)[2]
    keys, blocks = [], []
    for index, (square, label, text) in enumerate(notes):
        x, y = square_xy(square, sq)
        file = chess.square_file(square)
        if trap.after.piece_at(square) is None and square != hook:
            kx, ky = x + sq * 0.5, y + sq * 0.5          # empty square: key it in the middle
        elif square == hook or file in (0, 7):
            # the hook fills its square, and edge pieces have no free corner: key from outside the frame
            kx = 8 * sq + sq * 0.42 if file >= 4 else -sq * 0.62
            ky = y + sq * 0.5
        else:   # the free corner furthest from any red
            corners = [(x + sq * a, y + sq * b) for a in (0.11, 0.89) for b in (0.11, 0.89)]
            kx, ky = max(corners, key=lambda c: _clearance(c, red))
        keys.append('<circle cx="%.1f" cy="%.1f" r="14" fill="%s" stroke="%s" stroke-width="3"/>'
                    '<text x="%.1f" y="%.1f" font-family="Martian Mono" font-weight="600" font-size="17" fill="%s" '
                    'text-anchor="middle">%d</text>' % (kx, ky, INK, PAPER, kx, ky + 6, PAPER, index + 1))
        blocks.append('<div style="display:grid;grid-template-columns:52px auto;margin-bottom:34px">'
                      '<div class="mono" style="font-size:17px;font-weight:600;padding-top:9px">%d</div><div>'
                      '<div class="serif" style="font-size:32px;line-height:1">%s</div>'
                      '<div class="mono" style="font-size:17px;line-height:1.55;margin-top:12px">%s</div></div></div>'
                      % (index + 1, label, text))
    board = board_svg(trap.after, sq, catch_=(strokes, hook), trail=mistake, coords=True, coord_size=17,
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
    wanted = {int(n) for n in args.traps_only.split(",")} if args.traps_only else None
    if args.notes:
        notes = json.loads(pathlib.Path(args.notes).read_text(encoding="utf-8"))
        for trap in traps:
            trap.plain = notes.get(" ".join(trap.record["moves"]), {}).get("plain", "")
    jobs = []
    if "cards" in only:
        for trap in traps:
            if wanted and trap.number not in wanted:
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
