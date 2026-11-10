# Route A: Line & Hook (studio-v3)

Renderer: `src/trickfish/studio/` (HTML/CSS/SVG laid out in Python, rendered by Chromium at 2x).
Output: `dist/studio-v3/`, with a review sheet at `dist/studio-v3/contact-sheet.png`.
Rebuild: `PYTHONPATH=src python -m trickfish.studio packs/e4e5-white-1200/traps.json --notes packs/e4e5-white-1200/notes.json --output dist/studio-v3`

## The idea

In chess a *line* is a sequence of moves. In fishing, the line is what the hook hangs from.
So every Trickfish trap is drawn as **one red line, laid by hand across a printed book diagram, which ends in a hook around the piece that gets caught.**
The question card shows the bait (the position, plus how many real players bite).
The answer card is the same page with the line drawn in.

## Three ownable devices (used on every asset)

1. **The hook that holds a piece.** On the answer boards it hangs in the catch square with the victim inside its bend. The avatar is that same device on its own: a red hook holding a knight, on water. The wordmark lockup is a red line dropping from the top edge of the frame into a small hook.
2. **The hatched diagram.** Light squares are bare paper. Dark squares are hatched in ink, as in a printed chess book. The board has a ruled double ink frame, Merida pieces (the classic book-diagram set) and coordinates in mono. It is never a flat grey or coloured board.
3. **Red only as line.** Hook red appears in exactly three places: the punishing line, its split-shot stops and the hook. That holds everywhere, including the lockup and the avatar. No red text, no red numbers, no red highlights.

## Type system

| Role | Face | Notes |
|---|---|---|
| The one big number, titles | **Young Serif** (OFL) | Heavy old-style figures that descend and ascend like a printed catalogue. This is the warm, slightly odd voice that Inter never had. |
| Text | **Schibsted Grotesk** (OFL) | 400 for sentences, 600 for "Black to move." |
| Notation, data, captions | **Martian Mono** (OFL) | Every move and every number with a sample size is set in the mono. |
| Figurines | Merida pieces, inline SVG | Notation uses the same drawn pieces as the diagram (♘f3 style), so no fourth font is needed. |

Each card uses three sizes: **226 / 34 / 19 px** (number / text / mono), a jump of more than 6x from the number to the text.
The store images also keep to three sizes each (thumbnail 172/48/19, cover-1 150/44/17, cover-2 32/13, cover-3 32/17, banner 62/30/16).
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

## Grid (1080 x 1350 cards)

- 64 px outer margins.
- **Score column** (x 52-288). This is a mono score sheet whose rows sit on a 45 px pitch, half a diagram square, so the moves keep time with the ranks beside them.
  - Question: the game score, ending in a bold `?` in Black's slot.
  - Answer: the same score with the mistake filled in (`7…♔e8?`) and the punishment in heavier weight. Earlier moves fade back.
- **Diagram column** (x 296-1016). The board is 8 x 90 px, offset right so the page is asymmetric. Text blocks hang from the c-file line (x 476).
- The number hangs from the left margin above the score column.
- Everything critical sits inside the centred 1080 x 1080 safe zone (y 135-1215): number, sentence, opening name, board, and the source and defence lines.
  - Only non-critical items sit outside it: the lockup and trap number in the top band, and the handle and pack title in the footer.

## Board treatment and the line

- **Hatching:** a -45° ink rule at 30% duty, about 7.8 px pitch at card size, clamped for tiny boards so it never turns to moiré.
- **The line** is built from about 100 short round-capped segments whose width swells and thins (two slow sines plus an entry taper), and it bows slightly between stops. That reads as a nib, not a vector arrow.
- A paper knockout under the line keeps it legible over hatching and pieces, as overprinted diagrams do. Each intermediate stop gets a red split-shot dot.
- **Which line and which hook square is an editorial decision for each trap** (`CATCH` in `studio/__init__.py`). The line follows the punishing piece, and the hook goes on what is actually caught. For example:
  - Trap 17: the queen on d8, hit from c6 during the discovered check.
  - Trap 8: the knight on h5, chased by g4.
  - A fallback rule covers packs that have no art direction yet.
- **The hook always hangs from its eye.** We tried rotating it along the line and it read as a squiggle. A hook is only legible when it hangs, as in the mark.
- **The opponent's mistake** is drawn as a dotted ink wake from an empty ring on the square the piece came from. That puts their move in ink and our line in red.

## Data

Every number comes from `traps.json` and `notes.json`:

| What the image shows | Field |
|---|---|
| "bite" share | `record.error_share` |
| n at the position | `record.games` |
| White's score after the mistake | `top.our_score` |
| n for the mistake | `top.games` |
| Eval after the mistake | `top.our_cp` |
| Best defence and its eval | `record.best_reply_san`, `record.best_cp` |
| Pack totals | `sample_games`, `band`, `engine` |

## The deliverables

- `cards/trap-NN.png`, `trap-NN-answer.png`: 23 pairs, paper ground.
- `x/profile.png`: the hooked knight on water. Tested inside a 48 px circle.
- `x/banner.png`: the tagline in Young Serif, plus a diagram of trap 19 with its line. The bottom-left 300 x 180 is empty.
- `store/thumbnail.png`: "1.e4 e5 Traps for White" on water, with a paper plate.
- `store/cover-1.png`: Plate 3, the Traxler. The longest line in the pack (queen d1-h5-g6-g8-e8) on a paper half-page.
- `store/cover-2.png`: the catalogue. All 23 traps as numbered specimens, each with its bite share.
- `store/cover-3.png`: anatomy of a trap. A field-guide plate with a numbered key: bait, bite, hook, escape.

## How each DON'T is avoided

1. **No Inter, Geist, Roboto, Space Grotesk, Bricolage, Playfair, Instrument Serif or system fonts.** Verified by CDP font listing and in the test suite.
2. **No gradient, glow, blur or soft shadow.** The Merida gradient was stripped. The contact sheet uses `clip-path`, not a shadow.
3. **No rounded cards.** Plates are square-cornered paper. The only round things are genuinely round: the hook, the split-shot, the key discs on cover-3 and the avatar's crop.
4. **No pills, badges, status dots, emoji or icon tiles.**
5. **Not centre-stacked.** Score column plus offset board, with the number hung from the left margin.
6. **The board is a hatched printed diagram**, not grey, Lichess brown or Chess.com green.
7. **Two typefaces plus one mono, three sizes per card, one accent.**
8. **Every red pixel is the line or the hook.**
9. **Every card names an opening, a move and a number with its n.** There is no "level up".
10. **The card adds data the post text won't carry:** the score sheet and the n. No all-caps, no arrows at faces.
11. **Texture belongs to an object.** The hatching is the diagram's dark squares, nothing else.
12. **Every card carries a source line:** n, Lichess, the rating band and Stockfish.

## Self-checks

- **Screenshot test:** with the lockup hidden, the hatched diagram plus the red hook around a piece is not any other brand's card.
- **Median test:** an unprompted generator does not produce a book diagram with a hand-laid fishing line and a score sheet in the margin.
- **300 px thumbnail:** the number, the position and the red hook all survive. The score column and captions do not, and do not need to.
- **48 px avatar:** the red U and the paper knight read as one mark.
