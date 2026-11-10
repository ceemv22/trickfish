# Route A: Line & Hook (studio-v3)

Renderer: `src/trickfish/studio/` (HTML/CSS/SVG laid out in Python, rendered by Chromium at 2x).
Output: `dist/studio-v3/`, with a review sheet at `dist/studio-v3/contact-sheet.png`.
Rebuild: `PYTHONPATH=src python -m trickfish.studio packs/e4e5-white-1200/traps.json --notes packs/e4e5-white-1200/notes.json --output dist/studio-v3`

## The idea

In chess a *line* is a sequence of moves. In fishing, the line is what the hook hangs from.
So every Trickfish trap is drawn as **one red line, laid by hand across a printed book diagram, which ends in a hook around the piece that gets caught.**
The question card shows the bait (the position, plus how many real games went wrong there).
The answer card is the same page with the line drawn in.

## Three ownable devices (used on every asset)

1. **The hook that holds a piece.** On the answer boards it hangs inside the catch square, eye on the square's top edge, with the target piece (drawn at 66%) in its bend. The avatar is that same device on its own: a thick red hook holding an ink knight, on paper. The wordmark lockup is a red line dropping from the top edge of the frame into a small hook.
2. **The hatched diagram.** Light squares are bare paper. Dark squares are hatched in ink, as in a printed chess book. The board has a ruled double ink frame, Merida pieces (the classic book-diagram set) and coordinates in mono. It is never a flat grey or coloured board.
3. **Red only as line.** Hook red appears in exactly three places: the punishing line, its split-shot stops and the hook. That holds everywhere, including the lockup and the avatar. No red text, no red numbers, no red highlights.

## Type system

| Role | Face | Notes |
|---|---|---|
| The one big number, titles | **Young Serif** (OFL) | Set with `lnum` (lining figures) everywhere: the old-style 1 read as "I" at thumbnail size ("I.e4 e5", "6I%"). Lining figures also stop the hero from bouncing between cards. |
| Text | **Schibsted Grotesk** (OFL) | 400 for sentences, 600 for "Black to move." |
| Notation, data, captions | **Martian Mono** (OFL) | Every move and every number with a sample size is set in the mono. |
| Figurines | Merida pieces, inline SVG | Notation uses the same drawn pieces as the diagram (♘f3 style), so no fourth font is needed. |

Each card uses three sizes: **226 / 32 / 19 px**.
- 226 is the hero number only.
  - **Documented exception:** the hero and its "%" (or "½") are one lockup. The superscript is Young Serif at 0.42 of the hero (95 px), top-aligned to the figures' cap height, as financial print sets it.
  - The gap is calibrated per last figure (`SUPER_KERN`): the ink gap was measured on every rendered card and is 9.5–10.5 px on all 42 heroes that carry a superscript.
  - A legible number beats the three-size rule.
- 32 is everything that matters: the sentence (with the sample size), the opening or title, inline moves, the plain-words note, the best defence and the source line. That is about 12 px on a phone at 400 px feed width.
- 19 is reserved for details for people who open the image: the score sheet, the coordinates, the trap number and the footer.

Weight contrast (DO 4) is a documented deviation: Young Serif has one weight, so the contrast is between the 226 px heavy serif and 400-weight 32 px grotesk, not 300 against 800.
The store images also keep to three sizes each (thumbnail 148/48/19, cover-1 150/44/17, cover-2 32/13, cover-3 32/17, banner 62/30/16).
The fonts are self-hosted from `@fontsource` 5.3.0 in `assets/fonts/<family>/` with their OFL licences.
The renderer was checked through the Chrome DevTools Protocol (`CSS.getPlatformFontsForNode`): only Young Serif, Schibsted Grotesk and Martian Mono render, with no system fallbacks.

## Palette

| Token | Hex | Use |
|---|---|---|
| Bait paper | `#EEEAE0` | Card ground, diagram paper, plates |
| Ink | `#15130F` | Type, hatching, pieces, frame |
| Faded ink | `#6F6A5F` | Ink at roughly 60%, for secondary data and coordinates (a tint of ink, not a second colour) |
| Hook red | `#C4161C` | The line and the hook, nothing else |
| Water | `#1F3A44` | Avatar, Gumroad thumbnail, cover-1 ground |

No gradients. The one gradient in the source Merida SVGs was removed (see `studio/pieces/LICENSE.md`).

## Copy rules

- **Question hero:** the share of games at the position in which Black chose a reply that costs at least 1.2 pawns *and* after which White really scored at least 50% (`wrong_share()`). The sentence reads "of 2,404 games at 1200–1599 go wrong here." Example: #21 drops from 31% to 17%, because 4…Bxf2+ scored only 32% for White.
- **Answer hero:** White's score after the revealed move, with the move's own share in the sentence ("played in 31% of 2,404 games").
- **Small samples:** when the move has fewer than 50 games, the hero becomes White's points, with no "/n" (a half point is the same superscript as "%"). The sentence reads "White scored 19½ points / from 30 games after 7…♞h5? / (24% of 127)." This applies to #2, #4, #9, #10, #17 and #21.
- **Plain words:** every answer card carries a short note naming the mistake in words, from `notes.json` `plain` (falling back to the idea's first sentence).
  - It is set at 32 px in the margin under the score sheet (x 42-262; the score column stops short of the rank coordinates).
  - At most one move per note, at its start.
  - Only full moves (with a move number or a piece letter) go in Martian Mono 400, each as one unbreakable unit with its number. Bare squares ("f7") stay in Schibsted.
  - Line breaks come from real measurements. A `window.__layout()` script on the page, which render.mjs runs after the fonts load, picks the most even breaks such that no line holds a single word unless that word is the move. Hyphenated words use a non-breaking hyphen.
  - All 23 notes were checked. Three needed copy changes to meet the rule at this width; see the review-2 notes below.
- **Tagline:** "Stockfish finds the best move. We find the one they get wrong."

## Grid (1080 x 1350 cards)

- 64 px outer margins.
- **Score column** (x 46-288; the note under it runs x 42-262). This is a mono score sheet that starts level with rank 8, with rows on a 45 px pitch (half a diagram square), so the moves keep time with the ranks beside them. The number column is 3.6ch wide, so "10." keeps its space. On answer cards the plain-words note sits at the foot of the column, level with the board's bottom edge. When the score is long, the earliest opening moves are dropped to make room.
  - Question: the game score, ending in a bold `?` in Black's slot.
  - Answer: the same score with the mistake filled in (`7…♔e8?`) and the punishment in heavier weight. Earlier moves fade back.
- **Diagram column** (x 296-1016). The board is 8 x 90 px, offset right so the page is asymmetric. Text blocks hang from the c-file line (x 476).
- The number hangs from the left margin above the score column. Its top is at y ~141-153, inside the safe zone.
- Everything critical sits inside the centred 1080 x 1080 safe zone (y 135-1215): number, sentence, opening name, board, and the source and defence lines.
  - Only non-critical items sit outside it: the lockup and trap number in the top band, and the handle and pack title in the footer.

## Board treatment and the line

- **Hatching:** a -45° ink rule at 30% duty, about 7.8 px pitch at card size, clamped for tiny boards so it never turns to moiré.
- **The line** is built from about 100 short round-capped segments whose width swells and thins (two slow sines plus an entry taper), and it bows slightly between stops. That reads as a nib, not a vector arrow.
- A paper knockout under the line keeps it legible over hatching and pieces, as overprinted diagrams do. Each intermediate stop gets a red split-shot dot.
- **Which line and which hook square is an editorial decision for each trap** (`CATCH` in `studio/__init__.py`, keyed by the trap's move line). The line follows the punishing piece, and the hook goes on a piece: the one actually won, or the one the punishing move targets. It never goes on an empty square or on a piece that survives as if it were won. A test enforces this for the whole pack.
  - **Multi-stroke routes:** a discovery is drawn as two strokes. The first stroke is lighter and ends in a split-shot; the second runs into the hook. Examples: #7 Nd4→c6 then Be3→c5, #22 f4→e5 then e4→e5→f6, #23 Qd1→e2 then the e5 pawn's attack on f6.
  - **Waypoints** bend a line round a piece still on the diagram. #3's queen tour bows round g7, and its hook is on the black queen that is traded off on e8. The king is not the catch.
  - **Drop mode:** when the final stroke ends on a waypoint, the line runs to it and then drops vertically into the hook's eye. The hook is mirrored when the drop is right of the square's centre.
    - This is used on #3: g8→f8 along the back rank, stopping at the e8/f8 boundary, then down into the hook on the e7 queen.
    - It reads as "the queen is met on e8" (11…Qe8 12.Qxe8+).
    - It was checked at 300 px and in the cover-2 cell.
  - **Twins get different catch squares** where chess allows. #13 is drawn as d2-d4-d5-c6 (10.dxc6); #14 shows only the threat d2-d4-d5 into c6. #11 → e5, #12 → c6, #18 → f7.
  - A fallback rule covers packs that have no art direction yet.
- **Hook geometry:** the hook always hangs from its eye. It is small (bend radius 0.33 sq, shank 0.48 sq) and sits inside the catch square, tied up by a short snell. The last leg of the line runs along the real direction of the move and is clipped where it meets the hook, so nothing red crosses the caught piece.
- **Collision pass:** the opponent's dotted trail stops 0.25 sq before any red, and its ring moves to keep 0.12 sq of paper from the line. Black pieces get a thin paper edge so they hold on hatching.
- **The opponent's mistake** is drawn as a dotted ink wake from an empty ring on the square the piece came from. That puts their move in ink and our line in red.

## Data

Every number comes from `traps.json` and `notes.json`:

| What the image shows | Field |
|---|---|
| "go wrong" share | `record.replies` where the reply is in `Trap.mistakes` and `our_score` >= 0.5, over `record.games` |
| The revealed move's share | `top.share` |
| The plain-words line | `notes.json` `plain` |
| n at the position | `record.games` |
| White's score after the mistake | `top.our_score` |
| n for the mistake | `top.games` |
| Eval after the mistake | `top.our_cp` |
| Best defence and its eval | `record.best_reply_san`, `record.best_cp` |
| Pack totals | `sample_games`, `band`, `engine` |

## The deliverables

- `cards/trap-NN.png`, `trap-NN-answer.png`: 23 pairs, paper ground.
- `x/profile.png`: the hooked knight on paper, a thick hook with the barb and point as one shape and no cropped leader. Paper keeps the disc edge on X's black theme and gives the red real contrast. An ink knight on paper avoids the white-knight-on-dark-disc look of Lichess. Tested at 32 and 48 px on #000 and #FFF.
- `x/banner.png`: the new tagline plus a diagram of trap 19. The mono caption is gone, so the avatar area (x 16-390, bottom 170 px) is empty.
- `store/thumbnail.png`: "1.e4 e5 Traps" with lining figures on one line, a large paper plate filling the lower right, and two 48 px facts. It reads at 250, 160 and 100 px.
- `store/cover-1.png`: Plate 17, the discovered check that wins the queen, on a paper half-page.
- `store/cover-2.png`: the catalogue. All 23 traps as numbered specimens, each with its go-wrong share.
- `store/cover-3.png`: anatomy of a trap. A field-guide plate with a numbered key: bait, bite, hook, escape.

## How each DON'T is avoided

1. **No Inter, Geist, Roboto, Space Grotesk, Bricolage, Playfair, Instrument Serif or system fonts.** Verified by CDP font listing and in the test suite.
2. **No gradient, glow, blur or soft shadow.** The Merida gradient was stripped. The contact sheet uses `clip-path`, not a shadow.
3. **No rounded cards.** Plates are square-cornered paper. The only round things are genuinely round: the hook, the split-shot, the key discs on cover-3 and the avatar's crop.
4. **No pills, badges, status dots, emoji or icon tiles.**
5. **Not centre-stacked.** Score column plus offset board, with the number hung from the left margin.
6. **The board is a hatched printed diagram**, not grey, Lichess brown or Chess.com green.
7. **Two typefaces plus one mono, three sizes per card, one accent.**
8. **Every red pixel is the line, a split-shot or the hook.**
9. **Every card names an opening, a move and a number, with n in the same sentence.** There is no "level up".
10. **The card adds data the post text won't carry:** the score sheet and the n. No all-caps, no arrows at faces.
11. **Texture belongs to an object.** The hatching is the diagram's dark squares, nothing else.
12. **Every card carries a source line:** n, Lichess, the rating band and Stockfish.

## Self-checks

- **Screenshot test:** with the lockup hidden, the hatched diagram plus the red hook around a piece is not any other brand's card.
- **Median test:** an unprompted generator does not produce a book diagram with a hand-laid fishing line and a score sheet in the margin.
- **300 px thumbnail:** the number (lining figures: 61, 81 and 17 read correctly), the position and the red hook all survive. The score column does not, and does not need to.
- **400 px feed width:** the sentence, the opening, the plain-words note, the best defence and the source line all read at about 12 px.
- **48 px avatar:** the red U and the ink knight read as one mark on both black and white.

## Not posted, or post with care

These are editorial notes for the posting schedule, not renderer issues:
- #22 is the weakest trap in the pack (+1.5; the best defence is -0.1).
- Twins should not be posted within 7 days of each other: #8/#9, #13/#14, #19/#20 and #11/#12/#18.

## Review-2 notes

- **Copy edits beyond the review's wording**, needed to keep every note line at two words or more in a 220 px column at 32 px:
  - #1 "Only 7…Ke6 holds the pinned knight." ("d5" dropped; the hook marks it).
  - #10 "8.Qd5 eyes mate on f7 and the a8 rook."
  - #15 "7.Rxe5+ comes with check when the e4 knight moves."
- Every claim in `plain` was verified with python-chess against `traps.json`.
