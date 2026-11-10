# Review 2: final verification of studio-v3 (Route A, after review 1)

## How this was checked

- **Answer cards:** all 23 viewed at full size.
- **Question cards:** all 23 viewed as a grid at 400 px.
- **Hero numbers:** all 46 cropped and compared side by side, plus 4x zooms of the junction between each number and its suffix.
- **Chess:** every `CATCH` entry replayed with python-chess against `traps.json`: the legality of each drawn leg, which piece sits on each hook square, and pieces standing on the path of each leg.
- **Numbers:** every figure on every card recomputed (bite share, n, score, points, best defence).
- **Small sizes:** feed cards at 400 px; thumbnails at 300 px; the avatar at 48 and 32 px on #FFF and #000; the banner under the desktop (134 px) and mobile (80 px) avatar overlap; the Gumroad tile at 250, 160 and 100 px; covers 1-3.

## Verdict: ship after fixes

Almost all of review 1 has landed:
- Every number on every card is correct.
- 22 of 23 hooks sit on a real piece, and their lines follow legal geometry.
- The hero numbers now use lining figures.
- The 32 px text reads at about 12 px in the feed.
- The banner tagline is fixed, and the area under the avatar is clear.
- The avatar now holds on both white and black.
- The Gumroad tile reads down to 100 px.

Three things still block shipping:
1. The hero suffix ("%", "/n", "½") is broken on every card.
2. The plain-words margin note breaks moves in two places and reads clunky everywhere.
3. One illegal line remains, on #3 (also on cover-2).

All three are renderer or copy fixes. Nothing else needs to change.

---

## Must-fix

### 1. The hero suffix: "%", "/n" and "½" (all 46 cards)

`big_number()` sets the suffix at 32 px on the baseline after 226 px figures, pulled in by a fixed `margin-left:-6px`. The suffix is about 1/7 the height of the figures, so it reads as a footnote mark, not as part of the number. In the feed it is about 12 px against an 84 px number. Because the pull-in is fixed while the last figure's shape varies, it fails in two opposite ways.

**It collides with the last figure.** The suffix overprints a serif, foot or tail:

| Card(s) | Number | Collision |
|---|---|---|
| Q-07 | 24% | "%" overprints the foot serif of the 4 |
| Q-15 | 34% | same |
| Q-16 | 44% | same |
| A-06 | 64% | same |
| A-18 | 64% | same |
| Q-17 | 32% | "%" sits inside the tail of the 2 |
| Q-20 | 32% | same |
| A-05 | 62% | same |
| A-21 | 22/35 | "/" runs into the tail of the 2 |
| A-17 | 42½/49 | "½" is jammed into the tail of the 2 |
| A-08 | 71% | "%" touches the foot serif of the 1 |

**It floats detached.** The "%" sits alone at the bottom right after a 1, a 6 or a 9:

| Card(s) | Number |
|---|---|
| Q-06 | 61% |
| Q-08 | 18% |
| Q-10 | 16% |
| Q-21 | 17% |
| A-11 | 61% |
| A-16 | 81% |
| A-22 | 61% |
| A-07 | 69% |
| Q-12 | 69% |

**The points heroes have their own problem.**
- On A-09 and A-17, "19½/30" and "42½/49" read as "19 … half of 30".
- On A-02, A-04, A-10 and A-21, the "/48" (and so on) restates the n that the sentence already gives ("from those 48 games").

**Fix:**
- Set "%" in Young Serif, lining, at about 0.42 of the hero size (about 95 px).
- Top-align it to the figures' cap height, as a superscript, the way financial print sets it.
- Space it from the last figure's measured right edge, not with a fixed negative margin. A per-figure kerning table is enough:
  - after 1: -0.01em
  - after 2 and 4: +0.05em, which clears the tail and the foot serif
  - after anything else: +0.02em
- Document the hero plus its "%" as one lockup, an exception to the three-size rule. A legible number beats the rule.
- On the points cards:
  - Drop the "/n" suffix.
  - Set "½" as the same superscript.
  - Write the sentence as "White scored 19½ points from 30 games after 7…♞h5? (24% of 127)."
  - This also removes "those", which has nothing to refer to.
- Re-check all 46 heroes in a crop sheet afterwards. No suffix may touch a figure, and every gap should look the same.

### 2. The plain-words margin note (the 23 answer cards)

**(a) Moves break inside the token.** `prose()` wraps each move in a mono span without `white-space:nowrap`. The figurine is an inline-block, so the browser breaks the line straight after it. This is visible on:

| Card | Move | How it renders |
|---|---|---|
| A-07 | 7.♝xc5 | "7.♝ / xc5" |
| A-15 | 7.♜xe5+ | "7.♜ / xe5+" |

Every other note avoids the break only by luck of line length.
- **Fix:** add `white-space:nowrap` to the move span in `prose()`.
- **Fix:** keep the move number with the move. Use "7.♝xc5" as one unbreakable unit, never "7." at the end of a line.

**(b) Mixed mono and sans at 32 px looks clunky.**
- At the same pixel size, Martian Mono 500 is wider, taller and darker than Schibsted 400. Every move, and every bare square ("f7", "e4", "c6", "g7", "h8"), lands as a heavy spot in the middle of a sentence.
- The 200 px column at 32 px holds 9-12 characters per line, so the notes break into stacks of one or two words. Examples:
  - A-02: "takes a / bishop and / loses the / queen."
  - A-07: three of its four lines are mono.

**Fix:**
- In `prose()`, send only full moves to the mono (a move number or a piece letter plus a square). Bare squares stay in Schibsted.
- Set the mono at weight 400, not 500, so it matches the colour of the text around it.
- Allow at most one move per note, at the start of the note, so it sits alone on the first line.
- Rewrite these notes in `notes.json` `plain`:

| Card | Current note | Replacement |
|---|---|---|
| #1 | "The d5 knight is pinned. Only 7...Ke6 holds it." | "Only 7...Ke6 holds the pinned d5 knight." |
| #7 | "6.Nxc6 bxc6 7.Bxc5 wins the bishop." | "7.Bxc5 wins the bishop the knight trade left hanging." |
| #9 | "8.g4 f6 9.gxh5 wins the knight." | "9.gxh5 wins the knight." |
| #14 | "Same pin: 6.d4 and 7.d5 win the c6 knight." | "7.d5 wins the pinned c6 knight." |
| #15 | "When the knight moves, 7.Rxe5+ comes with check." | "7.Rxe5+ comes with check once the knight moves." |
| #22 | "5.d4 and 6.e5 drive the f6 knight back to g8." | "6.e5 sends the f6 knight back to g8." |

- Widen the note to the full score column (x 46-288, 242 px).
- After the change, no note may have a line of fewer than two words, except a line that holds the move alone.

### 3. Trap #3: the last leg is not a legal move (A-03 and cover-2, cell 03)

- **The problem:** the line runs d1-h5-g6, bows round g7 to g8 (that part is correct), and then cuts diagonally from g8 into the hook on the e7 queen. No white piece moves g8→e7: it is neither a queen line nor a knight jump. A chess player reads it as an illegal "Qxe7". In the real line, Black plays 11…Qe8 and the queen is taken on e8 (12.Qxe8+).
- **Fix:** run the final leg along the real back-rank path, g8→f8 (f8 is empty).
  - Stop it at the f8/e8 boundary, so it does not touch the king glyph on e8.
  - Drop a vertical snell down that boundary into the hook's eye on e7.
  - That reads as "the queen is met on e8", which matches the printed 11…Qe8 12.Qxe8+.
- **Implementation:** in `CATCH`, make the stroke `["d1","h5","g6","~g7:-0.5,0","g8","~f8:-0.5,0"]`, and make the hook leg vertical from that last waypoint.
- **Re-render** A-03 and cover-2.
- **If the snell cannot be made to read cleanly at 300 px,** keep #3 out of the X rotation and the cover-2 highlight. The PDF can keep it.

---

## Verified and no longer blocking

- **Lines and hooks:** every hook is on a real piece. Every other leg is a legal move or a legal line of attack (knight attacks drawn straight, as before).
  - The discoveries on #7, #22 and #23 are drawn as two strokes.
  - No red crosses a caught piece.
  - #17's c6→d8 knight attack passes the c7 pawn. Knights jump, so this is legal and acceptable.
- **Data:**
  - The question heroes use `wrong_share`, which leaves out mistakes that did not pay off in practice: #21 is 17% and #20 is 32%.
  - The answer heroes match `top.our_score` or the points total. Each answer sentence states the revealed move's own share and n.
  - Cover-1 (#17), cover-2 and cover-3 match the cards.
- **Feed (400 px):** the sentence, the opening or title, the best defence and the source line all read at about 12 px. The score sheet stays as detail, which is fine.
- **300 px:** the number and the position read. The hook is small at this size, but the line carries it.
- **Avatar:** reads as one mark at 48 and 32 px. The paper disc holds on #000, and the red has real contrast.
- **Banner:** the tagline is fixed, and nothing sits under the avatar on desktop or mobile.
- **Gumroad:** "1.e4 e5 Traps" with a lining 1 reads at 100 px.
