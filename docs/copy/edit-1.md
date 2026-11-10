# Edit 1: copy.md

Edited 2026-11-10 against `research.md`, `voice.md`, the cards in `dist/studio-v3/cards/`, and `packs/e4e5-white-1200/traps.json` + `notes.json` (loaded with `trappack_render.load`; lines checked with python-chess; engine numbers from the Stockfish 16 depth-16 eval cache in `~/.tfcache/evals`).

## Verdict: ship after fixes

The bones are good. Every post fits in 280 characters, links stay out of the question posts, the copy has no em dashes, emoji, hashtags or banned words, and most of the numbers match the data. The best lines sound like a club player wrote them: "the recapture your hand makes on its own", "a bishop on f2 and a lot of confidence", "pins the f3 knight and forgets its own pin", "not everyone found mate in one". A 1400 would stop for these and a coach would trust most of them.

It can't ship as it stands, for three reasons. Several claims are false or misleading: "we found 23" (38 positions passed the filter), "only 34%" (that was the most common reply), "a fifth of a pawn", "71% in those games", "nowhere good to go", "forces bxc6" and "cousin". Then a run of small tics that a reader adds up: colon reveals, a triad of adjectives, "Goodbye, queen.", "etc.", "Boring was right", the Giuoco Piano pun. Finally, the PDF the Gumroad page sells was built from an older `notes.json`, and it contradicts the posts (see fix 20). None of this needs a rewrite. The fixes below are line edits.

## Required fixes

Every replacement below has been length-checked with X's weighting (a link counts as 23). The highest is 275/280.

### Truth

**1. "We found 23" overstates the result.** `traps.json` has 38 positions that passed all three tests, and `notes.json` `_order` picks 23 of them. "We found 23" and "23 positions made it. To get in, a position had to pass three tests" both say that passing the tests got a position into the pack. It didn't.

- Post 1. Quote: `We found 23. This is the first.` → `38 positions passed. We kept 23, and this is the first.` (post is 274/280)
- Gumroad description. Quote: `23 positions made it. To get in, a position had to pass three tests:` → `A position had to pass three tests. 38 did, and we picked 23 of them for the pack.` (the three bullets follow unchanged)

**2. Post 2's "only 34%" is misleading.** 7...Ke6 was played in 828 of 2,404 games, more than any other reply (7...Ke8 had 756). "Only" suggests a minority move, and "probably why" is a guess.
Quote: `It looks suicidal, which is probably why only 34% of games went that way.`
→ `It looks suicidal, yet it was the most common reply, in 34% of games.`

**3. Day 2 morning: "hands Black a fifth of a pawn" is wrong as a cost.** In the cache, Stockfish has +0.19 before 3.Qh5 and −0.18 after it. So the move costs about 0.37 pawns, and Black ends up 0.2 better. "Hands Black a fifth of a pawn" reads as the cost. "That's all." is also a too-neat closing beat.
Quote: `Your coach calls 3.Qh5 a beginner move. Stockfish says it hands Black a fifth of a pawn. That's all.`
→ `Your coach calls 3.Qh5 a beginner move. Stockfish has Black only 0.2 better after it.`

**4. Day 11 evening credits the 71% to the wrong games.** 71% is White's score after 6...Nh5 (256 games), not after 7...Qh4.
Quote: `Black can save it with 7...Qh4 and some contortions, but White scored 71% in those games.`
→ `Black can save it with 7...Qh4 and some contortions, but White scored 71% after 6...Nh5.`

**5. Day 6 evening has three errors.** After 6...Nc6 7.Qxg7, the h8 rook has no legal moves at all (the g8 knight boxes it in), so "nowhere good to go" understates it. "Gains the tempo" is not idiomatic. "Almost two pawns" rounds up, and the card next to it says +1.8.
Quote: `6...Nc6 gains the tempo and gives up g7. 7.Qxg7, and the h8 rook has nowhere good to go.`
→ `6...Nc6 kicks the queen and gives up g7. 7.Qxg7 hits the h8 rook, and the rook has no squares.`
Quote: `Even then Stockfish has White almost two pawns better.` → `Even then Stockfish has White +1.8.`

**6. Day 8: the morning post says White's move loses a piece, and the evening post claims a forced move that isn't forced.**
- Morning. `Scotch, 5.Be3. The most natural developing move on the board loses a piece here.` reads as if 5.Be3 loses a piece, and the most popular move here is 5...Qf6, not a developing move. → `Scotch, 5.Be3. One of Black's most natural developing moves loses a piece here.`
- Evening. After 6.Nxc6, Black can also play 6...dxc6 or 6...Bxe3 (both still lose), so 6.Nxc6 doesn't force bxc6. Quote: `5...Nf6. Then 6.Nxc6 forces bxc6, and 7.Bxc5 takes a bishop nobody was guarding.` → `5...Nf6. After 6.Nxc6 bxc6 7.Bxc5, White has taken a bishop nobody was guarding.`

**7. Day 14 is the same position as Day 9, not its "cousin".** Trap 13 after 5...Nf6 and Trap 14 after 5...d6 have identical FENs (python-chess confirms it; they're the same position by transposition). Day 9's reply already calls 5...Nf6 "worse still", so a coach will notice. Say so, and turn it into credibility.
- Morning. Quote: `Day 9 had a Ruy Lopez pin. This is its cousin.` → `Ruy Lopez again, by a different road. Black to move after 5.c3.`
- Evening. Insert after the first paragraph: `Same position as Day 9 after 5...Nf6.` and change `That's 14 traps in 14 days.` to `14 traps in 14 days.` (248/280).

**8. Day 3 evening: the e-file doesn't "open".** White's own knight still stands on e5. Once Black's knight leaves e4, the e5 knight can move with discovered check. The post also has two jokes ("Nowhere yet." and "Goodbye, queen."), against voice.md's one-joke rule. Keep the first.
Quote: `Nowhere yet. Once it leaves e4, the e-file opens and White's e5 knight moves with discovered check. 6.Nc6+ also hits d8. Goodbye, queen.`
→ `Nowhere yet. Once it leaves e4, White's e5 knight can move with discovered check, and 6.Nc6+ also hits the queen on d8.`

**9. Comment reply: "best play is rare" isn't true.** 3...Qe7 is rare (15%), but 3...Qf6 (60%) is nearly as good. Only 20% of games go wrong.
Quote: `At 1200–1599, best play is rare.` → `At 1200–1599, one Black player in five goes wrong against it.`

**10. Gumroad description: four claims the data doesn't support.**
- `Stronger players fall for these less often.` We have no data above 1599. → `We only measured 1200–1599 games, so expect stronger players to fall for these less often.`
- `you're not lost: every page shows what to do then.` The pages show the best defence and its eval, but most don't show White's follow-up (Trap 3: "7...Bb6 is Black's best, and White is still clearly better."). → `you're not lost. Every page shows that defence and where it leaves you.`
- `you're somewhere between 1200 and 1600 online or at the club.` The band is Lichess ratings, which don't line up with club or FIDE ratings. → `your Lichess rating is somewhere around 1200–1600.`
- `the drills pages work as a worksheet on the most common e5 mistakes at this level.` They're 23 hand-picked positions from a tree walk, not "the most common mistakes". → `the drill pages work as a worksheet of 23 e5 positions where players at this level went wrong.`
- Also: `Then we ran Stockfish 16 over them,` → `Then Stockfish 16 checked the opening positions those games reached,` (Stockfish never analysed 902,003 games.)

**11. README: "you then scored" is false.** The reader didn't score anything. White did, in the sample games.
Quote: `and you then scored 60% or better.` → `and White then scored 60% or better in those games.`
Quote: `23 traps from 902,003 games between 1200–1599 players` → `23 traps from 902,003 Lichess games between players rated 1200–1599`

**12. Alt text: the answer template doesn't fit the Trap 17 card.** Answer cards with fewer than 50 games (`SMALL_SAMPLE` in `studio/__init__.py`) show points, not a percentage. Trap 17's card reads "White scored 42½ points from 49 games after 5...Nf6? (13% of 369)", and Trap 17 goes public on Day 3. Add a second template:
`Chess diagram after {line} {mistake}, with a red arrow for {first punishing move}. Card text: White scored {points} points from {games} games after {mistake}, {share}% of {total}. {one-line idea}. Best defence {best}.`

### AI tells and voice

**13. Bio: drop "Black to move."** (This answers the lead's doubt.) It's confusing. A bio isn't a position, and at the end of the bio it reads like a fragment. It only makes sense next to a diagram. It's also the profile's second joke if the location stays (see fix 21).
Quote: `Stockfish finds the best move. We find the one they get wrong. Opening traps from 902,003 real Lichess games at 1200–1599. Black to move.`
→ `Stockfish finds the best move. We find the one they get wrong. Opening traps that 1200–1599 players fell for, from 902,003 Lichess games.` (137/160)

**14. Post 3 opens with a colon reveal and reads like a spec sheet.** "How a position made the list:" works as a header, not as a first line. Lead with the point.
Quote (whole post) → 
```text
We only kept a position if White never had to gamble.

Every White move stays within half a pawn of Stockfish 16's best. At least 15% of opponents then chose a reply costing 1.2+ pawns, and White scored 60%+ after the most common one. 38 positions passed. 23 are in the pack.
```
(275/280)

**15. Post 4 has a colon followed by a triad, wrongly puts the PGN inside the PDF, and ends on a balanced parallel.** "Next two weeks" is also off by one, since 13 days remain.
Quote: `All 23 are in a 32-page PDF: one page per trap, drills with an answer key, and a PGN for your Lichess study. $14.` → `All 23 are in a 32-page PDF, one page per trap, with drills and an answer key at the back. A PGN for your Lichess study comes with it. $14.`
Quote: `Next two weeks: a trap every morning, the answer every evening.` → `One more trap each morning for the next 13 days, with the answer in the evening reply.` (252/280)

**16. Day 5 morning mentions the pack.** That breaks the morning rule in copy.md itself ("No link, no price, no mention of the pack").
Quote: `The biggest sample in the pack.` + `Stockfish's top answer for Black here turns up in about one game in ten. What's yours?`
→ `Vienna Gambit, 3.f4. Stockfish's top answer for Black turns up in about one game in ten. What's yours?`

**17. Day 3 morning has a colon followed by three adjectives**, which the research checklist bans in so many words.
Quote: `The Petrov: solid, symmetrical, famously dull.` → `The Petrov is supposed to be the dull one.`

**18. Day 13 morning is over-clever wordplay that adds nothing a player can use.** It's a translation fact plus a pun, and the hook is in the data: Black's most popular move here (8...Bg4, 61%) is the mistake.
Quote: `Giuoco Piano is Italian for "quiet game".` / `Black to move. It's about to get less quiet.`
→ `Giuoco Piano, after the bishop trade on d2. Black's most popular move here is a mistake.` / `Black to move.`

**19. A cluster of faux-casual tics.** Each one is fine alone. Together they read like a template.
- Day 2 evening, colon reveal: `3...g6 feels right: kick the queen.` → `3...g6 kicks the queen and feels right.`
- Day 5 evening, colon reveal: `Stockfish wants 3...d5: hit back in the centre.` → `Stockfish wants 3...d5, hitting back in the centre.`
- Day 7 evening, careless "every" (voice.md rule 8) that also contradicts "half": `7...Nxe4 is the move every Traxler player wants, and half of them played it.` → `7...Nxe4 is the Traxler player's reflex, and half of them played it.`
- Day 10, "holds everything" twice, plus "Boring was right", which repeats Day 6's "dull and correct": `4...d6 just holds everything, and it was the most popular reply. Boring was right.` → `4...d6 protects e5, and it was the most popular reply.`
- Day 11 evening, smug wink: `6...c5 (Stockfish's pick) or 6...Ng8 avoids all of it. A knight on the rim, etc.` → `6...c5 (Stockfish's pick) or 6...Ng8 avoids all of it.`
- Day 4 morning, coy teaser with the hook buried behind a caveat: `Only 100 games reached this one. Small sample. Then we saw how most of them went.` / `Ruy Lopez, White just took on e5. Black to move.` → `Ruy Lopez, White just took on e5. Black to move.` / `Only 100 games reached this one, so it's a small sample. Most of them went the same way.`
- Receipt, a "Here's the thing" cousin: `Thanks. Here's how we'd use it.` → `Thanks for buying.`

### Product (not in copy.md, but it blocks shipping the copy)

**20. Rebuild the PDF and PGN from the current `notes.json` before the Gumroad page goes live.** `dist/e4e5-white-1200/*.pdf` and `.pgn` were built at 13:32 from the 9 November notes, and `packs/.../notes.json` changed at 18:16. Problems in the shipped PDF:
- The method page says "every trap here is backed by thousands of real games". voice.md rule 8 calls that false (traps range from 100 to 6,076 games).
- Trap 8 says "7.g4! traps it", but the Day 11 post (correctly) says Black can save the knight with 7...Qh4.
- The cover tagline is "Trickfish finds the move your opponent will get wrong", which differs from ours and makes a promise.
- The trap names in the PGN differ from the cards (for example "Traxler: the greedy knight" vs "Two Knights, Traxler: ...").

## The lead's three doubts

- **Bio ending "Black to move."**: confusing, so cut it (fix 13). Clever lines only work when the reader already has the context, and a profile visitor doesn't.
- **Location "Move 7, Fried Liver"**: keep it, on one condition: it's the profile's only joke once "Black to move." goes. It passes the toaster test, every 1400 knows the Fried Liver, and it points at the pinned post. Don't use the suggested `Lichess, 1200–1599`. A brand name in the location field reads as an affiliation with Lichess, and it's a data point pretending to be a place. If you want plain, leave the field empty.
- **CTA "Buy this"**: right. It's plain, honest, and next to the price. "I want this!" adds a fake exclamation, and "Pay" is cold. Drop the custom fallback "Get the 23 traps": "Get" blurs that it's paid, and it adds nothing.

## Optional improvements

1. **Small samples: use points, the way the cards do.** The cards switch to points under 50 games. The copy still uses percentages: Gumroad's Trap 17 line ("White scored 87% in those 49 games") and Trap 2 line ("98% ... 48 games"), and Day 2's "White only scored 89%" (33 games). Suggested:
   - Day 2: `That came up 33 times, and White scored 29½ points, so at least four people missed mate in one.` (256/280; 3½ points lost means at least four games weren't won.)
   - Gumroad: `White took 42½ points from those 49 games.` and `One where White took 47 points from 48 games. Small sample, so don't get too excited, but it's in here.` That also drops "the position is real", which implies the others aren't.
   - Then make voice.md rule 5 agree with the renderer.
2. **Use one link label.** The posts use "Trap 17 of 23:", "Drill 22 in the pack:", "Drill 20:" and a bare link. research.md says to use the same word for the same thing. Use `Trap N of 23:` everywhere (the fixes above already do for Days 5, 8 and 10).
3. **Gumroad bullets vs. the checklist.** research.md allows bullets "for the file list only", but the description bullets the three tests and the examples too. On a phone those bullets help. Change the rule (bullets ban = posts only), not the page.
4. **The opening sneer.** `Your 1400 opponent hasn't read the opening books.` mocks the opponent, which voice.md rules out, and we can't verify it. Try: `Your 1400 opponent plays a lot of blitz, and blitz builds habits. This pack is about those habits.`
5. **The tagline is a parallel** ("Stockfish finds X. We find Y."). It's a deliberate keeper, so keep it, but treat it as the one parallel the brand gets. Don't add another next to it in the bio, on Gumroad or in the README.
6. **Day 11 morning.** "Pick its new square." leaves out the best move (6...c5 isn't a knight move), so the evening reply looks like a gotcha. Try `Black to move.` or `The knight on f6 is attacked. What do you play?`
7. **Day 6 morning.** "practically asking to be kicked" is stock personification. `White's queen is sitting on d4.` is enough, because the card does the rest.
8. **Bridge to the White buyer.** Every puzzle asks the reader to play Black, but the product is for White. Now and then, end the evening reply with the White-side point, e.g. `As White, this is the trap you set with 7.Qf3+.`
9. **Post 1's link is in Post 4, which isn't an answer reply.** This is fine, since it isn't the hook post. Write it into copy.md as the one deliberate exception so nobody "fixes" it later.
10. **"real" shows up a lot** ("real Lichess games", "real opponents", "White's real score"). Keep it once in the bio and once on Gumroad, and cut it elsewhere.

## What I checked and found correct

- **Lengths.** Bio 137/160, location 19/30. Every post and reply is ≤ 280 (longest original: Day 7 evening at 265). There are no single-character ellipses. The only non-ASCII characters are en dashes and ½, both weight 1.
- **Numbers matching `traps.json`.** 902,003 games: the 1.e4 e5 games in the both-players 1200–1599 file, which comes from the October 2026 dump (README `curl`). Also 2,404 / 65% / 7...Ke8 31% / 756 / 82%; 34% Ke6; 1,572 / 20% / 10% / 85%; 33 games / 89%; 369 / 13% / 49 / 87%; 25% Qe7; 100 / 69 / 30 / 77%; 6,076 / ~1 in 10 for 3...d5; 573 / 45%; 272 / half / 40%; 2,108 / 47%; 315 / a quarter for 5...a6; 1,411 / 71%; 147 / 19%; 23 / 32 pages / 23 drills / answer key / PGN comments.
- **Thresholds.** Within half a pawn (`sound_cp=50`), 15% (`min_error_share`), 1.2 pawns (`mistake_cp=120`) and 60% (`min_score`) all match `trappack.py`. Blitz/rapid/classical with no bullet, and both players in the band, match `lichess_db.py`.
- **Chess.** 4.Qxf7# is mate. After 7.g4 the h5 knight has no safe square. After 5.d3 every knight move allows 6.Nc6+. 4...Qe7 makes exf6 illegal. 9.Nxg6 hits e7. 8.d5 leaves the pinned c6 knight with no moves. After 8.Bxd5 in Trap 1, White is a pawn up.
