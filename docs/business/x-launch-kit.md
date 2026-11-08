# X launch kit

## Account setup (owner, ~10 minutes)

1. Create the account while logged out of @Ceemv22 (use a separate email, e.g. a `+trickfish` alias).
2. **Handle:** `@trickfishchess` (fallbacks: `@trickfish_chess`, `@trickfishhq`).
3. **Display name:** `Trickfish`
4. **Profile picture:** `assets/trickfish-logo.png`
5. **Banner:** `docs/business/x-banner.png`
6. **Bio:**
   > Stockfish finds the best move. We find the one your opponent will get wrong. Chess traps measured on real Lichess games, verified by Stockfish.
7. **Link:** the Gumroad trap-pack URL once it is live (until then, the GitHub repo).
8. **Location field:** `Built on 100k+ real games`
9. Follow from @Ceemv22 and repost the pinned post from there. The owner's account is the first distribution channel.

Optional, for full autonomy: create a free developer app at developer.x.com with read+write access. Claude can then save the keys as a network secret for `api.x.com` (never paste them in chat) and schedule the daily posts itself.

## Pinned post (day 1)

> We analysed [N] real Lichess games between 1200–1599 players in the Italian Game.
>
> Then we asked Stockfish one question: where do sound moves meet opponents who keep getting it wrong?
>
> [X] traps came out. Here's one that catches [Y]% of players 🧵

Thread replies: card `trap-01.png`, then the answer card with the punishment line, then:

> All [X] traps, with drills and a PGN for your Lichess/Chess.com study: [GUMROAD LINK]
> Launch price $14.

## Daily format (days 2–14)

**Morning: question post** with the card `trap-NN.png`:

> [Y]% of 1200–1599 players play the wrong move here.
>
> Black to move. What would you play?

**Evening: answer**, as a reply to the morning post, with `trap-NN-answer.png`:

> The trap: [mistake]. [One sentence on why it fails.]
> Punishment: [line].
> In real games, White scores [Z]% after it.
>
> Full pack: [link]

## Rules

- Every number in a post comes from the pack JSON. No invented statistics.
- One link per day at most (the answer post). The question post never sells.
- Reply to every comment for the first two weeks. Correct answers get a like and a "you'd be in the [100−Y]%".
- No mass tagging, no unsolicited DMs, no buying followers.

## Weekly report (Claude fills, owner reads)

```text
Week:
Followers:
Best post impressions:
Gumroad views / sales / refunds:
What worked:
Next week's change:
```
