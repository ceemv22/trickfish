# PDF QA: 1.e4 e5 Traps for White (1200–1599)

File: `dist/gumroad-upload/trickfish-e4e5-traps-white-1200-1599.pdf` (37 A4 pages) and its PGN.
Reviewed 2026-11-10 against `packs/e4e5-white-1200/traps.json` and `notes.json`, with python-chess and Stockfish (`/usr/games/stockfish`, depth 16, depth 20–22 where a claim was close).

## Verdict: fix soon

It's fine to keep selling. Every number in the book matches the data, every move is legal, every diagram matches its line, and nothing overflows, gets clipped or collides. Two copy promises don't match what the pages show, two chess sentences are wrong, and there are a few typographic slips. All of them can go into the next build.

## Defects

Ordered by importance. Page numbers are PDF page numbers, which match the folios.

1. **p3, "How to use it" item 03: the promise isn't kept.** It says "Every page shows it with Stockfish's verdict", but 11 of the 23 trap pages give the best defence with no evaluation: Traps 7, 11, 12, 13, 14, 15, 18, 19, 20, 22 and 23 (pages 12, 16–20, 23–25, 27 and 28). **Fix:** add the pack's `best_cp` to those `defence` notes in notes.json: T7 (Stockfish +0.2), T11 +0.4, T12 +0.2, T13 +0.3, T14 +0.5, T15 +0.2, T18 +0.5, T19 −0.2, T20 +0.2, T22 −0.1, T23 +0.5. Or change the sentence to "Every page shows it."

2. **p37, "About the numbers" item 01: the definition of "went wrong" doesn't match the number printed.** The studio's `wrong_share` counts only mistakes after which White scored at least 50%. The fineprint (and voice.md rule 3) leaves that condition out. Two traps come out differently under the printed definition: Trap 20 shows 32% where the definition gives 36% (5...Ne7, White 45%, is left out), and Trap 21 shows 17% where it gives 31% (4...Bxf2+, White 32%, is left out). A coach checking the PGN or the data would catch this. **Fix:** change fineprint[0] in notes.json to: "Went wrong: the share of games reaching the position in which Black chose a reply that costs at least 1.2 pawns by Stockfish's count, and after which White scored at least 50%. We only count replies played in at least 20 games and at least 2% of the games there." Make the same change to voice.md rule 3.

3. **p7, Trap 2, Best defence: "9...Kd6! is forced" is wrong.** 9...Kd7 is just as good: Stockfish gives +1.8 for 9...Kd7 and +1.9 for 9...Kd6 at depth 22, with the same plan after 10.Qd1 c6 11.Be4 Kc7. **Fix:** set the T2 `defence` to "9...Kd6! or 9...Kd7 holds, and White keeps a strong attack (Stockfish +1.9)."

4. **p18, Trap 13, Best defence: "5...a6 asks the bishop first and breaks the pin" is inaccurate.** After 6.Ba4 the c6 knight is still pinned. The pin only goes after ...b5, or after 6.Bxc6+ bxc6. **Fix:** set the T13 `defence` to "5...a6 puts the question to the bishop first: 6.Bxc6+ bxc6 ends the pin, and after 6.Ba4 Black has ...b5 (Stockfish +0.3)." Stockfish has 6.Ba4 b5 at about +0.5.

5. **pp7, 22 and 24: the mistake mark changes on the same page.** The label and caption say "9…Qxd5?", "5…Nf6?" and "3…g6?", because book.py always adds a single "?". The idea text on the same page says "9...Qxd5??", "5...Nf6??" and "3...g6??". The PGN gives all three $2 ("?"). **Fix:** either change those three prose marks in notes.json to "?" (T2, T17, T19 idea), or add a per-trap `"mark": "??"` to notes.json, use it in `book.py` (cover, trap page, `mistake` caption) and use `chess.pgn.NAG_BLUNDER` for it in `write_pgn`. The second fix is better chess: losing a queen or a rook is a "??".

6. **p37, items 02 and 05: straight double quotes.** `"went wrong"` and `"Mating"` print as straight quotes. Every apostrophe in the book is curly. **Fix:** use “went wrong” and “Mating” in `_meta.fineprint` in notes.json, or have `st.esc()` convert double quotes the same way it converts single ones.

7. **pp4–5, glance table: single-word last lines in the titles.** Rows 05 ("The double attack from / d5"), 08 ("…short of / squares"), 14 ("…by another / road") and 23 ("…that doesn't / work"). **Fix:** in `book.glance_pages`, apply `glue()` to the title: `html.escape(glue(st.title_of(trap).replace("'", "’")))`.

8. **p17, Trap 12 idea: "6...dxe5? trades queens".** Black's move doesn't trade queens. It lets White trade them, which is how Trap 18 puts it. **Fix:** "6...dxe5? lets White trade queens and drops a pawn: 7.Qxd8+ Kxd8 8.Nxe5…". The `plain` text has the same wording: "6...dxe5 allows a queen trade and drops a pawn."

9. **p24, Trap 19 idea: "Both f7 and e5 are hanging."** f7 is defended by the king. What White has is a mate threat (Qxf7#) plus a hit on e5. **Fix:** "The queen hits e5 and, with the c4 bishop, threatens mate on f7."

10. **pp6–28, "The punishment" lines: the spacing groups the wrong moves.** A space inside a move pair is set in the mono and is wide. The space between pairs is set in the text face and is narrower. So "8.Bxd5 Qf6 9.Bxc6+ bxc6" reads as "Qf6 9.Bxc6+". The header lines and the answer key are set wholly in mono and don't have the problem. **Fix:** in `book.line_html`, join the units with a mono space, e.g. `'<span class="mono"> </span>'.join(...)`, or give the `<p>` holding the punishment `font-family:'Martian Mono'`.

11. **p1 cover caption, the "After …" captions under the second diagram (pp6–28) and the drill captions (pp29–34): figurines print in full black inside grey labels.** On the cover the knight also touches the "f" of "f6". **Fix:** in those three places in book.py, call `st.notation(text, ink=st.FADED)`.

12. **p35, answer key #1: the explanation doesn't explain the answer.** The answer is 8.Bxd5, and the line under it is the page's `plain`, "Only 7…Ke6 holds the pinned knight." **Fix:** change T1 `plain` to "7...Ke8 drops the pinned knight to 8.Bxd5. Only 7...Ke6 holds it." Or give the answer key its own optional `answer` field.

13. **pp4–5, glance table "White scored": voice.md rule 5 isn't followed.** Five mistakes have 50–100 games behind them (T5 81, T6 90, T12 69, T13 64, T18 91), and the table gives the percentage without the game count. The "n" column counts the games at the position, not after the mistake. The trap pages get this right ("62% from 81 games"). **Fix (optional):** for 50 ≤ games < 100, add the count in the 7pt mono, e.g. `62% /81`.

## Checked and correct

- **Numbers.** All 23 rows of the glance table and all 23 trap pages match traps.json under the studio's metrics: went wrong, the top mistake and its share, White's score (points for the six traps under 50 games: 47/48, 28/38, 19½/30, 17/20, 42½/49, 22/35), the Stockfish figure after the mistake, and n. The method page is right too: 902,003 games, 38 positions passed, 23 picked, busiest 6,076, quietest 100, half a pawn (`sound_cp=50`), 15% / 1.2 pawns / 60% (every trap clears them: lowest score 60.9% on T11, lowest error share 16% on T10), and replies in at least 20 games and at least 2% of them. So are the fineprint example (42½ from 49 = T17) and the prose figures (61% on T11, 69% on T12, +5.3 on T16, "one game in ten" on T22, "most popular" on T6/T7, "most common" on T23). Every eval in the defence notes equals the pack's `best_cp`.
- **Chess.** Every move sequence in the notes is legal in its position (python-chess, 140 sequences). Stockfish agrees with every evaluative claim except items 3 and 4. Examples: T1 only 7...Ke6 holds, 7...Kg8 is mated; T2 9...Ke7 gets mated in 2; T3 ends at +5.7 after the queens come off; T4 7.Nf7 +3.7; T7 6...dxc6 +5.0, 6...Bxe3 +6.5; T8 7...Qh4 is the only way to save the knight (+3.8); T9 Nd5/Ng4/Ne4 all drop it; T10 Qxf7# and Qxa8 are both threats; T13 and T14 transpose (same FEN); T23 every move but 5...Ng8 is +2.9 or worse. I also checked "forces a queen trade" on T20: 5...Be7 is +3.4 at depth 20, against +3.0 for the trade, so avoiding the trade costs more.
- **Diagrams.** On every page the red line and hook follow the printed punishment (each `CATCH` route checked against `punish_uci`). The dotted trail is the mistake. The second diagram on each page and each drill diagram is the position after the most common mistake, and each drill caption names that move. Every answer-key line is the start of that trap's punishment and is legal.
- **Layout.** No `.fit` box shrank: the body sits at the same size on every trap page. Nothing is clipped or overflows. Folios run 2–37 and match the PDF pages. There's no table of contents, and the book doesn't promise one. The text layer is selectable and searchable ("Ke8" is found). At phone width (1170 px) the trap, glance and answer pages read fine without zooming. The 8pt labels are small but clear.
- **PGN.** Parses with 23 games and 0 errors. Each game reaches the same position as its trap page, puts the most common mistake in the main line and the best reply as a variation, and has the punishment line. Its comments carry the same went-wrong share, share, score (points under 50 games) and best-defence eval as the PDF.
