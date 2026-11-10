# Trickfish: paste-ready copy

Voice rules: [voice.md](voice.md). Checklist and sources: [research.md](research.md). Revised after [edit-1.md](edit-1.md).
Every number below was recomputed from `packs/e4e5-white-1200/traps.json` with `trappack_render.load`. Shares and scores are rounded to whole percents. Under 50 games we give points instead of a percentage, as the cards do (e.g. 42½ points from 49 games). Cards are in `dist/studio-v3/cards/`: `trap-NN.png` is the question, `trap-NN-answer.png` the answer.

The card already shows the percentage, the game count, the opening and the line, so the posts don't repeat them. A post adds what the card can't: why people fall for it, what the right move was, and how often anyone found it.

---

## 1. X profile

**Display name** (9/50)
```text
Trickfish
```

**Bio** (137/160)
```text
Stockfish finds the best move. We find the one they get wrong. Opening traps that 1200–1599 players fell for, from 902,003 Lichess games.
```

**Location** (19/30)
```text
Move 7, Fried Liver
```
This is the profile's only joke, and it points at the pinned post. If you want something plain, leave the field empty.

**Website:** https://ceemv22.gumroad.com/l/e4e5-traps-white

### Pinned thread (Day 1)

Post 4 carries the link even though it isn't an answer reply. That's deliberate: the hook post (Post 1) has no link, and this is the one exception to the rule in section 2.

**Post 1** · image `trap-01.png`
```text
You know the Fried Liver. Do you know Black's 7th move?

We went through 902,003 Lichess games at 1200–1599 for spots where White plays sound moves and Black keeps going wrong. We kept 23 of them, and this is the first.

Black to move. Answer before you scroll.
```

**Post 2** · image `trap-01-answer.png`
```text
7...Ke6. Walk the king forward and keep the d5 knight. It looks suicidal, yet it was the most common reply, in 34% of games.

7...Ke8 came up 756 times. 8.Bxd5 takes the piece back with a pawn to spare, and Black's king has lost castling.
```

**Post 3**
```text
We only kept a position if White never had to gamble.

Every White move stays within half a pawn of Stockfish 16's best. At least 15% of opponents then chose a reply costing 1.2+ pawns, and White scored 60%+ after the most common one. 38 positions passed. 23 are in the pack.
```

**Post 4**
```text
All 23 are in a 37-page PDF, one page per trap, with drills and an answer key at the back. A PGN for your Lichess study comes with it. $14.

https://ceemv22.gumroad.com/l/e4e5-traps-white

One more trap each morning for the next 13 days, with the answer in the evening reply.
```

---

## 2. Days 2–14

Morning: the question post with the question card. No link, no price, no mention of the pack.
Evening: the answer card, posted as a **reply to the morning post**. The link appears there and nowhere else that day, always labelled `Trap N of 23:`.

Fourteen traps go public (Trap 1 plus the 13 below). Traps 2, 4, 5, 9, 10, 11, 15, 18 and 21 stay in the pack.

### Day 2 · Trap 19 · Bishop's Opening, 3.Qh5

**Morning** · `trap-19.png`
```text
Your coach calls 3.Qh5 a beginner move. Stockfish has Black only 0.2 better after it.

You're Black. Pick your move before you read the replies.
```

**Evening reply** · `trap-19-answer.png`
```text
3...g6 kicks the queen and feels right. The queen takes e5 with check instead, and the h8 rook is next.

3...Nf6?? allows 4.Qxf7# at once. That came up 33 times, and White scored 29½ points, so not everyone found mate in one.

Trap 19 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 3 · Trap 17 · Petrov, 5.d3

**Morning** · `trap-17.png`
```text
The Petrov is supposed to be the dull one.

5.d3 kicks the knight on e4. Where does it go?
```

**Evening reply** · `trap-17-answer.png`
```text
Nowhere yet. Once it leaves e4, White's e5 knight can move with discovered check, and 6.Nc6+ also hits the queen on d8.

5...Qe7 first, then worry about the knight. A quarter of games went that way.

Trap 17 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 4 · Trap 12 · Ruy Lopez, 6.dxe5

**Morning** · `trap-12.png`
```text
Ruy Lopez, White just took on e5. Black to move.

Only 100 games reached this one, so it's a small sample. Most of them went the same way.
```

**Evening reply** · `trap-12-answer.png`
```text
6...dxe5 is the recapture your hand makes on its own. It loses a pawn: 7.Qxd8+ Kxd8 8.Nxe5, and c6 is loose too.

6...Nxe4 takes a pawn back first and Black is fine. 30 of the 100 found it.

Trap 12 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 5 · Trap 22 · Vienna Gambit, 3.f4

**Morning** · `trap-22.png`
```text
Vienna Gambit, 3.f4. Stockfish's top answer for Black turns up in about one game in ten. What's yours?
```

**Evening reply** · `trap-22-answer.png`
```text
Stockfish wants 3...d5, hitting back in the centre. Only 10% of games went that way.

3...Nc6 looks like normal development. Then 4.fxe5 Nxe5 5.d4 Ng6 6.e5, and the f6 knight is back on g8 by move 6.

Trap 22 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 6 · Trap 16 · Three Knights, 6.Qxd4

**Morning** · `trap-16.png`
```text
Three Knights, after the fork trick. White's queen is sitting on d4.

Black to move.
```

**Evening reply** · `trap-16-answer.png`
```text
6...Nc6 hits the queen and gives up g7. 7.Qxg7 hits the h8 rook, and the rook has no squares.

6...d6 is dull and correct (45% of games). Even then Stockfish has White +1.8.

Trap 16 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 7 · Trap 3 · Traxler, 7.Nxh8

**Morning** · `trap-03.png`
```text
Traxler players, this one's yours.

White has taken your rook. You have a bishop on f2 and a lot of confidence. Black to move.
```

**Evening reply** · `trap-03-answer.png`
```text
7...Nxe4 is the Traxler player's reflex, and half of them played it. 8.Qh5+! g6 9.Nxg6 frees the stuck knight with tempo, and the queens come off soon after.

7...d5 was the other popular try. White scored 40% after that one.

Trap 3 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 8 · Trap 7 · Scotch, 5.Be3

**Morning** · `trap-07.png`
```text
Scotch, 5.Be3. One of Black's most natural developing moves loses a piece here.

Black to move.
```

**Evening reply** · `trap-07-answer.png`
```text
5...Nf6. After 6.Nxc6 bxc6 7.Bxc5, White has taken a bishop nobody was guarding.

The most popular reply, 5...Qf6, is also the right one. White scored 47% against it.

Trap 7 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 9 · Trap 13 · Ruy Lopez, 5.c3

**Morning** · `trap-13.png`
```text
Ruy Lopez, 5.c3. Of Black's four most-played moves here, two lose material.

Black to move.
```

**Evening reply** · `trap-13-answer.png`
```text
5...Bg4 pins the f3 knight and forgets its own pin. 6.d4 Bxf3 7.gxf3 Bb6 8.d5, and the c6 knight can't move.

5...Nf6 is worse still by Stockfish's count. 5...a6, asking the bishop first, solves it. A quarter of games went that way.

Trap 13 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 10 · Trap 20 · Bishop's Opening, 4.Nf3

**Morning** · `trap-20.png`
```text
Back to 3.Qh5. The most common answer, 3...Qf6, holds everything.

Then 4.Nf3. Black would like that queen gone from h5. Black to move.
```

**Evening reply** · `trap-20-answer.png`
```text
4...g6 chases the queen and leaves e5 hanging. 5.Qxe5+ forces the queens off, and the knight lands on e5 aiming at f7.

4...d6 protects e5, and it was the most popular reply. As White, you set this one with 4.Nf3.

Trap 20 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 11 · Trap 8 · Scotch, 6.e5

**Morning** · `trap-08.png`
```text
Scotch, 6.e5. The knight on f6 is attacked. What do you play?
```

**Evening reply** · `trap-08-answer.png`
```text
If you went 6...Nh5, 7.g4 leaves the knight no squares. Black can save it with 7...Qh4 and some contortions, but White scored 71% after 6...Nh5.

6...c5 (Stockfish's pick) or 6...Ng8 avoids all of it.

Trap 8 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 12 · Trap 23 · Vienna Gambit, 4.e5

**Morning** · `trap-23.png`
```text
Vienna Gambit accepted, 4.e5. The knight on f6 is attacked, and Black has a clever-looking way to avoid retreating it.

Black to move.
```

**Evening reply** · `trap-23-answer.png`
```text
4...Qe7 pins e5 so the knight can stay. 5.Qe2 breaks the pin, the knight goes to g8 anyway, and Black's queen now blocks its own bishop.

4...Ng8 straight away was the most common move, and the best.

Trap 23 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 13 · Trap 6 · Giuoco Piano, 8.Nbxd2

**Morning** · `trap-06.png`
```text
Giuoco Piano, after the bishop trade on d2. Black's most popular move here is a mistake.

Black to move.
```

**Evening reply** · `trap-06-answer.png`
```text
The tempting one is 8...Bg4, pinning the knight. Then 9.Qb3 hits b7 and lines up with the c4 bishop against f7.

8...Nf6 was the move. 19% of games went that way.

Trap 6 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 14 · Trap 14 · Ruy Lopez, 5.c3 again

**Morning** · `trap-14.png`
```text
Ruy Lopez again, by a different road. Black to move after 5.c3.
```

**Evening reply** · `trap-14-answer.png`
```text
5...d6 opens the diagonal and pins its own c6 knight. 6.d4 Bb6 7.d5 wins it for a pawn. 5...O-O keeps the knight free.

Same position as Day 9 after 5...Nf6.

14 traps in 14 days. The pack has all 23, with drills and a PGN.

Trap 14 of 23: https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Replying to comments

- Right answer: like it, and reply with the line, e.g. `7...Ke6. You'd have been in the 34%.` Use the best-defence share from the data, not 100 minus the card number.
- Wrong answer: like it. No public correction. The evening reply does that for everyone.
- "Isn't 3.Qh5 just bad?": `Stockfish has it at about −0.2 with best play. At 1200–1599, one Black player in five goes wrong against it.`
- Someone finds a mistake in a line: thank them in public and fix the pack.

---

## 3. Gumroad product page

**Name**
```text
1.e4 e5 Traps for White (1200–1599)
```

**Summary** (the line beside the button)
```text
23 sound traps from 902,003 real Lichess games at 1200–1599. A 37-page PDF with drills, plus a PGN.
```

**Additional details**

| Row | Value |
| --- | --- |
| Traps | 23 |
| PDF | 37 pages: one page per trap, 23 drills, answer key |
| PGN | All 23 lines with stats in the comments |
| Games | 902,003 rated Lichess games, October 2026 |
| Rating band | Both players 1200–1599 |
| Time controls | Blitz, rapid, classical. No bullet |
| Engine | Stockfish 16 |
| You play | White, after 1.e4 e5 |
| Refunds | 30 days, no questions |


**Description**

```text
Stockfish finds the best move. We find the one they get wrong.

Your 1400 opponent plays a lot of blitz, and blitz builds habits. This pack is about those habits.

We took 902,003 rated Lichess games from October 2026 that started 1.e4 e5, with both players rated 1200–1599 (blitz, rapid and classical, no bullet). Then Stockfish 16 checked the opening positions those games reached, looking for spots where White's play is sound and Black keeps going wrong.

A position had to pass three tests. 38 did, and we picked 23 of them for the pack.
- Every White move on the way is within half a pawn of Stockfish's best. You never bet the game on a cheap shot.
- At least 15% of the players who reached it chose a reply that costs 1.2 pawns or more.
- White scored 60% or better in the games after the most common of those mistakes. (Score means points per game: a win is 1, a draw ½.)

A few of them:
- Fried Liver, move 7. 2,404 games reached it. Black played 7...Ke8 in 31% of them, and White scored 82% afterwards.
- Ruy Lopez, 6...dxe5. Black made the natural recapture in 69 of 100 games and dropped a pawn. White scored 77%.
- Petrov, 5...Nf6. Only 13% played it, but 6.Nc6+ wins the queen. White took 42½ points from those 49 games.
- One where White took 47 points from 48 games. Small sample, so don't get too excited, but it's in here.

What you get
- A 37-page PDF. One page per trap: the diagram, the moves, how many games got there, how often Black went wrong, White's score, the punishment line and the best defence.
- 23 drills, each set right after the mistake with White to move, plus an answer key.
- A PGN of all 23 with the numbers in the comments. Import it into a Lichess study, Chess.com or ChessBase.

What it won't do
It won't promise you rating points. The numbers describe 902,003 games that already happened, not your next one. We only measured 1200–1599 games, so expect stronger players to fall for these less often. And when someone finds the best defence, you're not lost. Every page shows that defence and where it leaves you.

Who it's for
You play 1.e4, your opponents answer 1...e5, and your Lichess rating is somewhere around 1200–1600. Coaches: the drill pages work as a worksheet of 23 e5 positions where players at this level went wrong.

$14. If it's not for you, ask for a refund within 30 days. No questions.

Game data: Lichess open database (CC0). Engine: Stockfish 16.
```

**Call-to-action button:** `Buy this`
It's plain, honest, and sits next to the price. "I want this!" adds a fake exclamation, and "Pay" is cold.

**Receipt message**
```text
Thanks for buying.

Play through Trap 1 on a real board. Do the drills at the back without looking. A week later, import the PGN into a Lichess study and see what stuck.

Spot a wrong move or a typo in a line? Reply to this email and we'll fix the file.
```

**Refund policy line**
```text
30-day refund, no questions. Reply to your receipt and you get your $14 back.
```
(Gumroad may apply one account-level policy. Set it to the 30-day money-back guarantee so the line matches.)

---

## 4. Alt text for the X cards

**Template, question card**
```text
Chess diagram after {line}, Black to move. Card text: {error%} of {games} games at 1200–1599 go wrong here. {Opening}. Trap {n} of 23, Trickfish.
```

**Template, answer card (50+ games after the mistake)**
```text
Chess diagram after {line} {mistake}, with a red arrow for {first punishing move}. Card text: White's score after {mistake}, {score}%, played in {share}% of {games} games. {one-line idea}. Best defence {best}.
```

**Template, answer card (under 50 games: the card shows points)**
```text
Chess diagram after {line} {mistake}, with a red arrow for {first punishing move}. Card text: White scored {points} points from {games} games after {mistake}, {share}% of {total}. {one-line idea}. Best defence {best}.
```

**Example, `trap-19.png`**
```text
Chess diagram after 1.e4 e5 2.Bc4 Bc5 3.Qh5, Black to move. Card text: 20% of 1,572 games at 1200–1599 go wrong here. Bishop's Opening. Trap 19 of 23, Trickfish.
```

**Example, `trap-19-answer.png`**
```text
Chess diagram after 1.e4 e5 2.Bc4 Bc5 3.Qh5 g6, with a red arrow showing the queen taking on e5 and hitting the rook on h8. Card text: White's score after 3...g6, 85%, played in 10% of 1,572 games. 4.Qxe5+ forks the king and the h8 rook. Best defence 3...Qe7.
```

**Example, `trap-17-answer.png` (small sample)**
```text
Chess diagram after 1.e4 e5 2.Nf3 Nf6 3.Nxe5 Nxe4 4.Qe2 d5 5.d3 Nf6, with a red arrow for 6.Nc6+. Card text: White scored 42½ points from 49 games after 5...Nf6, 13% of 369. 6.Nc6+ uncovers check and hits the queen. Best defence 5...Qe7.
```

---

## 5. README intro

```markdown
**Trickfish finds the opening traps your opponents fall for.** We take real Lichess games in one rating band and keep a position only when your moves stay within half a pawn of Stockfish's best, at least 15% of opponents chose a reply that costs them 1.2+ pawns, and White then scored 60% or better in those games.

First pack: **[1.e4 e5 Traps for White](https://ceemv22.gumroad.com/l/e4e5-traps-white)**. 23 traps from 902,003 Lichess games between players rated 1200–1599, as a PDF with drills and a PGN. $14.
```

---

## 6. Days 15–30 (text only, no new trap cards)

Same slots as section 2 (morning and evening, UTC times in `social/queue.json`). Days 15–30 use no cards. Polls are text-only, so the position is written out in the post. A poll's answer goes out in the evening as a reply to it, with no link: posts that contain a URL cost far more to publish, so the only links in this section are the two reminders (Days 20 and 28).

Every number was recomputed from `packs/e4e5-white-1200/traps.json` and `notes.json` with `trappack_render.load`. Facts used:

- Vienna Gambit 3.f4: 6,076 games, 25% (one in four) chose a reply costing 1.2+ pawns. 3...Nc6 came up in 1,087, the largest single mistake count in the data. 3...d5 (Stockfish's pick) in 635. 3...Bb4: 251 games, Stockfish +2.8 for White, White scored 55%.
- Pack positions (23): in 13 the most common reply is Stockfish's top move, in 6 it is a mistake of 1.2+ pawns, in 4 it is neither. 7 positions have under 200 games (smallest 100, largest 6,076).
- 38 positions passed; the 15 not in the pack range from 85 to 1,098 games; four of them are under 100 (85, 90, 92, 95); the smallest pack position has 100.
- 1.e4 e5 2.Nf3 Nc6 3.d4 d6 4.dxe5 dxe5 5.Qxd8+: 1,044 games. 5...Kxd8 579 games, White scored 61%. 5...Nxd8 465 games, White scored 61%.
- Petrov 3.d4 d6 4.dxe5 (164 games): 4...dxe5 91 games (55%), White scored 64%, costs 1.4 pawns. 4...Nxe4 68 games (41%), Stockfish's pick.
- Ruy Lopez 4.O-O Nxe4 5.Re1 (537 games): 5...Nd6 174 (32%), 5...Nf6 155 (29%, costs 0.3), 5...d5 108 (20%, costs 2.3, White scored 66%), 5...f5 46 (9%).
- Fried Liver 7.Qf3+ (2,404 games): 7...Kg8 came up 228 times and White scored 228 points. 7...Ke8: 756 games, White scored 82%.
- Pack by move 2: 18 after 2.Nf3, 3 after 2.Bc4, 2 after 2.Nc3. By page title: Scotch 5, Ruy Lopez 4, Bishop's Opening 3.

### Day 15 · Stat: the busiest position

**Morning**
```text
The busiest position in the pack is the Vienna Gambit after 3.f4. 6,076 games reached it, and in about one in four Black chose a reply that costs 1.2+ pawns.

The most common, 3...Nc6, came up 1,087 times. That's more than any other mistake in the data.
```

### Day 16 · Poll: Petrov, 3.d4

**Morning (poll)**
```text
1.e4 e5 2.Nf3 Nf6 3.d4 d6 4.dxe5

Black to move. Which would you play?
```
Poll options (300 minutes): 4...Nxe4 | 4...dxe5 | Something else

**Evening reply** (answers the poll)
```text
4...Nxe4. Taking the pawn back first was the move. 41% of the 164 games found it.

4...dxe5 was more popular (55%). 5.Qxd8+ Kxd8 6.Nxe5 and White is a pawn up. White scored 64% after it.
```

### Day 17 · Myth vs data: a pawn up

**Morning**
```text
Myth: win a pawn and the points follow.

1.e4 e5 2.Nf3 Nc6 3.d4 d6 4.dxe5 dxe5 5.Qxd8+. After 5...Nxd8? 6.Nxe5, White is a clean pawn up and scored 61%. After the correct 5...Kxd8, White also scored 61%.

1,044 games. The extra pawn changed nothing in the score.
```

### Day 18 · Stat: the popular move

**Morning**
```text
Is the move most people play the right one? Across the pack's 23 positions:

13 times it's Stockfish's top move.
6 times it's a mistake costing 1.2+ pawns.
4 times it's neither.

So the crowd is right a bit more than half the time.
```

### Day 19 · What we left out

**Morning**
```text
38 positions passed our three tests. 23 are in the pack.

The smallest position in the pack has 100 games. Four of the 15 that stayed out had fewer: 85, 90, 92 and 95.

Every page shows its game count, so you can judge the sample yourself.
```

### Day 20 · Reminder 1 (link)

**Morning**
```text
For anyone who just found us: 23 traps from 902,003 Lichess games at 1200–1599. A 37-page PDF with drills and an answer key, plus a PGN. $14.

https://ceemv22.gumroad.com/l/e4e5-traps-white

Trap 1 is free in the pinned thread.
```

### Day 21 · Poll: Ruy Lopez, 5.Re1

**Morning (poll)**
```text
1.e4 e5 2.Nf3 Nc6 3.Bb5 Nf6 4.O-O Nxe4 5.Re1

Black to move. Which would you play?
```
Poll options (300 minutes): 5...Nd6 | 5...Nf6 | 5...d5 | 5...f5

**Evening reply** (answers the poll)
```text
5...Nd6 is Stockfish's pick (32% of 537 games). 5...Nf6 is close, a third of a pawn worse (29%).

5...d5 came up in 20% and costs 2.3 pawns. 6.d3 kicks the knight and White wins material in the centre. White scored 66%.
```

### Day 22 · Behind the method: who we counted

**Morning**
```text
We only counted games where both players were rated 1200–1599, and we left out bullet.

A 1500 beating a 1900 says less about 1500s than a 1500 playing a 1500. Blitz, rapid and classical only.
```

### Day 23 · Myth vs data: the engine's verdict

**Morning**
```text
Myth: if Stockfish says White is winning, White wins.

Vienna Gambit, 3.f4 Bb4. Stockfish has White +2.8 after it. In 251 games White scored 55%.

That's why our third test looks at White's score, not just the eval.
```

### Day 24 · Where our numbers get thin

**Morning**
```text
7 of the 23 positions in the pack rest on fewer than 200 games. The smallest has 100. The biggest has 6,076.

Every page shows its count. A percentage from 100 games is a hint, not a law.
```

### Day 25 · Poll: what next

**Morning (poll)**
```text
If we run the numbers on another opening, which one?

No promises. Just counting votes.
```
Poll options (1440 minutes): 1.e4 c5, as White | 1.d4 d5, as White | 1.e4 e5, as Black | 1.d4, as Black

### Day 26 · Behind the method: "scored"

**Morning**
```text
When we say White scored 82%, we mean points per game. A win is 1, a draw is ½.

It isn't a win rate. After 7...Ke8 in the Fried Liver, White scored 82% across 756 games.
```

### Day 27 · Stat: the clean sheet

**Morning**
```text
Fried Liver, 7.Qf3+. Black played 7...Kg8 in 228 games.

White took 228 points from those 228 games. No draws, no losses.
```

### Day 28 · Reminder 2 (link)

**Morning**
```text
Trap 1 is in the pinned thread. The other 22 are in the pack: a 37-page PDF with a drill for each trap, plus a PGN for your Lichess study. $14, and a refund within 30 days if it's not for you.

https://ceemv22.gumroad.com/l/e4e5-traps-white
```

### Day 29 · Stat: where the traps start

**Morning**
```text
Where the 23 traps start: 18 come after 1.e4 e5 2.Nf3, three after 2.Bc4 and two after 2.Nc3.

By page title, Scotch has the most with five. Ruy Lopez has four.
```

### Day 30 · What the pack doesn't do

**Morning**
```text
The pack covers White after 1.e4 e5, and only 1200–1599 games. Expect stronger players to fall for these less often.

It won't promise rating points. The games already happened. Yours haven't.
```
