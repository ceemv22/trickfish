"""Trickfish studio: brand visuals laid out in HTML/CSS and rendered by Chromium.

Design rules (deliberately restrained):
* Black and white do the work. Grey for secondary text. One signal colour,
  used only where the opponent goes wrong.
* Inter Display, tight tracking, tabular figures. Big numbers carry the frame.
* A strict 72 px margin grid, hairline rules, no shadows, glows or gradients.
* Boards are flat greyscale vectors; the last move is the only tinted square.
"""

import base64
import html
import io
import json
import pathlib
import shutil
import subprocess
import tempfile

import chess
import chess.svg

from trickfish.trappack_render import pawns

SIGNAL = "#ff4d1a"
FONT_DIR = pathlib.Path("/usr/share/fonts/opentype/inter")
HERE = pathlib.Path(__file__).resolve().parent

CSS = """
@font-face { font-family: D; src: url('file://%(f)s/InterDisplay-Medium.otf'); font-weight: 500; }
@font-face { font-family: D; src: url('file://%(f)s/InterDisplay-SemiBold.otf'); font-weight: 600; }
@font-face { font-family: D; src: url('file://%(f)s/InterDisplay-Bold.otf'); font-weight: 700; }
@font-face { font-family: D; src: url('file://%(f)s/InterDisplay-ExtraBold.otf'); font-weight: 800; }
@font-face { font-family: D; src: url('file://%(f)s/InterDisplay-Black.otf'); font-weight: 900; }
@font-face { font-family: T; src: url('file://%(f)s/Inter-Regular.otf'); font-weight: 400; }
@font-face { font-family: T; src: url('file://%(f)s/Inter-Medium.otf'); font-weight: 500; }
@font-face { font-family: T; src: url('file://%(f)s/Inter-SemiBold.otf'); font-weight: 600; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: %(w)dpx; height: %(h)dpx; overflow: hidden; }
body { font-family: T; -webkit-font-smoothing: antialiased; font-feature-settings: 'tnum' 1, 'cv11' 1;
       position: relative; }
.light { background: #ffffff; color: #000000; }
.dark { background: #000000; color: #ffffff; }
.grey { color: #8a8a8a; }
.light .grey { color: #757575; }
.signal { color: %(signal)s; }
.d { font-family: D; }
.label { font-family: T; font-weight: 600; font-size: 22px; letter-spacing: 0.02em; text-transform: uppercase; }
.rule { height: 2px; background: currentColor; opacity: .14; }
.wm { font-family: D; font-weight: 800; font-size: 30px; letter-spacing: -0.03em; }
.abs { position: absolute; }
svg { display: block; }
"""


def board_svg(position, size, lastmove=None, flipped=False, dark=False):
    svg = chess.svg.board(position, size=size, lastmove=lastmove, flipped=flipped, coordinates=False,
                          colors={"square light": "#efefef", "square dark": "#bdbdbd",
                                  "square light lastmove": "#ffcbb6", "square dark lastmove": "#f59572",
                                  "outer border": "#000000" if dark else "#ffffff"})
    return svg.replace("<svg ", '<svg style="display:block" ', 1)


def mark_uri(size, fish=(255, 255, 255), trap=(255, 255, 255)):
    from trickfish import brand

    image = brand.mark(size, fish=fish, trap=trap)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def page(width, height, theme, body):
    css = CSS % {"f": FONT_DIR, "w": width, "h": height, "signal": SIGNAL}
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s</style></head>'
            '<body class="%s">%s</body></html>' % (css, theme, body))


def esc(text):
    return html.escape(str(text))


def opening_of(trap):
    return trap.name.split(":")[0]


def band(data):
    return data.get("band", "").replace("-", "–")


def punished(trap, plies=5):
    end = trap.after.copy()
    for uci in trap.punish_uci[:plies]:
        move = chess.Move.from_uci(uci)
        if move not in end.legal_moves:
            break
        end.push(move)
    return end


# ---------------------------------------------------------------- frames

def question(data, trap, total):
    side = "Black" if trap.board.turn == chess.BLACK else "White"
    share = round(trap.record["error_share"] * 100)
    board = board_svg(trap.board, 760, lastmove=trap.board.peek(), flipped=data["color"] == "black")
    meta = [("To move", side), ("Games", format(trap.record["games"], ",")),
            ("Last move", trap.line_text().split()[-1])]
    rows = "".join('<div style="margin-bottom:34px"><div class="label grey" style="font-size:17px">%s</div>'
                   '<div class="d" style="font-weight:700;font-size:30px;letter-spacing:-0.02em;margin-top:6px">%s</div></div>'
                   % (esc(k), esc(v)) for k, v in meta)
    body = f"""
<div class="abs wm" style="left:72px;top:60px">Trickfish</div>
<div class="abs label grey" style="right:72px;top:68px">Trap {trap.number:02d} / {total}</div>
<div class="abs d" style="left:64px;top:118px;font-weight:900;font-size:300px;line-height:.86;letter-spacing:-0.045em">{share}<span style="font-size:.62em;letter-spacing:-0.03em">%</span></div>
<div class="abs d" style="left:620px;top:202px;width:400px;font-weight:700;font-size:44px;line-height:1.08;letter-spacing:-0.035em">of {esc(band(data))} players go wrong here.</div>
<div class="abs" style="left:72px;top:448px">{board}</div>
<div class="abs" style="left:868px;top:452px;width:150px">{rows}</div>
<div class="abs rule" style="left:72px;right:72px;top:1246px"></div>
<div class="abs d" style="left:72px;top:1270px;font-weight:700;font-size:28px;letter-spacing:-0.02em">{esc(opening_of(trap))}. {side} to move.</div>
<div class="abs grey" style="right:72px;top:1276px;font-weight:500;font-size:22px">Answer tonight</div>
"""
    return page(1080, 1350, "light", body)


def answer(data, trap, total):
    end = punished(trap)
    board = board_svg(end, 600, lastmove=end.peek() if end.move_stack else None,
                      flipped=data["color"] == "black", dark=True)
    stats = [("%.0f%%" % (trap.top["our_score"] * 100), "White's real score after it" if data["color"] == "white"
              else "Black's real score after it"),
             (pawns(trap.top["our_cp"]), "Engine evaluation"),
             ("%.0f%%" % (trap.top["share"] * 100), "Players who chose it")]
    rows = "".join(f"""<div style="padding:22px 0 24px;border-top:2px solid rgba(255,255,255,.14)">
<div class="d" style="font-weight:800;font-size:64px;line-height:1;letter-spacing:-0.04em{';color:' + SIGNAL if i == 0 else ''}">{esc(v)}</div>
<div class="grey" style="font-weight:500;font-size:21px;margin-top:10px">{esc(k)}</div></div>""" for i, (v, k) in enumerate(stats))
    move = trap.mistake_text().replace("...", "…")
    punish = " ".join(trap.punish_text().split()[:6]).replace("...", "…")
    body = f"""
<div class="abs wm" style="left:72px;top:60px">Trickfish</div>
<div class="abs label grey" style="right:72px;top:68px">Trap {trap.number:02d} / {total}</div>
<div class="abs label grey" style="left:72px;top:160px">The mistake</div>
<div class="abs d" style="left:66px;top:196px;font-weight:900;font-size:184px;line-height:.9;letter-spacing:-0.045em">{esc(move)}<span class="signal">?</span></div>
<div class="abs" style="left:72px;top:448px">{board}</div>
<div class="abs" style="left:708px;top:448px;width:300px">{rows}</div>
<div class="abs rule" style="left:72px;right:72px;top:1086px"></div>
<div class="abs label grey" style="left:72px;top:1112px">The punishment</div>
<div class="abs d" style="left:72px;top:1150px;font-weight:700;font-size:44px;letter-spacing:-0.03em">{esc(punish)}</div>
<div class="abs grey" style="left:72px;top:1214px;font-weight:500;font-size:24px">Best defence was {esc(trap.best_text().replace("...", "…"))}.</div>
<div class="abs rule" style="left:72px;right:72px;top:1262px"></div>
<div class="abs d" style="left:72px;top:1284px;font-weight:700;font-size:26px;letter-spacing:-0.02em">All {total} traps, drills and PGN. Link in bio.</div>
"""
    return page(1080, 1350, "dark", body)


def profile():
    body = f"""<div class="abs" style="inset:0;display:flex;align-items:center;justify-content:center">
<img src="{mark_uri(300, trap=(110, 110, 110))}" style="width:470px"></div>"""
    return page(800, 800, "dark", body)


def banner(data, trap):
    board = board_svg(trap.board, 520, lastmove=trap.board.peek())
    body = f"""
<div class="abs label grey" style="left:80px;top:72px">Chess traps from real games</div>
<div class="abs d" style="left:76px;top:118px;width:980px;font-weight:800;font-size:64px;line-height:1.04;letter-spacing:-0.035em">Stockfish finds the best move.<br><span class="grey">We find the one they miss.</span></div>
<div class="abs" style="left:1060px;top:40px;transform:rotate(0deg)">{board}</div>
"""
    return page(1500, 500, "light", body)


def thumbnail(data, traps):
    trap = traps[0]
    board = board_svg(trap.board, 640, lastmove=trap.board.peek(), dark=True)
    stats = [(str(len(traps)), "traps"), (format(data.get("sample_games") or 0, ","), "real games"),
             (band(data), "rating band")]
    rows = "".join(f"""<div style="padding:16px 0;border-top:2px solid rgba(255,255,255,.14)">
<span class="d" style="font-weight:800;font-size:40px;letter-spacing:-0.03em">{esc(v)}</span>
<span class="grey" style="font-weight:500;font-size:22px;margin-left:10px">{esc(k)}</span></div>""" for v, k in stats)
    body = f"""
<div class="abs wm" style="left:80px;top:72px">Trickfish</div>
<div class="abs d" style="left:72px;top:150px;font-weight:900;font-size:210px;line-height:.88;letter-spacing:-0.042em">1.e4 e5<br><span class="signal">Traps.</span></div>
<div class="abs label grey" style="left:80px;top:560px">For White</div>
<div class="abs" style="left:80px;top:700px;width:400px">{rows}</div>
<div class="abs" style="left:600px;top:600px">{board}</div>
"""
    return page(1200, 1200, "dark", body)


def cover_hero(data, traps):
    trap = traps[0]
    board = board_svg(trap.board, 760, lastmove=trap.board.peek())
    body = f"""
<div class="abs wm" style="left:96px;top:80px">Trickfish</div>
<div class="abs d" style="left:88px;top:170px;font-weight:900;font-size:164px;line-height:.9;letter-spacing:-0.042em">1.e4 e5<br>Traps<span class="signal">.</span></div>
<div class="abs d" style="left:96px;top:520px;width:640px;font-weight:600;font-size:34px;line-height:1.22;letter-spacing:-0.02em">The {len(traps)} positions where real {esc(band(data))} players go wrong, found in {format(data.get('sample_games') or 0, ',')} Lichess games.</div>
<div class="abs rule" style="left:96px;width:640px;top:716px"></div>
<div class="abs grey" style="left:96px;top:740px;font-weight:500;font-size:24px">PDF guide · drills · PGN · for White</div>
<div class="abs" style="left:880px;top:70px">{board}</div>
"""
    return page(1600, 900, "light", body)


def cover_inside(data, traps):
    counts = {}
    for trap in traps:
        counts[opening_of(trap)] = counts.get(opening_of(trap), 0) + 1
    items = sorted(counts.items(), key=lambda item: -item[1])
    half = (len(items) + 1) // 2
    def column(entries):
        return "".join(f"""<div style="display:flex;justify-content:space-between;align-items:baseline;padding:18px 0;border-top:2px solid rgba(255,255,255,.14)">
<span class="d" style="font-weight:700;font-size:36px;letter-spacing:-0.025em">{esc(name)}</span>
<span class="d grey" style="font-weight:700;font-size:36px">{n:02d}</span></div>""" for name, n in entries)
    body = f"""
<div class="abs wm" style="left:96px;top:80px">Trickfish</div>
<div class="abs label grey" style="right:96px;top:88px">Inside the pack</div>
<div class="abs d" style="left:90px;top:150px;font-weight:900;font-size:120px;letter-spacing:-0.04em">{len(traps)} traps<span class="signal">.</span></div>
<div class="abs" style="left:96px;top:340px;width:680px">{column(items[:half])}</div>
<div class="abs" style="left:824px;top:340px;width:680px">{column(items[half:])}</div>
"""
    return page(1600, 900, "dark", body)


def cover_method(data, traps):
    steps = [("01", "Real games", "%s rated Lichess games where both players are %s."
              % (format(data.get("sample_games") or 0, ","), band(data))),
             ("02", "Sound moves", "Every move you play stays within half a pawn of Stockfish's best."),
             ("03", "Proven mistakes", "At least 15% of opponents go wrong, and you really score 60%+ after it.")]
    cols = "".join(f"""<div style="width:440px"><div class="d signal" style="font-weight:800;font-size:30px">{n}</div>
<div class="rule" style="margin:22px 0 26px;opacity:.9;height:3px;background:#000"></div>
<div class="d" style="font-weight:800;font-size:46px;letter-spacing:-0.035em">{esc(t)}</div>
<div class="grey" style="font-weight:500;font-size:26px;line-height:1.38;margin-top:16px">{esc(b)}</div></div>""" for n, t, b in steps)
    body = f"""
<div class="abs wm" style="left:96px;top:80px">Trickfish</div>
<div class="abs label grey" style="right:96px;top:88px">Method</div>
<div class="abs d" style="left:90px;top:160px;width:1300px;font-weight:900;font-size:104px;line-height:.95;letter-spacing:-0.04em">How we find a trap<span class="signal">.</span></div>
<div class="abs" style="left:96px;top:440px;right:96px;display:flex;gap:64px">{cols}</div>
"""
    return page(1600, 900, "light", body)


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
    parser.add_argument("--only", help="comma list: cards,x,store")
    args = parser.parse_args(argv)
    data, meta, traps = load(args.traps, args.notes)
    out = pathlib.Path(args.output)
    only = set((args.only or "cards,x,store").split(","))
    jobs = []
    if "cards" in only:
        for trap in traps:
            jobs.append((question(data, trap, len(traps)), out / "cards" / ("trap-%02d.png" % trap.number), 1080, 1350))
            jobs.append((answer(data, trap, len(traps)), out / "cards" / ("trap-%02d-answer.png" % trap.number), 1080, 1350))
    if "x" in only:
        jobs.append((profile(), out / "x" / "profile.png", 800, 800))
        jobs.append((banner(data, traps[0]), out / "x" / "banner.png", 1500, 500))
    if "store" in only:
        jobs.append((thumbnail(data, traps), out / "store" / "thumbnail.png", 1200, 1200))
        jobs.append((cover_hero(data, traps), out / "store" / "cover-1-hero.png", 1600, 900))
        jobs.append((cover_inside(data, traps), out / "store" / "cover-2-inside.png", 1600, 900))
        jobs.append((cover_method(data, traps), out / "store" / "cover-3-method.png", 1600, 900))
    render(jobs)
    print("rendered %d frames into %s" % (len(jobs), out))


if __name__ == "__main__":
    main()
