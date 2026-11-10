# PDF copy: 1.e4 e5 Traps for White

Paste-ready text for the rebuilt PDF (edit-1, fix 20). Voice: [voice.md](voice.md). Numbers are from `packs/e4e5-white-1200/traps.json` via `trappack_render.load`. Alternative-move evals marked "SF d16" were checked with `/usr/games/stockfish` at depth 16, the same depth the pack uses.

Six traps have fewer than 50 games after the most common mistake, so their pages should show points, as the cards do: Trap 2 (47 from 48), Trap 4 (28 from 38), Trap 9 (19½ from 30), Trap 10 (17 from 20), Trap 17 (42½ from 49) and Trap 21 (22 from 35).

---

## (a) Cover

**Title**
```text
1.e4 e5 Traps for White
```

**Subtitle**
```text
23 traps that 1200–1599 players fell for, found in 902,003 Lichess games and checked by Stockfish 16
```

**Tagline** (replaces "Trickfish finds the move your opponent will get wrong")
```text
Stockfish finds the best move. We find the one they get wrong.
```

**Stat row:** `23` traps · `902,003` Lichess games · `1200–1599` both players

---

## (b) How this pack was made

```text
We started with 902,003 rated Lichess games from October 2026 that opened 1.e4 e5. Both players were rated 1200–1599, and every game was blitz, rapid or classical. No bullet. The games come from a large sample of that month's database, which Lichess publishes under CC0.

Then we walked the opening tree from White's side. White only plays moves within half a pawn of Stockfish 16's best, so you never have to gamble to set these traps.

At each position with Black to move, we compared what Black played with what Stockfish thinks of each reply. A position counts as a trap when at least 15% of the players who reached it chose a reply that costs 1.2 pawns or more, and White then scored at least 60% in the games after the most common of those mistakes. 38 positions passed. We picked 23 for this pack.

Some of these positions are common and some are rare. The busiest was reached in 6,076 games, the quietest in 100. Every page gives its number, so you can judge the sample yourself.
```

---

## (c) How to use it

```text
- Play through each trap once on a real board. Then do the drills at the back without looking.
- Import the PGN into a Lichess study or a Chess.com library, and come back to it a week later.
- Learn the best defence too. The traps are sound, so the right reply doesn't refute them, but you should know what comes next. Every page shows it with Stockfish's verdict.
- The numbers come from 1200–1599 games only. Expect stronger players to fall for these less often.
```

---

## (d) About the numbers

```text
Went wrong: the share of games reaching the position in which Black chose a reply that costs at least 1.2 pawns by Stockfish's count. We only count replies played in at least 20 games and at least 2% of the games there.

Most common mistake: the most-played of those replies. Its share is part of "went wrong", not the same number.

White's score: White's points per game in the games after the most common mistake (a win is 1, a draw ½, a loss 0). It's a score, not a win rate.

Under 50 games: when the most common mistake was played in fewer than 50 games, we give White's points instead of a percentage, for example 42½ points from 49 games. A percentage would look more precise than the sample allows.

Engine: Stockfish 16 at depth 16, in pawns, from White's point of view. "Mating" means Stockfish found a forced mate.

These numbers describe games that already happened. They aren't a promise about your next one.
```

---

## (e) Drills intro

```text
Each diagram is the position right after your opponent went wrong. White to move. Find the punishment without looking back. The answers are at the end.
```

---

## notes.json: suggested replacements

"keep" means the current text is true and in voice. Each "why" note says what was wrong, and gives the engine check where there was one. Don't merge the "why" notes; they're for whoever does the merge.

| # | Field | Suggested text | Why |
| --- | --- | --- | --- |
| 1 | name, plain | keep | |
| 1 | idea | After 7.Qf3+ the knight on d5 is pinned and attacked twice. Only 7...Ke6 keeps it. 7...Ke8 and 7...Qf6 look natural, but 8.Bxd5 wins the piece back with a pawn extra, and Black's king has lost the right to castle. 7...Kg8?? is already lost. | 7...Qf6 blocks the check. It isn't a "retreat". |
| 1 | defence | 7...Ke6! 8.Nc3 Ncb4 holds the d5 knight (Stockfish +1.0). White has attacking play for the piece. | 8...Nce7 is +2.4 at SF d16, so it doesn't belong next to Ncb4 (+1.0). "Easy" overclaims. |
| 2 | name, plain | keep | |
| 2 | idea | 9...Qxd5?? takes the bishop, but 10.Qxd5+ takes the queen back, and the king can't recapture because the c3 knight guards d5. Black is a queen for a bishop down. 9...Ke7?? is even worse and gets mated. | "The knight on c3 protects the queen" doesn't make clear which queen. |
| 2 | defence | 9...Kd6! is forced, and White keeps a strong attack (Stockfish +1.9). | 10.Qf7 is only Stockfish's third choice at d16 (+1.5; 10.Qd1 is +1.9). "Ferocious" overstates. |
| 3 | name, plain | keep | |
| 3 | idea | After 7.Nxh8 the white knight is stuck in the corner, and 7...Nxe4 looks like the natural way to keep attacking. It opens the light squares instead. 8.Qh5+! g6 9.Nxg6 gets the knight out with tempo. After 9...hxg6 10.Qxg6+ Kd8 11.Qg8+ Qe8 12.Qxe8+ Kxe8 the queens are off, Black's attack is gone and White stays clearly ahead. | "Black is already down an exchange" isn't true in the diagram. Black is a full rook down until the h8 knight falls. |
| 3 | defence | 7...Bb6 is Black's best, and White is still clearly better (Stockfish +1.4). | Adds the eval the page shows anyway. |
| 4 | name | keep | |
| 4 | idea | With the king stuck on f8, 6...Bxf2+? gives a bishop away: 7.Kxf2 and Black has no follow-up. 6...h6? fails too, to 7.Nf7, which hits the queen and the h8 rook. | "Just" cut. "Too slow" was vague. SF d16: 6...h6 7.Nf7 is +3.7. |
| 4 | defence | 6...Qe7 keeps Black in the game, but White stays better (Stockfish +1.5). | Adds the eval. |
| 4 | plain | 6...Bxf2+ gives a bishop away for nothing. | "The copycat check just gives a bishop away" uses filler "just". |
| 5 | name, idea, plain | keep | Checked: 6.Qd5 Bxf2+ 7.Kf1 O-O 8.Qxe4, and Black can't meet both threats. |
| 5 | defence | 5...Nc5 or 5...d5 keeps Black in the game, though White stays better (Stockfish +1.2). | SF d16: Nc5 +1.2, d5 +1.3. "Afloat" undersold how much better White is. |
| 6 | name | Giuoco Piano: the queen on b3 | "The b7/f7 queen" reads like a label, not a name. |
| 6 | idea | 8...Bg4? looks active, and it's the most popular move here. 9.Qb3! attacks b7 and lines up with the c4 bishop against f7. Black loses at least a pawn. | 61% played it, which is worth saying. "And gets a bad position" adds nothing. |
| 6 | defence | 8...Nf6 meets the plan (Stockfish +0.6). | 8...Na5 is +1.5 at SF d16, a full pawn worse than 8...Nf6 (+0.5). |
| 6 | plain | keep | |
| 7 | name | keep | |
| 7 | idea | 5...Nf6? leaves the c5 bishop with no defender. 6.Nxc6! bxc6 7.Bxc5, and White is a piece up. (6...dxc6 and 6...Bxe3 lose too.) | "Trade off the d4 knight with tempo" misdescribes 6.Nxc6, and 6...bxc6 isn't forced (edit-1, fix 6). "Simply" cut. |
| 7 | defence | 5...Qf6 defends everything, and it was the most popular reply. | 32% chose it, the largest share. |
| 7 | plain | 6.Nxc6 and 7.Bxc5 win the bishop nobody guarded. | Smoother than "the bishop the knight trade left hanging". |
| 8 | name, plain | keep | |
| 8 | idea | 6...Nh5? puts the knight on the rim, and 7.g4! hits it at once: f4, f6 and g3 are all covered. Black can save it only with 7...Qh4 8.Be3 c5 9.Qe4 g6 10.Nc3 Ng7, and Stockfish rates the result clearly better for White. | Now matches the Day 11 post. The knight can be saved, at a price. |
| 8 | defence | 6...c5 (Stockfish's choice) or 6...Ng8 avoids the trap, though White keeps an edge (Stockfish +1.6). | Best defence still leaves White +1.6 (pack data). SF d16 has 6...Ng8 at +1.9. |
| 9 | name, plain | keep | |
| 9 | idea | The same idea one move later, and this time the knight is lost: 7...Nh5? 8.g4! f6 9.gxh5. | Same claim, tighter. |
| 9 | defence | 7...Ng8 is the only safe retreat. 7...Nd5, 7...Ng4 and 7...Ne4 all drop the knight to the queen. Even after 7...Ng8, White is clearly better (Stockfish +2.4). | SF d16: Nd5 +4.9, Ng4 +4.3, Ne4 +4.8, Ng8 +2.5. Data caution for the merge: White scored 19½ points from 30 games after 7...Nh5, and 66% from 40 after 7...Ng8. That's no practical difference, so consider dropping this trap in a later pack. |
| 10 | name, idea, plain | keep | Checked: after 7...b6 8.Qd5, Qxf7# and Qxa8 are both threats. |
| 10 | defence | 7...d6 is correct, and White still has an edge (Stockfish +1.5). | Adds the eval. The mistake sample is 20 games (17 points), so the page should show points. |
| 11 | name, defence, plain | keep | |
| 11 | idea | Recapturing 5...Nxd8? gives up the e5 pawn: 6.Nxe5 and White is a clean pawn up. In these games, though, White scored about the same after the correct 5...Kxd8 (61%), so at this level the pawn hasn't turned into points. | White scored 60.9% after 5...Nxd8 and 61.1% after 5...Kxd8. Saying so is honest and on voice. |
| 12 | all | keep | |
| 13 | name, defence, plain | keep | |
| 13 | idea | With ...d6 played, the knight on c6 is pinned to the king. After 5...Bg4? 6.d4 Bxf3 7.gxf3 Bb6 8.d5 the pinned knight is lost. 5...Nf6? reaches the same position as Trap 14. | Same board as Trap 14 after 5...d6 (python-chess). A coach will notice, so say it first. |
| 14 | name | Ruy Lopez: the c6 pin by another road | "The same pin again" undersells the fact that it's the same position. |
| 14 | idea | 5...d6? opens the diagonal and pins Black's own c6 knight to the king. 6.d4 Bb6 7.d5 wins it for a pawn. This is the same position as Trap 13 after 5...Nf6. | "Wins a piece" leaves out 7...Nxe4, which wins a pawn back. |
| 14 | defence, plain | keep | |
| 15 | name, defence, plain | keep | |
| 15 | idea | 5...d5? defends the knight on e4 but leaves Black's king in the centre. 6.d3 kicks the knight, and wherever it goes, White wins material in the centre. After 6...Nxf2 it even comes with check: 7.Rxe5+ Be7 8.Kxf2. | "As soon as it moves, White takes e5 with check" is only true after 6...Nxf2. SF d16: 6...Nf6 7.Nxe5 (+4.9), 6...Nd6 7.Bxc6+ (+4.2), 6...Ng5 7.Bxg5 (+6.2). Data caution: White scored 66% after 5...d5 and 66% after the harmless 5...Nf6. |
| 16 | name, plain | keep | |
| 16 | idea | 6...Nc6? hits the queen but leaves g7 undefended. 7.Qxg7 attacks the h8 rook, which has no squares, and Stockfish rates the result +5.3 for White. | The g8 knight boxes the rook in (edit-1, fix 5). |
| 16 | defence | 6...d6 is best. White keeps the bishop pair and a clear edge (Stockfish +1.8). | "Covers the dark squares" was vague. Material is level after 6.Qxd4. |
| 17 | name | keep | |
| 17 | idea | Black's knight on e4 blocks the e-file between White's queen on e2 and the e5 knight. Once it moves, any move by the e5 knight is a discovered check. After 5...Nf6?? 6.Nc6+ uncovers check and hits the queen on d8. | The knight isn't pinned against the king: White's own e5 knight is also on the file (edit-1, fix 8). |
| 17 | defence | 5...Qe7 is the fix. It closes the e-file before the knight has to move (Stockfish +1.4). | 5...Be7 loses the knight to 6.dxe4 (SF d16 +3.4). Remove it. |
| 17 | plain | keep | Matches the card. |
| 18 | name, idea, defence | keep | |
| 18 | plain | After the queen trade, e5 falls and Black's king has had to move. | "f7 is next" is false. 6...Be6 covers it (SF d16 +1.9). |
| 19 | all | keep | |
| 20 | name | Bishop's Opening: the queen kick that drops e5 | "With a sting" is a stock phrase. |
| 20 | idea, defence, plain | keep | |
| 21 | name, idea, plain | keep | |
| 21 | defence | 4...O-O is best, but White keeps an edge (Stockfish +1.3). | "Black is fine" is false: the best defence still leaves +1.3 (pack data, SF d16 agrees). |
| 22 | name, idea, plain | keep | |
| 22 | defence | 3...d5! is Stockfish's choice, and it turned up in only about one game in ten. | 10.5% of 6,076 games. The pack knows this, so say it. |
| 23 | name, idea, plain | keep | |
| 23 | defence | 4...Ng8 at once is Black's best, and it was also the most common reply. | 60% played it. |

### `_meta` fields

Replace `_meta.method` with section (b), `_meta.usage` with section (c), and `_meta.fineprint` with section (d). Then set:

- `_meta.subtitle`: `23 traps that 1200–1599 players fell for, found in 902,003 Lichess games and checked by Stockfish 16`
- Cover tagline in the renderer: `Stockfish finds the best move. We find the one they get wrong.`
