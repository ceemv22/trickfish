from dataclasses import dataclass
import hashlib
import json
import pathlib
import re

from .position import Position, STARTING_FEN
from .variation import replay_uci_line


@dataclass(frozen=True)
class ReviewCase:
    name: str
    position: Position


@dataclass(frozen=True)
class Repertoire:
    raw: bytes
    purpose: str
    cases: tuple[ReviewCase, ...]

    @property
    def sha256(self):
        return hashlib.sha256(self.raw).hexdigest()


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key: " + key)
        value[key] = item
    return value


def load_repertoire(path):
    raw = pathlib.Path(path).read_bytes()
    data = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(data, dict) or data.get("schema") != "trickfish.practical-cases.v1":
        raise ValueError("unsupported repertoire schema")
    if set(data) != {"schema", "purpose", "positions"}:
        raise ValueError("repertoire requires only schema, purpose and positions")
    if not isinstance(data["purpose"], str) or not data["purpose"].strip():
        raise ValueError("repertoire purpose must be nonempty text")
    if not isinstance(data["positions"], list) or not data["positions"]:
        raise ValueError("repertoire must contain positions")
    cases, names, fens = [], set(), set()
    reserved = {"con", "prn", "aux", "nul", *["com" + str(i) for i in range(1, 10)], *["lpt" + str(i) for i in range(1, 10)]}
    for item in data["positions"]:
        if not isinstance(item, dict) or not {"name", "moves"} <= item.keys() or set(item) - {"name", "moves", "fen"}:
            raise ValueError("each position requires name/moves and optional fen")
        name = item["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) or name in reserved or name in names:
            raise ValueError("case names must be unique safe lowercase file names")
        moves = item["moves"]
        if not isinstance(moves, list) or any(not isinstance(move, str) for move in moves):
            raise ValueError("case moves must be a list of UCI strings")
        fen = item.get("fen", STARTING_FEN)
        if not isinstance(fen, str):
            raise ValueError("case fen must be text")
        root = Position.from_fen(fen)
        other = "b" if root.side_to_move == "w" else "w"
        if root.is_in_check(other):
            raise ValueError("nonmoving king cannot be in check")
        position = replay_uci_line(root, moves)
        if position.to_fen() in fens:
            raise ValueError("duplicate final FEN in repertoire")
        names.add(name)
        fens.add(position.to_fen())
        cases.append(ReviewCase(name, position))
    return Repertoire(raw, data["purpose"], tuple(cases))
