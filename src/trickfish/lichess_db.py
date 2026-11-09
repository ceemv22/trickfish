"""Extract opening lines from the public Lichess game database (CC0).

Reads decompressed PGN from stdin, keeps rated non-bullet games whose players
both fall inside a rating band, and writes one line per game:
``<result>\t<average rating>\t<SAN SAN SAN ...>`` truncated to ``--plies``.

The written file feeds :class:`LocalExplorer`, which answers the same questions as
the online Lichess opening explorer for a fixed sample of real games.
"""

import argparse
import bisect
import gzip
import re
import sys
from collections import defaultdict

COMMENT = re.compile(r"\{[^}]*\}")
MOVE_NUMBER = re.compile(r"^\d+\.(\.\.)?$")
RESULTS = {"1-0": "w", "0-1": "b", "1/2-1/2": "d"}


def movetext_sans(text, plies):
    sans = []
    for token in COMMENT.sub(" ", text).split():
        if MOVE_NUMBER.match(token) or token in RESULTS or token == "*":
            continue
        if token[0].isdigit():
            token = token.split(".")[-1]
            if not token:
                continue
        sans.append(token.rstrip("?!"))
        if len(sans) >= plies:
            break
    return sans


def extract(stream, output, low, high, plies, max_games=None):
    headers = {}
    kept = seen = 0
    for line in stream:
        if line.startswith("["):
            space = line.find(" ")
            headers[line[1:space]] = line[space + 2:line.rfind('"')]
            continue
        if not line.strip() or not headers:
            continue
        seen += 1
        event = headers.get("Event", "")
        result = RESULTS.get(headers.get("Result"))
        try:
            white, black = int(headers.get("WhiteElo", 0)), int(headers.get("BlackElo", 0))
        except ValueError:
            white = black = 0
        headers = {}
        if result is None or not event.startswith("Rated") or "Bullet" in event:
            continue
        if not (low <= white <= high and low <= black <= high):
            continue
        sans = movetext_sans(line, plies)
        if len(sans) < 6:
            continue
        output.write("%s\t%d\t%s\n" % (result, (white + black) // 2, " ".join(sans)))
        kept += 1
        if kept % 200000 == 0:
            print("kept %d of %d games" % (kept, seen), file=sys.stderr, flush=True)
        if max_games and kept >= max_games:
            break
    return kept, seen


class LocalExplorer:
    """Opening-explorer answers computed from an extracted game file.

    Games under the root are kept as a sorted list of SAN tuples, so every
    position query is a binary-searched range instead of a stored prefix tree.
    """

    def __init__(self, path, prefix_sans):
        self.prefix = tuple(prefix_sans)
        size = len(self.prefix)
        intern = {}
        games = []
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                result, _, moves = line.rstrip("\n").split("\t")
                sans = moves.split()
                if tuple(sans[:size]) != self.prefix:
                    continue
                games.append((tuple(intern.setdefault(san, san) for san in sans[size:]), result))
        games.sort()
        self.keys = [game[0] for game in games]
        self.results = [game[1] for game in games]
        self.games = len(games)
        self.requests = 0

    def _range(self, path):
        low = bisect.bisect_left(self.keys, path)
        high = bisect.bisect_left(self.keys, path + ("\U0010ffff",), low)
        return low, high

    def counts(self, path):
        empty = lambda: {"white": 0, "draws": 0, "black": 0}
        key = {"w": "white", "d": "draws", "b": "black"}
        low, high = self._range(path)
        totals = empty()
        children = defaultdict(empty)
        depth = len(path)
        for index in range(low, high):
            outcome = key[self.results[index]]
            totals[outcome] += 1
            sans = self.keys[index]
            if len(sans) > depth:
                children[sans[depth]][outcome] += 1
        return totals, children

    def __call__(self, board):
        self.requests += 1
        replay = board.copy()
        sans = []
        while replay.move_stack:
            move = replay.pop()
            sans.append(replay.san(move))
        sans.reverse()
        if tuple(sans[:len(self.prefix)]) != self.prefix:
            raise ValueError("position is outside the extracted opening")
        totals, children = self.counts(tuple(sans[len(self.prefix):]))
        node = dict(totals)
        moves = []
        for san, stats in children.items():
            try:
                move = board.parse_san(san)
            except ValueError:
                continue
            moves.append({"san": board.san(move), "uci": move.uci(), **stats})
        moves.sort(key=lambda move: move["white"] + move["draws"] + move["black"], reverse=True)
        node["moves"] = moves
        return node


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract rating-band opening lines from Lichess PGN on stdin")
    parser.add_argument("--low", type=int, default=1200)
    parser.add_argument("--high", type=int, default=1599)
    parser.add_argument("--plies", type=int, default=30)
    parser.add_argument("--max-games", type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    stream = open(sys.stdin.fileno(), "r", encoding="utf-8", errors="replace", buffering=1 << 20)
    with gzip.open(args.output, "wt", encoding="utf-8", compresslevel=5) as output:
        kept, seen = extract(stream, output, args.low, args.high, args.plies, args.max_games)
    print("kept %d of %d games" % (kept, seen), file=sys.stderr)


if __name__ == "__main__":
    main()
