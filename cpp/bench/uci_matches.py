import argparse
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import pathlib
import platform
import queue
import re
import subprocess
import sys
import threading
import time

from search_benchmark import digest

from trickfish.position import Position


DRAW_POLICY = "always claim fifty moves/threefold; automatic seventy-five/fivefold; mate first"


def repetition_identity(position):
    return (position.board, position.side_to_move, position.castling, position._repetition_en_passant_file())


def adjudicate(position, counts):
    status = position.game_status()
    if status == "checkmate":
        return ("0-1" if position.side_to_move == "w" else "1-0", "checkmate")
    if status == "stalemate":
        return "1/2-1/2", "stalemate"
    if position.is_insufficient_material():
        return "1/2-1/2", "insufficient_material"
    repetitions = counts[repetition_identity(position)]
    if position.halfmove_clock >= 150:
        return "1/2-1/2", "seventy_five_moves"
    if repetitions >= 5:
        return "1/2-1/2", "fivefold_repetition"
    if position.halfmove_clock >= 100:
        return "1/2-1/2", "always_claim_fifty_moves"
    if repetitions >= 3:
        return "1/2-1/2", "always_claim_threefold"
    return None


def opening_position(opening):
    position = Position.from_fen(opening["fen"])
    counts = Counter([repetition_identity(position)])
    for text in opening.get("moves", []):
        if adjudicate(position, counts) is not None:
            raise ValueError("opening continues after adjudicated game end")
        legal = {move.to_uci(): move for move in position.legal_moves()}
        if text not in legal:
            raise ValueError(f"illegal opening move: {text}")
        position = position.make_move(legal[text])
        counts[repetition_identity(position)] += 1
    return position, counts


def load_openings(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not data.get("openings"):
        raise ValueError("openings require version 1 and a nonempty list")
    names = set()
    for opening in data["openings"]:
        name = opening["id"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("opening IDs must be nonempty and unique")
        names.add(name)
        position = Position.from_fen(opening["fen"])
        opposite = "b" if position.side_to_move == "w" else "w"
        if position.is_square_attacked(position._king_square(opposite), position.side_to_move):
            raise ValueError(f"nonmoving king is checked: {name}")
        opening["fen"] = position.to_fen()
        if not isinstance(opening.get("moves", []), list):
            raise ValueError("opening moves must be a list")
        final, counts = opening_position(opening)
        if adjudicate(final, counts) is not None:
            raise ValueError("opening ends in an adjudicated position")
    return data["openings"]


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("engine profile must be an option object")
    names = set()
    for name, value in profile.items():
        if not isinstance(name, str) or not name.strip() or name != name.strip() or any(ord(c) < 32 or ord(c) == 127 for c in name) or name.casefold() in names or type(value) not in (bool, int):
            raise ValueError("profile requires unique option names and boolean/integer values")
        names.add(name.casefold())
    return dict(profile)


def load_profiles(path):
    if path is None:
        return {"a": {}, "b": {}}
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate profile JSON key")
            result[key] = value
        return result
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if data.get("version") != 1 or not isinstance(data.get("engines"), dict) or set(data["engines"]) - {"a", "b"}:
        raise ValueError("profiles require version 1 and engine keys a/b")
    return {label: validate_profile(data["engines"].get(label, {})) for label in ("a", "b")}


class Engine:
    def __init__(self, binary, timeout, profile=None):
        self.binary = binary
        self.timeout = timeout
        self.process = None
        self.events = queue.Queue()
        self.name = "unknown"
        self.profile = validate_profile({} if profile is None else profile)
        self.option_catalog = {}
        self.applied_options = {}

    def __enter__(self):
        self.process = subprocess.Popen([str(self.binary)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        def read():
            try:
                for line in self.process.stdout:
                    self.events.put(line.rstrip("\r\n"))
            finally:
                self.events.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        try:
            self.send("uci")
            self.until("uciok")
            self.apply_profile()
            self.send("ucinewgame")
            self.send("isready")
            self.until("readyok")
        except BaseException:
            self.close()
            raise
        return self

    def apply_profile(self):
        actions = []
        for requested, value in self.profile.items():
            option = self.option_catalog.get(requested.casefold())
            if option is None:
                raise ValueError(f"engine did not advertise option: {requested}")
            kind = option["type"]
            if kind == "check":
                if type(value) is not bool: raise ValueError("check profile value must be boolean")
                encoded = "true" if value else "false"
            elif kind == "spin":
                minimum = re.search(r"(?:^|\s)min (-?\d+)(?=\s|$)", option["spec"])
                maximum = re.search(r"(?:^|\s)max (-?\d+)(?=\s|$)", option["spec"])
                if type(value) is not int or minimum is None or maximum is None or not int(minimum[1]) <= value <= int(maximum[1]):
                    raise ValueError("spin profile value is outside advertised bounds")
                encoded = str(value)
            else:
                raise ValueError("match profiles support advertised check/spin options only")
            actions.append((option["name"], value, encoded))
        for name, value, encoded in actions:
            self.send(f"setoption name {name} value {encoded}")
            self.applied_options[name] = value

    def send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def until(self, prefix):
        deadline = time.monotonic() + self.timeout
        info = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(f"UCI timeout waiting for {prefix}: {self.binary}")
            try:
                line = self.events.get(timeout=remaining)
            except queue.Empty as error:
                raise RuntimeError(f"UCI timeout waiting for {prefix}: {self.binary}") from error
            if line is None:
                raise RuntimeError(f"UCI engine exited waiting for {prefix}: {self.binary}")
            if line.startswith("info string error:"):
                raise RuntimeError(f"UCI engine rejected command: {line}")
            option = re.fullmatch(r"option name (.+) type (\w+)(?: (.*))?", line)
            if option is not None:
                name, kind, spec = option.groups()
                self.option_catalog[name.casefold()] = {"name": name, "type": kind, "spec": spec or ""}
            if line.startswith("id name "):
                self.name = line[8:]
            if line.startswith("info "):
                info = line
            if line == prefix or line.startswith(prefix + " "):
                return line, info

    def choose(self, fen, moves, go):
        self.send("position fen " + fen + (" moves " + " ".join(moves) if moves else ""))
        self.send("isready")
        self.until("readyok")
        started = time.perf_counter_ns()
        self.send(go)
        line, info = self.until("bestmove")
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        parts = line.split()
        if len(parts) < 2:
            raise RuntimeError("malformed UCI bestmove")
        return parts[1], info, elapsed

    def close(self):
        if self.process is None:
            return
        try:
            if self.process.poll() is None:
                self.send("quit")
            self.process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait(timeout=3)
        finally:
            try:
                self.process.stdin.close()
            except OSError:
                pass
            self.reader.join(timeout=1)
            self.process.stdout.close()
        returncode = self.process.returncode
        self.process = None
        if returncode != 0:
            raise RuntimeError(f"UCI engine exited with code {returncode}: {self.binary}")

    def __exit__(self, *_):
        self.close()


def play_game(opening, binaries, white, go, max_plies, timeout, engine_factory=Engine, profiles=None):
    started_utc = datetime.now(timezone.utc).isoformat()
    position, counts = opening_position(opening)
    moves = list(opening.get("moves", []))
    decisions = []
    black = "b" if white == "a" else "a"
    assignment = {"w": white, "b": black}
    with ExitStack() as stack:
        profiles = {"a": {}, "b": {}} if profiles is None else profiles
        engines = {label: stack.enter_context(engine_factory(path, timeout, profiles.get(label, {})))
            for label, path in binaries.items()}
        while True:
            outcome = adjudicate(position, counts)
            if outcome is not None:
                result, reason = outcome
                break
            if len(decisions) >= max_plies:
                result, reason = "*", "searched_ply_limit"
                break
            label = assignment[position.side_to_move]
            text, info, elapsed = engines[label].choose(opening["fen"], moves, go)
            legal = {move.to_uci(): move for move in position.legal_moves()}
            if text not in legal:
                raise RuntimeError(f"illegal bestmove from engine {label}: {text}")
            decisions.append({"engine": label, "side": position.side_to_move, "move": text,
                "process_wall_ms": elapsed, "info": info})
            position = position.make_move(legal[text])
            moves.append(text)
            counts[repetition_identity(position)] += 1
        names = {label: engine.name for label, engine in engines.items()}
        applied = {label: engine.applied_options for label, engine in engines.items()}
    return {"started_utc": started_utc, "ended_utc": datetime.now(timezone.utc).isoformat(),
        "opening": opening["id"], "root_fen": opening["fen"], "opening_plies": len(opening.get("moves", [])),
        "white": white, "black": black, "engine_names": names, "applied_options": applied, "moves": moves, "decisions": decisions,
        "result": result, "reason": reason, "final_fen": position.to_fen()}


def score_games(games):
    scores = {label: {"wins": 0, "losses": 0, "draws": 0, "unfinished": 0} for label in ("a", "b")}
    for game in games:
        if game["result"] in {"*", "1/2-1/2"}:
            category = "unfinished" if game["result"] == "*" else "draws"
            for score in scores.values(): score[category] += 1
        elif game["result"] in {"1-0", "0-1"}:
            winner = game["white"] if game["result"] == "1-0" else game["black"]
            loser = "b" if winner == "a" else "a"
            scores[winner]["wins"] += 1
            scores[loser]["losses"] += 1
        else:
            raise ValueError("unsupported game result")
    return scores


def main():
    parser = argparse.ArgumentParser(description="Sequential color-paired UCI match baseline; no Elo/SPRT inference")
    parser.add_argument("engine_a", type=pathlib.Path)
    parser.add_argument("engine_b", type=pathlib.Path)
    parser.add_argument("--openings", type=pathlib.Path, default=pathlib.Path(__file__).with_name("match_openings.json"))
    budget = parser.add_mutually_exclusive_group()
    budget.add_argument("--depth", type=int)
    budget.add_argument("--movetime", type=int)
    budget.add_argument("--nodes", type=int)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--profiles", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    depth = 2 if args.depth is None and args.movetime is None and args.nodes is None else args.depth
    if args.rounds < 1 or args.max_plies < 1 or not 0 < args.timeout < float("inf"):
        parser.error("rounds/ply limit and finite watchdog timeout must be positive")
    if depth is not None and not 1 <= depth <= 64:
        parser.error("depth must be 1..64")
    if args.nodes is not None and not 1 <= args.nodes <= (1 << 64) - 1:
        parser.error("nodes must be 1..18446744073709551615")
    if args.movetime is not None and (args.movetime < 1 or args.movetime >= args.timeout * 1000):
        parser.error("movetime must be positive and shorter than the watchdog timeout")
    binaries = {"a": args.engine_a.resolve(strict=True), "b": args.engine_b.resolve(strict=True)}
    hashes = {label: digest(path) for label, path in binaries.items()}
    opening_path = args.openings.resolve(strict=True)
    opening_hash = digest(opening_path)
    openings = load_openings(opening_path)
    profile_path = args.profiles.resolve(strict=True) if args.profiles else None
    profile_hash = digest(profile_path) if profile_path is not None else None
    profiles = load_profiles(profile_path)
    if depth is not None:
        budget_kind, budget_value = "depth", depth
    elif args.nodes is not None:
        budget_kind, budget_value = "nodes", args.nodes
    else:
        budget_kind, budget_value = "movetime", args.movetime
    go = f"go {budget_kind} {budget_value}"
    games = []
    for round_number in range(1, args.rounds + 1):
        for opening in openings:
            for white in ("a", "b"):
                game = play_game(opening, binaries, white, go, args.max_plies, args.timeout, profiles=profiles)
                game["round"] = round_number
                games.append(game)
    if any(digest(path) != hashes[label] for label, path in binaries.items()) or digest(opening_path) != opening_hash or (profile_path is not None and digest(profile_path) != profile_hash):
        raise RuntimeError("engine binary or openings changed during matches")
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "engines": {label: {"path": str(path), "sha256": hashes[label], "arguments": []} for label, path in binaries.items()},
        "openings": {"path": str(opening_path), "sha256": opening_hash},
        "profiles": profiles,
        "profile_source": {"path": str(profile_path), "sha256": profile_hash} if profile_path is not None else None,
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "policy": {"go": go, "search_budget": {"kind": budget_kind, "value": budget_value}, "rounds": args.rounds, "searched_ply_limit": args.max_plies,
            "watchdog_seconds": args.timeout, "schedule": "sequential fresh processes; same opening, swapped colors",
            "draws": DRAW_POLICY,
            "errors": "abort run without assigning a game result", "ply_limit_result": "unfinished"},
        "scores": score_games(games), "games": games}
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
