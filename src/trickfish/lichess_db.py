"""Extract opening lines from the public Lichess game database (CC0).

Reads decompressed PGN from stdin, keeps rated non-bullet games whose players
both fall inside a rating band, and writes one line per game:
``<result>\t<average rating>\t<SAN SAN SAN ...>`` truncated to ``--plies``.

The written file feeds :class:`LocalExplorer`, which answers the same questions as
the online Lichess opening explorer for a fixed sample of real games.
"""

import argparse
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
    """Opening-explorer answers computed from an extracted game file."""

    def __init__(self, path, prefix_sans):
        self.prefix = tuple(prefix_sans)
        self.children = defaultdict(lambda: defaultdict(lambda: {"white": 0, "draws": 0, "black": 0}))
        self.totals = defaultdict(lambda: {"white": 0, "draws": 0, "black": 0})
        self.games = 0
        self.requests = 0
        size = len(self.prefix)
        key = {"w": "white", "d": "draws", "b": "black"}
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                result, _, moves = line.rstrip("\n").split("\t")
                sans = moves.split()
                if tuple(sans[:size]) != self.prefix:
                    continue
                self.games += 1
                outcome = key[result]
                for index in range(size, len(sans) + 1):
                    path_key = tuple(sans[size:index])
                    self.totals[path_key][outcome] += 1
                    if index < len(sans):
                        self.children[path_key][sans[index]][outcome] += 1

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
        path_key = tuple(sans[len(self.prefix):])
        node = dict(self.totals.get(path_key, {"white": 0, "draws": 0, "black": 0}))
        moves = []
        for san, stats in self.children.get(path_key, {}).items():
            try:
                uci = board.parse_san(san).uci()
            except ValueError:
                continue
            moves.append({"san": board.san(board.parse_san(san)), "uci": uci, **stats})
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
