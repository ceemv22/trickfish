"""Short vertical videos (1080x1920, 30 fps, with a synthesised sound layer) for the trap pack.

Chromium renders only keyframes (one batch for every video); ffmpeg turns the
list of (frame, duration) into H.264 with the concat demuxer. The look is the
cards': the studio's board, line, hook, fonts and numbers are reused."""
import json
import math
import pathlib
import shutil
import subprocess
import tempfile

import chess

from trickfish import studio as st
from trickfish.trappack_render import numbered

W, H, FPS = 1080, 1920, 30
SQ, BX, BY = 100, 140, 650           # board 800 px; text above it sits in y 150-620
MARGIN, TEXT_W = 64, 952
COORD = 28
PLY_FRAMES, MOVE_FRAMES = 6, 8       # in-between frames while a piece slides
TICK = 2                             # frames each in-between frame is held (1/15 s)
PLY_HOLD = 15                        # 0.5 s on the finished ply (the whole ply takes 0.9 s)


def sec(seconds):
    return int(round(seconds * FPS))


def tx(html, top, size, cls="txt", weight=400, color=None, width=TEXT_W, lh=1.2, left=MARGIN):
    style = "left:%dpx;top:%dpx;width:%dpx;font-size:%dpx;line-height:%.2f;font-weight:%d" % (left, top, width, size, lh, weight)
    if color:
        style += ";color:" + color
    return '<div class="abs %s" style="%s">%s</div>' % (cls, style, html)


def hero(value):
    # big_number sets its figures at x=52; shifted so the ink starts at the 64 px margin
    return '<div class="abs" style="left:12px;top:0">%s</div>' % st.big_number(value)


def mono(text, size):
    return '<span style="font-size:%dpx">%s</span>' % (size, st.move_html(text))


def frame_html(trap, total, answer, body):
    return st.page(W, H, st.card_frame(None, trap, total, answer) + body)


def board_div(svg):
    return '<div class="abs" style="left:%dpx;top:%dpx">%s</div>' % (BX, BY, svg)


def overlay(svg, extra):
    cut = svg.rfind("</svg>")
    return svg[:cut] + extra + svg[cut:]


def piece_at(piece, x, y):
    code = ("w" if piece.color else "b") + piece.symbol().upper()
    return st.piece_svg(code, x, y, SQ, st.INK, st.PAPER, 1.5 if not piece.color else 0.0)


def ease(t):
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- the red line, growing

def geometry(strokes, hook):
    """Per stroke: points (x, y, is_stop, square) of the centre line and cumulative lengths."""
    out = []
    drop = strokes[-1][-1][3] is False
    x0, y0 = st.square_xy(hook, SQ)
    for index, stroke in enumerate(strokes):
        pts = []
        for square, dx, dy, stop in stroke:
            cx, cy = st.centre(square, SQ)
            pts.append((cx + dx * SQ, cy + dy * SQ, stop, square))
        if index == len(strokes) - 1:
            if drop:
                square, dx, dy, _ = stroke[-1]
                pts.append((st.centre(square, SQ)[0] + dx * SQ, y0 + SQ * st.HOOK_GEOMETRY["eye_y"], False, None))
            else:
                if stroke[-1][0] == hook:
                    pts.pop()
                pts.append((x0 + SQ / 2, y0 + SQ / 2, True, hook))
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.dist(a[:2], b[:2]))
        out.append((pts, cum))
    return out


def reveal_steps(geo, played):
    """Length of every stroke drawn after each played ply: a stroke advances when the
    punishing piece makes the move between two of its stops."""
    lens, si, ti, out = [0.0] * len(geo), 0, 0, []
    for _, move in played:
        if si < len(geo):
            pts, cum = geo[si]
            tj = next((j for j in range(ti + 1, len(pts)) if pts[j][2]), None)
            if tj is not None and pts[ti][3] == move.from_square and pts[tj][3] == move.to_square:
                lens[si], ti = cum[tj], tj
                if tj == len(pts) - 1:
                    si, ti = si + 1, 0
        out.append(list(lens))
    return out


def lines_svg(lines, geo, lens, uid):
    paths = ""
    for (pts, _), reach in zip(geo, lens):
        if reach > 0.5:
            paths += ('<path d="M%s" fill="none" stroke="#fff" stroke-width="%d" stroke-dasharray="%.1f 100000"/>'
                      % (" L".join("%.1f %.1f" % p[:2] for p in pts), SQ * 0.9, reach))
    if not paths:
        return ""
    return ('<defs><mask id="rv-%s" maskUnits="userSpaceOnUse" x="-200" y="-200" width="1400" height="1400">'
            '<rect x="-200" y="-200" width="1400" height="1400" fill="#000"/>%s</mask></defs>'
            '<g mask="url(#rv-%s)">%s</g>' % (uid, paths, uid, lines))


# ---------------------------------------------------------------- one trap

class Plan:
    """The legal sequence behind a video: the mistake, then the punishing plies that are
    played on the board. The line stops before the move that takes (or moves) the hooked
    piece: that piece stays on its square, so the hook can land on it."""

    def __init__(self, trap):
        self.trap = trap
        self.strokes, self.hook, self.plies = st.catch(trap)
        self.mistake = chess.Move.from_uci(trap.top["uci"])
        assert self.mistake in trap.board.legal_moves, "illegal mistake in trap %d" % trap.number
        board, self.played, stopped = trap.after.copy(), [], False
        for uci in trap.punish_uci[:self.plies]:
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves, "illegal punishment %s in trap %d" % (uci, trap.number)
            stopped = stopped or self.hook in (move.from_square, move.to_square)
            if not stopped:
                self.played.append((board.copy(), move))
            board.push(move)
        self.final = self.played[-1][0].copy() if self.played else trap.after.copy()
        if self.played:
            self.final.push(self.played[-1][1])
        assert self.final.piece_at(self.hook) is not None, "nothing to hook in trap %d" % trap.number
        self.seed = trap.number * 7 + 3
        self.lines, _, self.red, _ = st.draw_catch((self.strokes, self.hook), SQ, self.seed)
        self.geo = geometry(self.strokes, self.hook)
        self.totals = [cum[-1] for _, cum in self.geo]
        self.steps = reveal_steps(self.geo, self.played)
        self.trail = st._trail(self.mistake, SQ, st.INK, st.PAPER, self.red)

    def board(self, board, extra="", lens=None, uid="v"):
        svg = st.board_svg(board, SQ, coords=True, coord_size=COORD, seed=self.seed, uid=uid)
        grown = lines_svg(self.lines, self.geo, lens, uid) if lens else ""
        return board_div(overlay(svg, self.trail + grown + extra))

    def slide(self, before, move, t, lens, uid):
        """`before` with the moving piece `t` of the way from its square to its target."""
        if t >= 1:
            after = before.copy()
            after.push(move)
            return self.board(after, "", lens, uid)
        piece = before.piece_at(move.from_square)
        rest = before.copy()
        rest.remove_piece_at(move.from_square)
        (ax, ay), (bx, by) = st.square_xy(move.from_square, SQ), st.square_xy(move.to_square, SQ)
        e = ease(t)
        return self.board(rest, piece_at(piece, ax + (bx - ax) * e, ay + (by - ay) * e), lens, uid)


HOOK_SQ = 120                         # hook v2: board 960 px wide
HOOK_BX = (W - 8 * HOOK_SQ) // 2
FRACTIONS = ((1, 2), (1, 3), (2, 3), (1, 4), (1, 5), (1, 6))


def stat_line(share):
    """'1 in 5 get this wrong' when the share is within 2 points of a simple fraction, else '65% get this wrong'."""
    near = min(FRACTIONS, key=lambda f: abs(share - f[0] / f[1]))
    if abs(share - near[0] / near[1]) <= 0.02:
        return "%d in %d get this wrong" % near
    return "%s%% get this wrong" % st.percent(share)


def hook_v2(trap, total, mover, add, event, clock):
    """0 to 2.5 s: the board is the hero; White's last move slides in (0 to 0.5 s) and lands with its tock."""
    prev = trap.board.copy()
    last = prev.pop() if prev.move_stack else None
    by = (150 + (H - 400)) // 2 - 4 * HOOK_SQ     # centred in the safe area
    text = (tx(st.esc(mover) + " to move.", 150, 80, "serif", lh=1.1) +
            tx(st.esc(stat_line(st.wrong_share(trap))), 248, 60, "serif", lh=1.1, color=st.HOOK))

    def board(pos, extra, uid):
        svg = st.board_svg(pos, HOOK_SQ, coords=True, coord_size=34, seed=trap.number * 7 + 3, uid=uid)
        return '<div class="abs" style="left:%dpx;top:%dpx">%s</div>' % (HOOK_BX, by, overlay(svg, extra))

    if last is None:
        add(text + board(trap.board, "", "h"), False, sec(2.5))
        return
    piece = prev.piece_at(last.from_square)
    rest = prev.copy()
    rest.remove_piece_at(last.from_square)
    (ax, ay), (bx, byy) = st.square_xy(last.from_square, HOOK_SQ), st.square_xy(last.to_square, HOOK_SQ)
    code = ("w" if piece.color else "b") + piece.symbol().upper()

    def sliding(t, uid):
        e = ease(t)
        glyph = st.piece_svg(code, ax + (bx - ax) * e, ay + (byy - ay) * e, HOOK_SQ, st.INK, st.PAPER, 1.5 if not piece.color else 0.0)
        return text + board(rest, glyph, uid)

    add(sliding(0, "h0"), False, 3)
    for k in range(1, 7):
        add(sliding(k / 7, "h%d" % k), False, TICK)
    kind = "capture" if prev.is_capture(last) else "move"
    event(kind)
    if prev.gives_check(last):
        event("check")
    add(text + board(trap.board, "", "h"), False, sec(2.5) - 15)


def build(data, trap, total, hook="v2"):
    """Return the list of (html, frames) for one video."""
    plan = Plan(trap)
    mover, games = st.side_name(trap.board.turn), trap.record["games"]
    us, top = st.side_name(trap.color), trap.top
    frames, events = [], []

    def clock():
        return sum(count for _, count in frames) / FPS

    def event(kind, at=None, **extra):
        events.append(dict(type=kind, t=round(clock() if at is None else at, 4), **extra))

    def landing(board, move, at):
        kind = "capture" if board.is_capture(move) else "move"
        event(kind, at)
        if board.gives_check(move):
            event("check", at)

    def add(body, answer, count):
        frames.append((frame_html(trap, total, answer, body), count))

    if hook == "v1":
        # 1  the hook (3 s)
        share = st.percent(st.wrong_share(trap)) + "%"
        add(hero(share) +
            tx("of %s games at %s<br>go wrong here. <span style=\"font-weight:600\">%s to move.</span>"
               % (st.thousands(games), st.esc(st.band(data)), mover), 385, 52) +
            tx(st.esc(st.opening_of(trap)) + ".", 522, 60, "serif") +
            plan.board(trap.board), False, sec(3))
        countdown = ((3, sec(1.4)), (2, sec(1.3)), (1, sec(1.3)))      # 4 s
    else:
        hook_v2(trap, total, mover, add, event, clock)
        countdown = ((2, sec(1.0)), (1, sec(1.0)))                     # 2 s

    # 2  what would you play: 3-2-1 (v1) or 2-1 (v2)
    for digit, count in countdown:
        event("tick")
        add(tx("What would<br>you play?", 170, 88, "serif", width=640, lh=1.1) +
            '<div class="abs num" style="right:90px;top:150px;font-size:280px;color:%s">%d</div>' % (st.HOOK, digit) +
            tx("%s to move." % mover, 408, 52, weight=600) +
            plan.board(trap.board), False, count)

    # 3  the most common mistake (move 0.5 s, held 2.5 s)
    played_text = trap.mistake_text() + "?"
    mistake_text = (tx(mono(played_text, 88), 165, 88, lh=1.1) +
                    tx(st.esc(st.title_of(trap)) + ".", 290, 60, "serif", lh=1.1) +
                    tx("The most common mistake:<br>played in %s%% of games." % st.percent(top["share"]), 385, 52))
    before = trap.board
    for k in range(1, MOVE_FRAMES + 1):
        add(mistake_text + plan.slide(before, plan.mistake, k / (MOVE_FRAMES + 1), None, "m%d" % k), False, TICK)
    landing(before, plan.mistake, clock())
    add(mistake_text + plan.slide(before, plan.mistake, 1, None, "m"), False, sec(2.5))

    # 4  the punishment, ply by ply (0.9 s each); the red line grows with the piece
    full = numbered(trap.punish[:plan.plies], trap.ply + 1)
    note = tx(st.prose(st.plain_of(trap)), 400, 48, lh=1.2) if st.plain_of(trap) else ""

    def punish_text(text):
        return tx(st.notation(text).join(['<span class="mono" style="font-weight:500;font-size:52px">', "</span>"]),
                  165, 52, lh=1.3) + note

    prev = [0.0] * len(plan.geo)
    for k, ((board, move), lens) in enumerate(zip(plan.played, plan.steps)):
        text = punish_text(numbered(trap.punish[:k + 1], trap.ply + 1))
        begin = clock()
        for j in range(1, PLY_FRAMES + 1):
            t = ease(j / (PLY_FRAMES + 1))
            now = [a + (b - a) * t for a, b in zip(prev, lens)]
            add(text + plan.slide(board, move, j / (PLY_FRAMES + 1), now, "p%d_%d" % (k, j)), True, TICK)
        landing(board, move, clock())
        if any(b - a > 0.5 for a, b in zip(prev, lens)):
            event("line_start", begin)
            event("line_end", clock())
        add(text + plan.slide(board, move, 1, lens, "p%d" % k), True, PLY_HOLD)
        prev = lens
    # 4b the line runs out to the target, then the hook lands on the caught piece
    text = punish_text(full)
    run_from = clock()
    for j in range(1, 4):
        t = ease(j / 4)
        add(text + plan.board(plan.final, "", [a + (b - a) * t for a, b in zip(prev, plan.totals)], "g%d" % j), True, TICK + 1)
    if any(b - a > 0.5 for a, b in zip(prev, plan.totals)):
        event("line_start", run_from)
        event("line_end", clock())
    event("hook")
    svg = st.board_svg(plan.final, SQ, catch_=(plan.strokes, plan.hook), trail=plan.mistake, coords=True,
                       coord_size=COORD, seed=plan.seed, uid="hk")
    add(text + board_div(svg), True, sec(2.2) if len(plan.played) < 3 else sec(1.8))

    # 5  the score and the best defence, then the sign-off (3.8 s)
    if top["games"] < st.SMALL_SAMPLE:
        scored = st.points(top["our_score"], top["games"])
        number = scored
        first = ("%s scored %s points from %d games after %s"
                 % (us, scored, top["games"], mono(played_text, 52)))
        sub = "(%s%% of %s games)" % (st.percent(top["share"]), st.thousands(games))
    else:
        number = st.percent(top["our_score"]) + "%"
        first = "%s’s score after %s" % (us, mono(played_text, 52))
        sub = "(played in %s%% of %s games)" % (st.percent(top["share"]), st.thousands(games))
    score = (hero(number) + tx(first, 395, 52, lh=1.25) + tx(sub, 395 + (190 if top["games"] < st.SMALL_SAMPLE else 130), 48, color=st.FADED) +
             '<div class="abs" style="left:64px;top:700px;width:952px;height:3px;background:%s"></div>' % st.INK +
             tx("Best defence", 740, 52, weight=600) +
             tx(mono(trap.best_text(), 96), 820, 96, lh=1.1) +
             tx("Stockfish %s" % st.esc(st.pawns(trap.record["best_cp"])), 950, 48, color=st.FADED))
    add(score, True, sec(1.6))
    event("end_card")
    add(score + tx("@trickfishchess", 1150, 100, "serif", lh=1.1) +
        tx("%d traps · link in bio" % total, 1290, 64, weight=600), True, sec(2.2))
    if hook != "v1" and clock() > 20.0:            # keep every v2 video within 20 s: the end card gives the time
        html, count = frames[-1]
        frames[-1] = (html, count - int(math.ceil((clock() - 20.0) * FPS)))
    return frames, events


# ---------------------------------------------------------------- rendering

def encode(sequence, out, fade_in=0.2):
    """sequence: [(png path, frames)] -> silent H.264 mp4. Returns the duration in seconds."""
    total = sum(n for _, n in sequence)
    seconds = total / FPS
    lines = []
    for path, n in sequence:
        lines += ["file '%s'" % path, "duration %.6f" % (n / FPS)]
    lines.append("file '%s'" % sequence[-1][0])
    listing = pathlib.Path(str(out) + ".txt")
    listing.write_text("\n".join(lines) + "\n")
    fade = ("fade=t=in:st=0:d=%.2f:color=%s," % (fade_in, st.PAPER) if fade_in else "") + "fade=t=out:st=%.3f:d=0.4:color=%s" % (seconds - 0.4, st.PAPER)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-vf", "fps=%d,%s,format=yuv420p" % (FPS, fade), "-t", "%.3f" % seconds,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-an", str(out)], check=True)
    finally:
        listing.unlink()
    return seconds


def add_sound(silent_mp4, events, seconds, out):
    """Synthesise the sound layer from the event timeline, normalise it and mux it into `out`."""
    from trickfish.studio import sound
    wav = pathlib.Path(str(out) + ".wav")
    try:
        sound.write_wav(wav, sound.mix(events, seconds))
        sound.mux(silent_mp4, wav, out)
    finally:
        wav.unlink(missing_ok=True)


def make(data, traps, out, numbers, silent=False, timelines=None, hook="v2"):
    """Render the videos for the trap numbers into out/trap-NN.mp4 and return {number: seconds}.
    `timelines`, if given, is filled with {number: {"scenes": [...], "events": [...]}}."""
    by_number = {trap.number: trap for trap in traps}
    out = pathlib.Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="trickfish-video-"))
    try:
        manifest, plans, plans_events = [], {}, {}
        for number in numbers:
            sequence = []
            frames, events = build(data, by_number[number], len(traps), hook)
            if timelines is not None:
                scenes, at = [], 0.0
                for _, count in frames:
                    scenes.append((round(at, 4), round(count / FPS, 4)))
                    at += count / FPS
                timelines[number] = {"scenes": scenes, "events": events}
            plans_events[number] = events
            for index, (markup, count) in enumerate(frames):
                name = "t%02d-%03d" % (number, index)
                (work / (name + ".html")).write_text(markup, encoding="utf-8")
                manifest.append({"html": str(work / (name + ".html")), "out": str(work / (name + ".png")),
                                 "width": W, "height": H, "scale": 1, "pdf": False})
                sequence.append((str(work / (name + ".png")), count))
            plans[number] = sequence
        (work / "manifest.json").write_text(json.dumps(manifest))
        subprocess.run(["node", str(st.HERE / "render.mjs"), str(work / "manifest.json")], check=True, cwd=str(st.HERE))
        result = {}
        for number, sequence in plans.items():
            target = out / ("trap-%02d.mp4" % number)
            if silent:
                result[number] = encode(sequence, target, 0.2 if hook == "v1" else 0)
            else:
                quiet = work / ("quiet-%02d.mp4" % number)
                result[number] = encode(sequence, quiet, 0.2 if hook == "v1" else 0)
                add_sound(quiet, plans_events[number], result[number], target)
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)
