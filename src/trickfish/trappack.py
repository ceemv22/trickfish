"""Trap finder: sound moves that real players at a rating band frequently answer badly.

A trap is recorded at a position where the opponent is to move, reached by a line
of moves that are all objectively sound for our side.  Evidence comes from three
independent sources:

* Stockfish: our moves lose at most ``sound_cp`` against the engine's best move, and
  a reply counts as a mistake when it hands us at least ``mistake_cp``.
* Lichess opening explorer: how often players in the rating band actually chose
  each reply, and how those games ended.
* Optionally, a human-move model supplying the probability of each reply.

Game statistics come either from the online explorer or from a local extract of
the public Lichess database (see :mod:`trickfish.lichess_db`).
"""

import argparse
import hashlib
import json
import math
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field

import chess
import chess.engine

EXPLORER_URL = "https://explorer.lichess.ovh/lichess"
MATE_CP = 1500


def clamp_score(score, color):
    value = score.pov(color).score(mate_score=100000)
    return max(-MATE_CP, min(MATE_CP, value))


class JsonCache:
    def __init__(self, directory):
        self.directory = pathlib.Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        return self.directory / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")

    def get(self, key):
        path = self._path(key)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def put(self, key, value):
        self._path(key).write_text(json.dumps(value), encoding="utf-8")


class Explorer:
    """Rate-limited, disk-cached client for the Lichess opening explorer."""

    def __init__(self, cache, ratings, speeds, delay=0.6, opener=urllib.request.urlopen):
        self.cache = cache
        self.ratings = ",".join(str(value) for value in ratings)
        self.speeds = ",".join(speeds)
        self.delay = delay
        self.opener = opener
        self.requests = 0

    def __call__(self, board):
        query = urllib.parse.urlencode({"variant": "standard", "fen": board.fen(), "ratings": self.ratings,
                                        "speeds": self.speeds, "moves": 15, "topGames": 0,
                                        "recentGames": 0})
        key = "explorer?" + query
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        for attempt in range(6):
            time.sleep(self.delay)
            try:
                request = urllib.request.Request(EXPLORER_URL + "?" + query,
                                                 headers={"Accept": "application/json",
                                                          "User-Agent": "trickfish-trappack"})
                with self.opener(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.requests += 1
                self.cache.put(key, data)
                return data
            except urllib.error.HTTPError as error:
                if error.code == 429:
                    time.sleep(61)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                time.sleep(5 * (attempt + 1))
        raise RuntimeError("Lichess explorer kept failing for " + board.fen())


class Evaluator:
    """Disk-cached Stockfish evaluation, always reported from ``color``'s side."""

    def __init__(self, engine_path, cache, depth, threads=3, hash_mb=256):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.engine.configure({"Threads": threads, "Hash": hash_mb})
        self.name = self.engine.id.get("name", "unknown engine")
        self.cache = cache
        self.depth = depth

    def analyse(self, board, depth=None):
        depth = depth or self.depth
        key = "eval|%s|%d|%s" % (self.name, depth, board.fen())
        cached = self.cache.get(key)
        if cached is None:
            if board.is_game_over():
                outcome = board.outcome()
                white = 0 if outcome.winner is None else (MATE_CP if outcome.winner else -MATE_CP)
                cached = {"white_cp": white, "pv": []}
            else:
                info = self.engine.analyse(board, chess.engine.Limit(depth=depth))
                cached = {"white_cp": clamp_score(info["score"], chess.WHITE),
                          "pv": [move.uci() for move in info.get("pv", [])]}
            self.cache.put(key, cached)
        return cached

    def cp(self, board, color):
        value = self.analyse(board)["white_cp"]
        return value if color == chess.WHITE else -value

    def close(self):
        self.engine.quit()


@dataclass
class Reply:
    san: str
    uci: str
    games: int
    share: float
    our_cp: int
    gain_cp: int
    our_score: float
    maia: float | None = None


@dataclass
class Trap:
    moves: list
    fen: str
    games: int
    best_cp: int
    best_reply_san: str
    error_share: float
    expected_gain_cp: float
    replies: list
    punish: dict = field(default_factory=dict)
    maia_error: float | None = None

    @property
    def score(self):
        return self.expected_gain_cp * math.log10(max(self.games, 10))


def games(node):
    return node.get("white", 0) + node.get("draws", 0) + node.get("black", 0)


def score_for(node, color):
    total = games(node)
    if not total:
        return 0.0
    wins = node["white"] if color == chess.WHITE else node["black"]
    return (wins + 0.5 * node["draws"]) / total


def san_line(board, ucis, limit):
    board = board.copy()
    line = []
    for uci in ucis[:limit]:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            break
        line.append(board.san(move))
        board.push(move)
    return line


class TrapFinder:
    def __init__(self, explorer, evaluator, color, maia=None, min_games=200, max_ply=22,
                 sound_cp=50, mistake_cp=120, min_error_share=0.15, min_score=0.6, our_share=0.04,
                 their_share=0.08, our_branching=4, their_branching=3, log=print):
        self.explorer = explorer
        self.evaluator = evaluator
        self.color = color
        self.maia = maia
        self.min_games = min_games
        self.max_ply = max_ply
        self.sound_cp = sound_cp
        self.mistake_cp = mistake_cp
        self.min_error_share = min_error_share
        self.min_score = min_score
        self.our_share = our_share
        self.their_share = their_share
        self.our_branching = our_branching
        self.their_branching = their_branching
        self.log = log
        self.traps = {}
        self.visited = set()

    def run(self, board):
        self._walk(board.copy())
        return sorted(self.traps.values(), key=lambda trap: trap.score, reverse=True)

    def _walk(self, board):
        key = board.epd()
        if key in self.visited or board.ply() > self.max_ply or board.is_game_over():
            return
        self.visited.add(key)
        node = self.explorer(board)
        total = games(node)
        if total < self.min_games:
            return
        if board.turn == self.color:
            self._our_move(board, node, total)
        else:
            self._their_move(board, node, total)

    def _our_move(self, board, node, total):
        best = self.evaluator.analyse(board)
        best_uci = best["pv"][0] if best["pv"] else None
        best_cp = self.evaluator.cp(board, self.color)
        candidates = [move["uci"] for move in node["moves"] if games(move) / total >= self.our_share]
        candidates = candidates[:self.our_branching]
        if best_uci and best_uci not in candidates:
            candidates.append(best_uci)
        for uci in candidates:
            move = chess.Move.from_uci(uci)
            board.push(move)
            sound = best_cp - self.evaluator.cp(board, self.color) <= self.sound_cp
            if sound:
                self._walk(board)
            board.pop()

    def _their_move(self, board, node, total):
        best_cp = self.evaluator.cp(board, self.color)
        best = self.evaluator.analyse(board)
        replies = []
        for move in node["moves"]:
            count = games(move)
            if count / total < 0.02 or count < 20:
                continue
            board.push(chess.Move.from_uci(move["uci"]))
            our_cp = self.evaluator.cp(board, self.color)
            board.pop()
            replies.append(Reply(move["san"], move["uci"], count, count / total, our_cp,
                                 our_cp - best_cp, score_for(move, self.color)))
        mistakes = [reply for reply in replies if reply.gain_cp >= self.mistake_cp]
        error_share = sum(reply.share for reply in mistakes)
        top = max(mistakes, key=lambda reply: reply.share) if mistakes else None
        if top and error_share >= self.min_error_share and top.our_score >= self.min_score:
            self._record(board, total, best_cp, best, replies, mistakes, error_share)
        mainline = sorted((reply for reply in replies if reply.gain_cp < self.mistake_cp),
                          key=lambda reply: reply.games, reverse=True)
        for reply in mainline[:self.their_branching]:
            if reply.share < self.their_share:
                continue
            board.push(chess.Move.from_uci(reply.uci))
            self._walk(board)
            board.pop()

    def _record(self, board, total, best_cp, best, replies, mistakes, error_share):
        moves = [move.uci() for move in board.move_stack]
        best_reply = san_line(board, best["pv"], 1)
        top = max(mistakes, key=lambda reply: reply.share)
        after = board.copy()
        after.push(chess.Move.from_uci(top.uci))
        punish_pv = self.evaluator.analyse(after, self.evaluator.depth + 4)["pv"]
        punish = {"after": top.san, "line": san_line(after, punish_pv, 9), "uci": punish_pv[:9],
                  "our_cp": top.our_cp}
        maia_error = None
        if self.maia is not None:
            probabilities = self.maia(board)
            for reply in replies:
                reply.maia = probabilities.get(reply.uci, 0.0)
            maia_error = sum(probabilities.get(reply.uci, 0.0) for reply in mistakes)
        trap = Trap(moves, board.fen(), total, best_cp, best_reply[0] if best_reply else "",
                    error_share, sum(r.share * r.gain_cp for r in mistakes), replies, punish, maia_error)
        self.traps[board.epd()] = trap
        self.log("trap %-60s games=%d err=%.0f%% gain=%.0f" % (" ".join(san_line(chess.Board(), moves, 40)),
                                                                total, error_share * 100, trap.expected_gain_cp))


def board_from(moves):
    board = chess.Board()
    for token in moves.split():
        board.push_san(token)
    return board


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find practical opening traps backed by Lichess games")
    parser.add_argument("--moves", required=True, help="SAN moves leading to the opening root")
    parser.add_argument("--color", choices=["white", "black"], required=True)
    parser.add_argument("--ratings", default="1200,1400", help="Lichess explorer rating buckets")
    parser.add_argument("--speeds", default="blitz,rapid,classical")
    parser.add_argument("--engine", default="/usr/games/stockfish")
    parser.add_argument("--depth", type=int, default=18)
    parser.add_argument("--min-games", type=int, default=200)
    parser.add_argument("--max-ply", type=int, default=28)
    parser.add_argument("--branching", type=int, default=5, help="moves followed per side at each node")
    parser.add_argument("--follow-share", type=float, default=0.05, help="minimum share of a move to follow it")
    parser.add_argument("--min-error-share", type=float, default=0.15)
    parser.add_argument("--min-score", type=float, default=0.6)
    parser.add_argument("--games", help="local extract from trickfish.lichess_db instead of the online explorer")
    parser.add_argument("--band", default="1200-1599", help="rating band label for the report")
    parser.add_argument("--cache", default=".trappack-cache")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    cache = JsonCache(args.cache)
    ratings = [int(value) for value in args.ratings.split(",")]
    root = board_from(args.moves)
    if args.games:
        from trickfish.lichess_db import LocalExplorer
        explorer = LocalExplorer(args.games, args.moves.split())
        print("%d games in the opening sample" % explorer.games)
    else:
        explorer = Explorer(cache, ratings, args.speeds.split(","))
    evaluator = Evaluator(args.engine, cache, args.depth)
    color = chess.WHITE if args.color == "white" else chess.BLACK
    try:
        finder = TrapFinder(explorer, evaluator, color, None, args.min_games, args.max_ply,
                            min_error_share=args.min_error_share, min_score=args.min_score,
                            our_share=args.follow_share * 0.6, their_share=args.follow_share,
                            our_branching=args.branching, their_branching=args.branching)
        traps = finder.run(root)
    finally:
        evaluator.close()
    result = {"schema": "trickfish.trappack.v1", "root": args.moves, "color": args.color,
              "ratings": ratings, "speeds": args.speeds, "engine": evaluator.name, "depth": args.depth,
              "band": args.band, "source": args.games or EXPLORER_URL,
              "sample_games": getattr(explorer, "games", None), "min_games": args.min_games,
              "traps": [{**asdict(trap), "score": trap.score} for trap in traps]}
    pathlib.Path(args.output).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("%d traps, %d explorer requests, %d positions visited" % (len(traps), explorer.requests,
                                                                    len(finder.visited)))


if __name__ == "__main__":
    main()
