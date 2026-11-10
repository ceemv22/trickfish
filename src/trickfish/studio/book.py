"""The paid PDF in the Line & Hook identity.

A4 pages are laid out in HTML/CSS (fixed 210 x 297 mm pages, so every page is
designed rather than flowed) and printed by Chromium's page.pdf(): text stays
selectable, diagrams stay vector. All prose comes from notes.json: `_meta`
(title, subtitle, method, usage, fineprint, optional `labels`) and, per trap,
name / idea / defence / plain. Numbers come from traps.json. The only words in
this file are structural labels, which `_meta.labels` can override.

Type scale (pt): display 26 (Young Serif: titles and the hero), text 11
(Schibsted Grotesk), detail 8 (Martian Mono: notation in tables, coordinates,
labels, folios). The trap hero is the same Young Serif lockup as the cards.
"""

import html
import math
import re

import chess

from trickfish.trappack_render import pawns
from trickfish import studio as st

MM = 96 / 25.4                      # CSS px per mm
PAGE_W, PAGE_H = 210, 297

LABELS = {
    "contents_method": "How this pack was made",
    "contents_usage": "How to use it",
    "glance": "The traps at a glance",
    "glance_cols": ["#", "Opening and title", "Line", "Went wrong", "White scored", "n"],
    "drills": "Drills",
    "facts": ["{n} traps", "{n} Lichess games", "{band} both players"],
    "drill": "Drill",
    "white_to_move": "White to move",
    "black_to_move": "Black to move",
    "answers": "Answer key",
    "about": "About the numbers",
    "trap": "Trap",
    "after": "after",
    "went_wrong": "of {n} games went wrong here.",
    "most_common": "Most common mistake",
    "played_in": "in {share}% of games",
    "score": "White’s score after it",
    "points": "{points} points from {games} games",
    "score_pct": "{score}% from {games} games",
    "engine_after": "Stockfish after it",
    "idea": "The idea",
    "punishment": "The punishment",
    "defence": "Best defence",
    "others": "The other {n}",
    "others_price": "Full pack",
}


def labels(meta):
    out = dict(LABELS)
    out.update(meta.get("labels") or {})
    return out


# ---------------------------------------------------------------- text helpers

_ALLOWED = re.compile(r"(</?(?:b|i|em|strong)>)")


def rich(text):
    """notes.json prose: keep <b>/<i>, escape everything else, set full moves in
    the mono with figurines (one unbreakable unit each)."""
    out = []
    for part in _ALLOWED.split(str(text)):
        if _ALLOWED.fullmatch(part):
            out.append(part)
        else:
            text = st.prose(re.sub(r"(?<=\d)-(?=\d)", "\u2013", part))
            # number ranges ("1200\u20131599") never break at the dash
            out.append(re.sub(r"(?<![\w>])(\d[\d,]*\u2013\d[\d,]*)", r'<span style="white-space:nowrap">\1</span>', text))
    return "".join(out)


def glue(text):
    """No widows: bind the last two words of a heading."""
    head, _, tail = text.rpartition(" ")
    return head + " " + tail if head and " " in head else text


def line_html(sans, start_ply=0):
    """A move sequence in the mono, each numbered move an unbreakable unit."""
    parts = []
    for offset, san in enumerate(sans):
        ply = start_ply + offset
        if ply % 2 == 0:
            parts.append("%d.%s" % (ply // 2 + 1, san))
        elif offset == 0:
            parts.append("%d…%s" % (ply // 2 + 1, san))
        else:
            parts.append(san)
    # keep "7.Bxd5 Qf6" together: a white move and black's reply form one unit
    units, i = [], 0
    while i < len(parts):
        if re.match(r"\d+\.", parts[i]) and i + 1 < len(parts) and not re.match(r"\d", parts[i + 1]):
            units.append(parts[i] + " " + parts[i + 1])
            i += 2
        else:
            units.append(parts[i])
            i += 1
    # pairs are joined by a mono space, never narrower than the space inside a pair
    return '<span class="mono"> </span>'.join('<span class="mv">%s</span>' % st.notation(u) for u in units)


def side(color):
    return st.side_name(color)


# ---------------------------------------------------------------- CSS

def css():
    return st.font_css() + """
@page { size: A4; margin: 0; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { background: %(paper)s; color: %(ink)s; }
body { font-family: 'Schibsted Grotesk'; font-size: 11pt; line-height: 1.42; font-kerning: normal;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 210mm; height: 297mm; position: relative; overflow: hidden; background: %(paper)s;
        break-after: page; }
.page:last-child { break-after: auto; }
.abs { position: absolute; }
.serif { font-family: 'Young Serif'; font-weight: 400; font-feature-settings: 'lnum' 1; letter-spacing: -0.01em; }
.mono { font-family: 'Martian Mono'; font-weight: 400; font-variant-numeric: tabular-nums; }
.faded { color: %(faded)s; }
.mv { white-space: nowrap; font-family: 'Martian Mono'; }
.fig { display: inline-block; position: relative; width: .92em; height: .92em; vertical-align: -0.14em;
       margin: 0 -0.04em 0 -0.02em; }
.fig svg { width: 100%%; height: 100%%; display: block; }
.figtxt { position: absolute; left: 0; right: 0; top: 0; text-align: center; color: transparent; font-size: 1.1em; line-height: .9; letter-spacing: -0.05em; }
svg { overflow: visible; }
h1, h2 { font-family: 'Young Serif'; font-weight: 400; font-feature-settings: 'lnum' 1; text-wrap: balance;
         letter-spacing: -0.01em; }
h2 { font-size: 26pt; line-height: 1.08; }
p { text-wrap: pretty; hyphens: none; }
.label { font-family: 'Martian Mono'; font-size: 8pt; line-height: 1.3; color: %(faded)s; }
.folio { position: absolute; left: 18mm; right: 16mm; bottom: 9mm; display: flex; justify-content: space-between;
         font-family: 'Martian Mono'; font-size: 8pt; color: %(faded)s; }
.fit { overflow: hidden; }
p .mono, p .mv { font-size: .9em; }
.label .fig { margin-right: .06em; }
table { border-collapse: collapse; }
""" % {"paper": st.PAPER, "ink": st.INK, "faded": st.FADED}


FIT_SCRIPT = """<script>
// Copy comes from notes.json and may change: any .fit box whose text overflows
// is set a little smaller (never below 8.5pt) until it fits its page.
window.__layout = () => {
  for (const el of document.querySelectorAll('.fit')) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    const floor = 8.5 * 96 / 72;
    while (el.scrollHeight > el.clientHeight + 1 && size > floor) {
      size -= 0.25; el.style.fontSize = size + 'px';
    }
    if (el.scrollHeight > el.clientHeight + 1) el.setAttribute('data-overflow', '1');
  }
};
</script>"""


def document(title, pages):
    return ('<!doctype html><html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>%s%s'
            '</body></html>' % (html.escape(title), css(), "".join(pages), FIT_SCRIPT))


def page(body, folio=None):
    foot = ""
    if folio:
        foot = '<div class="folio"><span>%s</span><span>%s</span></div>' % folio
    return '<section class="page">%s%s</section>' % (body, foot)


def board_block(board, size_mm, **kw):
    sq = size_mm * MM / 8
    kw.setdefault("coord_size", 8 * 96 / 72)
    return st.board_svg(board, sq, **kw)


def hero(value, size_pt=54):
    """The card hero lockup at book size: lining figures plus a cap-aligned
    superscript at 0.42 of the size."""
    if value.endswith("%") or value.endswith("½"):
        whole, sup = value[:-1], value[-1]
    else:
        whole, sup = value, ""
    small = size_pt * st.SUPER
    out = '<span style="display:inline-flex;align-items:flex-start;line-height:1">'
    out += '<span class="serif" style="font-size:%.1fpt;line-height:1;letter-spacing:-0.03em">%s</span>' % (size_pt, whole)
    if sup:
        drop = st.CAP_TOP["fig"] * size_pt - st.CAP_TOP[sup] * small
        kern = (st.SUPER_KERN.get(whole[-1:], 0.016) + (st.HALF_EXTRA if sup == "½" else 0)) * size_pt
        out += ('<span class="serif" style="font-size:%.1fpt;line-height:1;margin:%.2fpt 0 0 %.2fpt">%s</span>'
                % (small, drop, kern, sup))
    return out + "</span>"


# ---------------------------------------------------------------- pages

def cover(data, meta, traps, L):
    trap = st.pick(traps, "1.e4 e5 2.Nf3 Nf6 3.Nxe5 Nxe4 4.Qe2 d5 5.d3")
    board = board_block(trap.after, 118, catch_=st.catch(trap)[:2], trail=chess.Move.from_uci(trap.top["uci"]),
                        seed=trap.number * 7 + 3, uid="cv")
    facts = [L["facts"][0].format(n=len(traps)),
             L["facts"][1].format(n=st.thousands(data.get("sample_games") or 0)),
             L["facts"][2].format(band=st.band(data))]
    tagline = meta.get("tagline", "")
    body = """
<div class="abs" style="left:18mm;top:0;width:120mm;height:30mm">%s</div>
<h1 class="abs" style="left:18mm;top:44mm;width:150mm;font-size:56pt;line-height:1">%s</h1>
<p class="abs" style="left:18mm;top:108mm;width:118mm;font-size:13pt;line-height:1.35">%s</p>
<div class="abs mono" style="left:18mm;top:132mm;width:176mm;font-size:8pt;line-height:1.9">%s</div>
<p class="abs serif" style="left:18mm;top:152mm;width:57mm;font-size:16pt;line-height:1.2;text-wrap:balance">%s</p>
<div class="abs" style="left:80mm;top:150mm">%s</div>
<div class="abs label" style="left:80mm;top:276mm;width:118mm">%s %02d. %s, %s %s</div>
""" % (st.lockup(0, 60, 26),
       html.escape(glue(meta.get("title", ""))), rich(meta.get("subtitle", "")),
       ' <span class="faded">\u00b7</span> '.join(rich(f) for f in facts), html.escape(glue(tagline)).replace("'", "\u2019"),
       board,
       L["trap"], trap.number, html.escape(trap.name.replace("'", "’")), L["after"],
       st.notation(trap.mistake_text() + "?", ink=st.FADED))
    return page(body)


def prose_page(heading, paragraphs, numbered, folio):
    items = []
    for index, text in enumerate(paragraphs, start=1):
        if numbered:
            items.append('<div style="display:grid;grid-template-columns:12mm 1fr;margin-bottom:5mm">'
                         '<span class="mono faded" style="font-size:8pt;padding-top:1.2mm">%02d</span><p>%s</p></div>'
                         % (index, rich(text)))
        else:
            items.append('<p style="margin-bottom:4.5mm">%s</p>' % rich(text))
    body = """
<h2 class="abs" style="left:18mm;top:24mm;width:150mm">%s</h2>
<div class="abs fit" style="left:%smm;top:52mm;width:118mm;bottom:26mm;font-size:12pt;line-height:1.5">%s</div>
""" % (html.escape(glue(heading)), "18" if numbered else "18", "".join(items))
    return page(body, folio)


def score_text(trap, L):
    top = trap.top
    if top["games"] < st.SMALL_SAMPLE:
        return L["points"].format(points=st.points(top["our_score"], top["games"]), games=top["games"])
    return L["score_pct"].format(score=st.percent(top["our_score"]), games=st.thousands(top["games"]))


def glance_pages(data, traps, L, folio_for, per_page=12):
    pages = []
    cols = L["glance_cols"]
    for start in range(0, len(traps), per_page):
        rows = []
        for trap in traps[start:start + per_page]:
            top = trap.top
            if top["games"] < st.SMALL_SAMPLE:
                scored = ('%s<span class="mono" style="font-size:7pt;white-space:nowrap"> /%d pts</span>'
                          % (st.points(top["our_score"], top["games"]), top["games"]))
            else:
                scored = "%s%%" % st.percent(top["our_score"])
                if top["games"] < 100:   # voice rule 5: show n for 50-99 games
                    scored += '<span class="mono" style="font-size:7pt;white-space:nowrap"> /%d</span>' % top["games"]
            rows.append(
                '<tr><td class="mono" style="padding-top:1.2mm">%02d</td>'
                '<td><div class="faded" style="font-size:8.5pt">%s</div><div>%s</div></td>'
                '<td class="mono" style="font-size:7.5pt;line-height:1.55;padding-top:.6mm">%s</td>'
                '<td class="serif num">%s%%</td><td class="serif num">%s</td>'
                '<td class="mono num" style="font-size:8pt;padding-top:1.4mm">%s</td></tr>'
                % (trap.number, html.escape(st.opening_of(trap).replace("'", "’")),
                   html.escape(glue(st.title_of(trap).replace("'", "’"))), line_html(trap.sans),
                   st.percent(st.wrong_share(trap)), scored, st.thousands(trap.record["games"])))
        head = "".join('<th class="label" style="text-align:%s">%s</th>' % ("right" if i >= 3 else "left", html.escape(c))
                       for i, c in enumerate(cols))
        table = ('<table style="width:176mm">'
                 '<colgroup><col style="width:9mm"><col style="width:44mm"><col><col style="width:19mm">'
                 '<col style="width:27mm"><col style="width:13mm"></colgroup>'
                 '<thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, "".join(rows)))
        heading = L["glance"] if start == 0 else ""
        body = """
<style>
.glance td { border-top: 0.35mm solid %(rule)s; padding: 2.4mm 2mm 2.4mm 0; vertical-align: top; font-size: 10pt; line-height: 1.3; }
.glance th { padding: 0 2mm 2mm 0; font-weight: 400; }
.glance td.num { text-align: right; white-space: nowrap; font-size: 14pt; line-height: 1; padding-top: 2.2mm; }
</style>
%(h)s
<div class="abs glance" style="left:18mm;top:%(top)smm;width:176mm">%(table)s</div>
""" % {"rule": "#CFC9BB", "h": ('<h2 class="abs" style="left:18mm;top:24mm;width:150mm">%s</h2>' % html.escape(glue(heading))
                                 if heading else ""), "top": 50 if heading else 24, "table": table}
        pages.append(page(body, folio_for(len(pages))))
    return pages


def trap_page(data, trap, total, L, folio):
    total = total or 0
    strokes, hook, plies = st.catch(trap)
    top = trap.top
    q = board_block(trap.board, 96, uid="q%d" % trap.number)
    a = board_block(trap.after, 96, catch_=(strokes, hook), trail=chess.Move.from_uci(top["uci"]),
                    seed=trap.number * 7 + 3, uid="a%d" % trap.number)
    mover = L["black_to_move"] if trap.board.turn == chess.BLACK else L["white_to_move"]
    mistake = st.notation(trap.mistake_text() + "?")
    facts = [
        (L["most_common"], '<span class="mv">%s</span> %s' % (mistake, L["played_in"].format(
            share=st.percent(top["share"])))),
        (L["score"], score_text(trap, L)),
        (L["engine_after"], html.escape(pawns(top["our_cp"]))),
    ]
    facts_html = "".join('<div style="margin-top:3.2mm"><div class="label">%s</div><div>%s</div></div>' % f for f in facts)
    defence = trap.defence or ""
    best = '<span class="mv">%s</span> (Stockfish %s)' % (st.notation(trap.best_text()), html.escape(pawns(trap.record["best_cp"])))
    sections = []
    plain = st.plain_of(trap)
    if plain:
        sections.append('<p style="font-weight:600;font-size:1.18em;line-height:1.3;margin-bottom:4mm">%s</p>' % rich(plain))
    if trap.idea:
        sections.append('<div class="label">%s</div><p style="margin-bottom:3.5mm">%s</p>' % (L["idea"], rich(trap.idea)))
    sections.append('<div class="label">%s</div><p style="margin-bottom:3.5mm">%s</p>'
                    % (L["punishment"], line_html(trap.punish, trap.ply + 1)))
    sections.append('<div class="label">%s</div><p>%s</p>' % (L["defence"], rich(defence) if defence else best))
    body = """
<div class="abs label" style="left:18mm;top:15mm">%(trap)s %(num)02d / %(total)d · %(opening)s</div>
<h2 class="abs" style="left:18mm;top:21mm;width:176mm;font-size:24pt">%(title)s</h2>
<div class="abs mono" style="left:18mm;top:34mm;width:176mm;font-size:8.5pt;line-height:1.7">%(line)s</div>
<div class="abs" style="left:25mm;top:52mm">%(q)s</div>
<div class="abs label" style="left:25mm;top:156mm">%(mover)s</div>
<div class="abs fit" style="left:130mm;top:52mm;width:64mm;height:100mm">
  <div>%(hero)s</div>
  <p style="margin-top:2mm;line-height:1.3">%(went)s</p>
  %(facts)s
</div>
<div class="abs" style="left:25mm;top:164mm">%(a)s</div>
<div class="abs label" style="left:25mm;top:268mm">%(after)s %(mistake)s</div>
<div class="abs fit" style="left:130mm;top:164mm;width:64mm;bottom:20mm;font-size:10pt;line-height:1.4">%(sections)s</div>
""" % {"trap": L["trap"], "num": trap.number, "total": total,
       "opening": html.escape(st.opening_of(trap).replace("'", "’")),
       "title": html.escape(glue(st.title_of(trap).replace("'", "’"))),
       "line": line_html(trap.sans), "q": q, "a": a, "mover": mover,
       "hero": hero(st.percent(st.wrong_share(trap)) + "%"),
       "went": L["went_wrong"].format(n=st.thousands(trap.record["games"])),
       "facts": facts_html, "after": L["after"].capitalize(), "mistake": st.notation(trap.mistake_text() + "?", ink=st.FADED),
       "sections": "".join(sections)}
    return page(body, folio)


def drill_pages(traps, L, folio_for, intro="", per_page=4):
    pages = []
    size = 80
    for start in range(0, len(traps), per_page):
        cells = []
        for index, trap in enumerate(traps[start:start + per_page]):
            x = 25 + (index % 2) * 92
            y = (52 if start == 0 else 30) + (index // 2) * 116
            board = board_block(trap.after, size, uid="d%d" % trap.number)
            cells.append('<div class="abs label" style="left:%dmm;top:%dmm;width:84mm">'
                         '<span style="color:%s">%s %d</span> · %s · %s %s</div>'
                         '<div class="abs" style="left:%dmm;top:%dmm">%s</div>'
                         % (x - 7, y - 7, st.INK, L["drill"], trap.number, L["white_to_move"], L["after"],
                            st.notation(trap.mistake_text(), ink=st.FADED), x, y, board))
        heading = ""
        if start == 0:
            heading = '<h2 class="abs" style="left:18mm;top:24mm;width:150mm">%s</h2>' % html.escape(L["drills"])
            if intro:
                heading += ('<p class="abs" style="left:94mm;top:25mm;width:100mm;font-size:10pt;line-height:1.4">%s</p>'
                            % rich(intro))
        pages.append(page(heading + "".join(cells), folio_for(len(pages))))
    return pages


def answer_pages(traps, L, folio_for, per_page=12):
    pages = []
    for start in range(0, len(traps), per_page):
        rows = []
        for trap in traps[start:start + per_page]:
            _, _, plies = st.catch(trap)
            rows.append('<tr><td class="mono" style="padding-top:.8mm">%d</td>'
                        '<td><div class="mono" style="font-size:8.5pt;line-height:1.7">%s</div>'
                        '<div style="margin-top:1mm">%s</div></td></tr>'
                        % (trap.number, line_html(trap.punish[:max(plies, 1)], trap.ply + 1),
                           rich(getattr(trap, "key", "") or st.plain_of(trap))))
        heading = ('<h2 class="abs" style="left:18mm;top:24mm;width:150mm">%s</h2>' % html.escape(L["answers"])
                   if start == 0 else "")
        body = """
<style>.key td { border-top: 0.35mm solid #CFC9BB; padding: 2.6mm 3mm 2.6mm 0; vertical-align: top; font-size: 10.5pt; line-height: 1.35; }</style>
%s<div class="abs fit key" style="left:18mm;top:%dmm;width:176mm;bottom:24mm">
<table style="width:176mm"><colgroup><col style="width:12mm"><col></colgroup><tbody>%s</tbody></table></div>
""" % (heading, 50 if heading else 24, "".join(rows))
        pages.append(page(body, folio_for(len(pages))))
    return pages


# ---------------------------------------------------------------- assembly

def others_page(meta, others, L, folio):
    """Sampler closing page: the traps that are not in this PDF, titles only."""
    half = (len(others) + 1) // 2
    cols = []
    for chunk in (others[:half], others[half:]):
        cols.append("".join(
            '<div style="display:grid;grid-template-columns:8mm 1fr;padding:1.1mm 0;border-top:0.35mm solid #CFC9BB;'
            'font-size:9pt;line-height:1.25"><span class="mono faded" style="font-size:7.5pt;padding-top:.4mm">%02d</span>'
            '<span>%s</span></div>' % (t.number, html.escape(t.name.replace("'", "\u2019"))) for t in chunk))
    url = html.escape(meta.get("url", ""))
    body = """
<h2 class="abs" style="left:18mm;top:24mm;width:150mm">%s</h2>
<p class="abs" style="left:18mm;top:44mm;width:140mm;font-size:12pt;line-height:1.5">%s</p>
<div class="abs" style="left:18mm;top:84mm;width:84mm">%s</div>
<div class="abs" style="left:110mm;top:84mm;width:84mm">%s</div>
<div class="abs" style="left:18mm;top:222mm;width:176mm">
  <div class="label">%s</div>
  <p class="serif" style="font-size:22pt;line-height:1.1;margin-top:1mm">%s</p>
  <p class="mono" style="font-size:9pt;margin-top:2mm"><a href="%s" style="color:%s">%s</a></p>
</div>
<p class="abs serif" style="left:18mm;top:262mm;width:150mm;font-size:12pt;line-height:1.25">%s</p>
""" % (html.escape(L["others"].format(n=len(others))), rich(meta.get("cta", "")), cols[0], cols[1],
       html.escape(L["others_price"]), html.escape(meta.get("price", "")), url, st.INK, url,
       html.escape(meta.get("tagline", "")).replace("'", "\u2019"))
    return page(body, folio)


def book(data, meta, traps, others=None, total=None):
    """With `others` (the traps left out) this is the free sampler: no
    at-a-glance table, "Trap 19 of 23" on the pages, a closing page."""
    L = labels(meta)
    title = meta.get("title", "")
    sections = []          # lists of page html; folios are filled after counting
    counter = {"n": 1}

    def folio_factory():
        def make(_index):
            counter["n"] += 1
            return ("Trickfish · %s" % html.escape(title), str(counter["n"]))
        return make

    folio = folio_factory()
    pages = [cover(data, meta, traps, L)]
    pages.append(prose_page(L["contents_method"], meta.get("method", []), False, folio(0)))
    pages.append(prose_page(L["contents_usage"], meta.get("usage", []), True, folio(0)))
    if others is None:
        pages += glance_pages(data, traps, L, folio)
    for trap in traps:
        pages.append(trap_page(data, trap, total or len(traps), L, folio(0)))
    pages += drill_pages(traps, L, folio, meta.get("drills_intro", ""))
    pages += answer_pages(traps, L, folio)
    pages.append(prose_page(L["about"], meta.get("fineprint", []), True, folio(0)))
    if others:
        pages.append(others_page(meta, others, L, folio(0)))
    return document(title or "Trickfish", pages)


def slug(data, meta):
    return meta.get("slug") or "trickfish-%s-%s" % (data.get("color", "white"), data.get("band", ""))
