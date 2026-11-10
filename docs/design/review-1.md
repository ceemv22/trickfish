# Review 1: studio-v3, Route A "Line & Hook"

Reviewer brief: art direction and chess correctness. This review does not redesign anything. Every fix below works inside the existing system.
Checked: all 46 cards at full size and in Q/A pairs; the 400 px feed width; 300 px thumbnails; the avatar at 48 px and 32 px in a circle on white and black; the banner under the desktop (134 px) and mobile (80 px) avatar overlap; the Gumroad thumbnail at 250/160/100 px; all three covers. Every trap was replayed from `traps.json` with python-chess (moves, punish line, CATCH route, legality of each route leg).

## Verdict: ship after fixes (do not post any answer card until fixes 1-4 are in)

The system is the strongest round so far, and it is close to the real thing. The hatched book diagram, the hand-laid red line and the hook are an idea that belongs to Trickfish, and they pass the screenshot test: with the lockup hidden, nobody else's card looks like this. The palette is disciplined and there are no gradients, glows, pills or rounded cards. Every number on every card matches `traps.json`. What stops it shipping is the chess, and the chess is what a 2000-rated follower will judge the brand on. The hook geometry makes the red line overshoot the target square on every answer card, so the drawn path is not the move that was played. On #3, #7 and #20 the line passes straight through pieces that are still standing. On #3, #20, #22 and #23 the hook sits on something that is not caught at all: a king, a pawn that is immediately recaptured, a square that is empty, and a path that runs through Black's queen. #3 is also the hero of cover-1. On top of that, the headline "bite" percentage is not the share of the mistake the answer reveals, and the source line is about 7 px tall on a phone. All of this is fixable in the renderer and in the `CATCH` table without touching the visual language. One judgement call remains for the owner: the giant-number-top-left composition is the one part of the layout that is still the median stat card (see nice-to-have 1).

---

## Required fixes (in priority order)

### 1. Hook geometry: the line overshoots the catch square on every answer card (systemic, `draw_catch`)
`draw_catch` ends the red line at the hook's eye. The eye is placed 0.86 of a square *above* and 0.47 of a square *left of* the centre of the catch square. As a result the last leg of every line points at the wrong square, and it often runs through the piece being caught.
- **#1:** Bc4xd5 is drawn as a near-vertical stroke up to the c6/d6 corner. The eye sits on the c6 knight, so it reads as Bxc6.
- **#4:** Kxf2 reads as the king walking up the e-file to e3. The line and the shank also form two parallel red strokes (a tuning fork).
- **#7:** the line crosses the c5 bishop it is supposed to catch, and the bishop is knocked out by the paper halo.
- **#11 and #22:** the caught e5 pawn is almost invisible under the line.
- **#15:** d2-d3 is drawn running on to d5.
- **#17:** Nc6 → d8 is drawn as c6 → c8, straight through the c7 pawn (a rook move, not a knight move).
- **#12, #13, #14:** the last leg runs over the c7 pawn.
- **#23:** the eye lands on the white e5 pawn.
- **#6:** the eye lands on the a8 rook, so it reads as Qxa8.
- **#10:** the a8 rook is hidden under the hook.

**Fix:** keep the hanging hook, but make it smaller (bend radius about 0.33 sq, shank about 0.45 sq) so that its eye sits on the catch square's own top edge, inside the square. Draw the final leg of the line along the true vector of the last move (previous stop → catch square centre). Clip it where it meets the bend, and tie it to the eye with a short vertical snell of about 0.15 sq. Nothing red may cross the caught piece's glyph. The paper knockout must never hide more than 15% of any piece. Re-render all 23 answers plus the banner, thumbnail and covers.

### 2. Lines drawn through pieces that are still on the diagram
The diagram is static, so a route leg that crosses a piece still on the board looks illegal to a chess player, even when the sequence itself is legal.
- **#3 (also cover-1):** the g6→g8 leg goes straight through the g7 pawn. That pawn only leaves during the line (…g6, hxg6).
  - Fix: route d1-h5-g6. If the queen-trade idea is kept, take the line on to e8 by bowing it *around* g7: route through h7 → g8 visually, as a curve that clears the g7 glyph. The simpler alternative is to stop at g6 (see fix 3).
- **#7:** e3→c5 goes through the white knight on d4. The point of the trap is the discovered attack 6.Nxc6 bxc6 7.Bxc5.
  - Fix: allow a two-stroke route for discoveries. Draw stroke 1 as Nd4→c6 with a split-shot on c6, then stroke 2 as Be3→c5 into the hook. Draw stroke 1 first, so stroke 2 visibly starts after d4 is empty, or draw it at 60% weight. Do not draw a single e3-c5 stroke over the knight.
- **#20:** the e5→h8 leg crosses Black's queen on f6, and that leg is not even in the line (see fix 3).

### 3. Hooks that catch the wrong thing (change `CATCH`)
Cover-2 says "The hook marks what it catches." That is false on these cards:
- **#3, Traxler (and cover-1):** the hook closes around the **black king on e8**. That reads as "the king is caught". It is not: 11…Qe8 12.Qxe8+ Kxe8 is a queen trade that kills Black's attack while White keeps the material (the note says exactly this).
  - Fix: either hook the queen on e7, the piece forced to e8 and traded, with the route bowing around g7 as in fix 2, or end at g6 with `(["d1","h5","g6"], "g6", 5)`.
  - In either case, swap cover-1's hero to a trap with a clean win. #17 wins the queen with a discovered check and needs one knight jump. #2 scores 98%.
- **#20:** the route is h5→e5→h8, but the queen never goes to h8. 5.Qxe5+ Qxe5 6.Nxe5 trades queens, and the line to h8 runs through Qf6. The note says the knight on e5 "aims at f7 together with the c4 bishop".
  - Fix: `(["h5","e5"], "e5", 3)` and print 5.Qxe5+ Qxe5 6.Nxe5. Do not hook h8.
- **#22:** the hook is on the e5 pawn, but 4…Nxe5 recaptures it at once. Nothing is won there. The note: "5.d4 and 6.e5 drive both knights back to their home squares."
  - Fix: hook the f6 knight (driven to g8 by 6.e5), print through 6…Ng8, and retitle "Both knights go home".
  - This is the weakest trap in the pack (+1.5, best defence −0.1). Consider leaving it out of the X rotation.
- **#23:** the hook hangs on **e4, an empty square**, and the printed line includes the ugly 6…Qh4+ 7.Kd1. The note says the point is that the f6 knight has to go back to g8.
  - Fix: `(["d1","e2"], "f6", 2)` and print 5.Qe2 Ng8. Never hang a hook on an empty square.
- **#8:** the hook says the h5 knight is won after 7.g4, and the score sheet stops at 7.g4. Stockfish's own line keeps the knight: 7…Qh4 8.Be3 c5 9.Qe4 g6 10.Nc3 Ng7. notes.json repeats the false claim ("7.g4! traps it").
  - Fix: print 7.g4 Qh4 and change the copy to "short of squares", or drop #8 from X and post #9, where 8.g4 f6 9.gxh5 really wins it. The two cards are twins anyway.
  - Correct the PDF note as well.
- **#16:** the hook on h8 says the rook is caught. Stockfish's line saves it with 7…Qf6 8.Qxf6 Nxf6.
  - Fix: hook g7 (the pawn actually taken) with `(["d4","g7"], "g7", 1)`, or print 7.Qxg7 Qf6 so the threat reads as a threat.
  - Change cover-2's caption to "The hook marks the target".

### 4. The "bite" statistic is not the mistake the answer reveals
The question card's number is `error_share`, the sum of *every* reply that loses at least 1.2 pawns. The answer card reveals only `top`, and it never says how often that move was played. A follower who compares the two will feel misled:

| Trap | Bite | Revealed move | Its share |
|---|---|---|---|
| #1 | 65% | 7…Ke8 | 31% |
| #4 | 46% | 6…Bxf2+ | 24% |
| #7 | 24% | 5…Nf6 | 12% |
| #16 | 44% | 6…Nc6 | 25% |
| #17 | 32% | 5…Nf6 | 13% |
| #19 | 20% | 3…g6 | 10% |

Worse, **#21's 31% includes 4…Bxf2+**, after which White scored only **32%** in real games: it is counted as a "bite" in which White mostly loses.
- **Fix:** add the share to the answer card's first caption line, for example "7…♔e8? was played in 31% of 2,404 games". Cover-3 already does this correctly.
- **Fix:** on the question card, change "of 1200–1599 players bite here" to "of 1200–1599 players go wrong here". "Players" also overstates it: these are games that reached the position, not all players in the band.
- **Fix:** for the headline, exclude mistakes after which White scored under 50%. #21 then reads 17%.

### 5. Banner: the tagline says the wrong thing, and the caption sits under the avatar
- **"Stockfish finds the best move. We find the one they miss."** The antecedent of "they" is Stockfish, so it reads as "we find the move Stockfish misses". That claims to beat the engine that verifies every trap. A chess audience will dunk on it.
  - Fix, for example: "Stockfish finds the best move. We find the one they actually play." or "…the mistake they actually make."
- **The mono caption starts at x 340.** The X avatar covers about x 16-390 and the bottom 170 px of a 1500 x 500 header on desktop (134 px avatar plus the ring at 600 px wide), and about the same on mobile. In both simulations the avatar eats the first words: "Opening", and the start of "found in".
  - Fix: start the caption at x ≥ 440, or align it with the board's left edge and right-align it. Better still, delete it: at 16 px it renders at 4-6 px on X and is illegible anyway.

### 6. Text that is too small to matter on a phone (a literal DON'T 12 failure)
At 400 px feed width the card shrinks to 37%. The 19 px mono becomes about 7 px. That covers the source line ("n = 2,404 games… Lichess… Stockfish 16"), the whole score sheet, the best-defence line, the trap number and the footer.
The research requires the data source line, and it is technically present but unreadable where the brand's credibility is meant to come from.
- **Fix:** move the sample size into the 34 px sentence ("65% of 2,404 games went wrong here").
- **Fix:** raise the caption block to at least 28 px (about 10 px on a phone). The space is free: the lower-left quadrant is empty on almost every card.
- The score sheet can stay small: it is a reward for people who open the image.

### 7. "1.e4 e5" reads "I.e4 e5" (thumbnail, cover-1)
Young Serif's old-style **1** is an x-height stroke with a flag. In "1.e4 e5" at Gumroad tile size it reads as a capital I. It is the product's own title.
- This also breaks DO 5 ("moves in notation in the mono or with figurines, never in the body face").
- **Fix:** set "1.e4 e5" with a lining 1 (use `lnum` if Young Serif has it; otherwise draw a lining 1 or set the move numbers in Martian Mono at display size). Keep "Traps / for White" in Young Serif.
- The same 1 makes "16%", "18%", "31%", "61%" and "81%" read as "I6%", "6I%" and so on at 300 px. Apply the same fix to the hero number.

### 8. Titles: duplicates, a wrong title and inconsistent opening names
- **Duplicate titles in one pack:**
  - #1 and #13 are both "The pinned knight."
  - #11 and #18 are both "The wrong recapture." #12 "The automatic recapture" is the same motif again.
  - Rename, for example: #13 "The pin on c6", #18 "The Petrov queen trade", #11 "Knight takes, pawn drops".
- **#4:** the card shows "after 6…♗xf2+?" and the title "The bishop check on f7". The check on f7 was White's 5th move. Retitle "The copycat check on f2".
- **#5:** "The double attack on d5" should be "The double attack from d5". The queen attacks f7 and e4 *from* d5.
- **#15:** "The e-file." is a cryptic two-word fragment. Use "The knight with no way back", or "The e-file pin" if the pin is the point.
- **#3 and #4** are the same opening (4.Ng5 Bc5, Traxler/Wilkes-Barre), but one is labelled "Traxler" and the other "Two Knights". Label both "Two Knights, Traxler".

### 9. Hero numbers built on tiny samples
These answer cards set a 226 px percentage from fewer than 50 games:

| Trap | Score | n |
|---|---|---|
| #10 | 85% | 20 |
| #9 | 65% | 30 |
| #21 | 63% | 35 |
| #4 | 74% | 38 |
| #2 | 98% | 48 |
| #17 | 87% | 49 |

For a brand whose whole claim is "real games", n has to be visible at the same moment as the number.
- **Fix:** below n = 50, set the hero as a count rather than a percentage. For example, #2 becomes "47 of 48 games" in the number position (it is more vivid anyway).
- **Fix:** alternatively, keep those traps out of the X rotation.

### 10. Repeated pictures across the 46 cards
- **#13 and #14** have an almost pixel-identical answer: d2-d4-d5 line, hook on c6.
- **#8 and #9** have the same g2-g4 line and hook on h5, and nearly the same question board.
- **#19 and #20** have the same h5-e5-h8 triangle (until fix 3).
- **#11, #12 and #18** are the same f3-e5 knight stroke after a queen trade on d8.
- Posted in pack order, followers will see what looks like a repost.
- **Fix:** do not post twins within 7 days of each other, and choose a different catch square per twin:
  - #13 → c6, and #14 → e4 (the pawn 7…Nxe4 grabbed) or a different end.
  - #8 → drop (see fix 3).
  - #11 → e5, #12 → c6, #18 → f7, which already differ. Keep it that way.

### 11. Collisions between the trail, the line and the hook
- **#4:** the dotted c5→f2 wake ends on the hook's eye.
- **#12:** the trail ring on d6 sits under the red line.
- **#14:** the d7→d6 dots run under the line.
- **#16, #19, #20 and the banner:** the eye overlaps the g8 knight's head and touches the frame.
- **#3 and #10:** the hook sits on the frame at the top edge or corner.
- **Fix (after fix 1):** run a collision pass in `draw_catch`. Keep at least 0.12 sq of clear paper between the trail ring and the red line, end the trail 0.25 sq before any red, and keep the eye at least 0.1 sq inside the frame.
- **Cover-3:** key disc 1 sits on the h5 queen's crown, and disc 2 sits on the g6 pawn's head. Offset each disc to the square's top-left corner, as discs 3 and 4 already are.

### 12. Literal checklist violations not covered above
- **DON'T 7, "no more than 3 sizes per card":** each card actually uses **five** sizes:
  - 226 (number), 136 (the "%" at .6em), 34 (text), about 29 (the inline move at .86em) and 19 (mono).
  - route-a.md claims three.
  - Fix: set the "%" at 34 px, hung from the number's x-height, and set the inline move at 34 px.
- **DO 6, safe zone:** on every card whose number starts with an ascending old-style figure (6, 8 and so on), the number's top is at **y 127**, which is 8 px above the 135 px safe line.
  - Fix: move the number down by 10 px.
- **DO 4, extreme weight contrast:** Young Serif has only one weight, and the text runs 400/600. There is no 300-vs-800 contrast anywhere. Either accept and document this deviation, or set the sentence at Schibsted 400 and the opening name at Schibsted 800.
- **Route A spec, "the mistake is named in plain words":** the answer card gives only notation plus a short title.
  - Fix: add one plain-words line from the first clause of `notes.json` `idea`, for example "Only 7…♔e6 keeps the d5 knight."
- **Score sheet:** double-digit moves lose their space ("10.♕xg6+" and "11.♕g8+" sit under "8. ♕h5+"). This happens on #3, #6, #12 and #13.
  - Fix: widen the number column from 3.1ch to 3.6ch.
- **Cover-3:** "Stockfish's best" uses a straight apostrophe. It comes from a format string that bypasses `esc()`, while every other card uses ’. "3…g6?, played" also has awkward "?," punctuation.

### 13. Avatar (48 px in a circle)
- **It reads:** a red U holding a white knight head. Good.
- **Red #C4161C on Water #1F3A44 is only about 2.0:1 luminance contrast.** At 32-48 px the hook vibrates and muddies.
- **On X's black "Lights out" theme, the Water disc against #000 is about 1.7:1.** The circle edge disappears, leaving a floating knight.
  - Fix: either lighten the hook (or add a 2 px paper keyline at 800 px scale), or move the ground to paper with an ink knight and a red hook. Test both on #000 and #FFF.
- **The barb is drawn as a separate triangle.** At 800 px there is a visible gap between barb and point (the halo is drawn under the point), which looks like a rendering glitch.
  - Fix: merge the barb and the point into one path.
- **The cropped leader at the top** becomes a red stub plus a dot at 48 px. Either shorten it so the eye starts inside the circle, or remove it.
- **Distinctiveness risk:** a white knight head on a dark disc is also how Lichess's mark reads at feed size. The hook is the ownable part, so keep it thick and dominant.

### 14. Gumroad thumbnail as a grid tile
- **At 250 px** the title and the hook read. The five-row mono spec list (19 px → 4 px) is noise, and the top-right quadrant, about 40% of the tile, is empty water.
- **Below 160 px** only "1.e4 e5 Traps" and a red scrap remain.
- **Fix:** drop the list to at most 2 rows ("23 traps · 902,003 games") at ≥ 40 px, scale the paper plate up to fill the right half from y 360, and fix the "1" (fix 7).
- **The hairline-ruled spec list** is also the attempt-2 Swiss tell coming back. Lose the rules.

---

## Nice-to-haves

1. **The median test is only half passed.** The card's skeleton is the stock social stat card:
   - a giant tight percentage top-left;
   - a two-line label to its right;
   - an image below;
   - a mono source line;
   - a handle footer.

   Strip away the board treatment and it is attempt 2 with a serif, and the owner rejected attempt 2 for "huge tight numbers". The route itself asked for the statistic "set like a caption in a field guide". Without redesigning, consider:
   - dropping the number to about 150 px;
   - hanging it on the board's top-left corner as a plate caption ("Plate 01. 65% go wrong here. n = 2,404.");
   - letting the board be the single dominant element.

   Mock up two cards both ways before deciding.
2. **The hero number bounces.** Old-style figures put the top of the number anywhere from y 127 to y 176 across consecutive cards: "65" ascends and "24" sits low. In a profile grid it looks unaligned. Either use lining figures or optically align the cap line.
3. **The lower-left quadrant (x 52-288, y 650-1200) is dead** on 40 of 46 cards, because short score sheets end at rank 5 or 6.
   - Start the score sheet level with rank 8, which matches the board's top edge and makes the "keeps time with the ranks" idea true.
   - Or use the space for the plain-words line (fix 12).
4. **Black pieces on hatched squares lose figure-ground at 300 px.** Classic diagrams leave a thin paper halo around pieces on dark squares. Add a 1 px (at 90 px/sq) paper stroke around the black glyphs only.
5. **"White's real score" is unclear to non-players.** "White scored 82% after 7…♔e8?" is plainer, and it is how chess databases phrase it.
6. **The two big numbers in a pair mean different things** (bite % on Q, score % on A). In a thread they read as one statistic changing. Consider labelling the answer hero ("scored") in the 34 px line directly beside it, as the question card does.
7. **Cover-2:**
   - The title starts at x 437, which aligns with no column (the board columns start at 64, 297, 531…). Hang it at 531 (column 3) or at 64.
   - "really fall for" is filler. Use "23 traps that 1200–1599 players fall for".
8. **Cover-3:** the "3" key disc floats outside the frame, far from its text. Consider keying the hook from inside h8 once fix 1 shrinks the hook.
9. **Banner:** the board sits 52 px from the top but about 70 px from the bottom including the coordinates. Centre it vertically on the 500 px height.
10. **Stale comment:** the code comment in `studio/__init__.py` says the text "hangs from the d-file line (566)". It actually hangs at x 476. Keep the comment and route-a.md in sync.

## What is good, and must survive the fixes
- The hatched diagram with Merida pieces, the double frame and the mono coordinates is ownable and correct.
- Red appears only as line and hook, everywhere.
- Every number on every card (bite %, n, score %, evals, best defence) matches `traps.json` exactly.
- The dotted ink wake from an empty ring is a lovely and correct device on all 23 cards. It shows the right from-square and to-square every time.
- Q/A pairs are true pairs: same grid, same board, only the reveal added.
- Cover-3 "anatomy of a trap" is the best single piece in the set: correct, specific and properly sourced.
