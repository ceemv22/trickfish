from __future__ import annotations

import sys
from threading import Event, Lock, Thread
from typing import TextIO

from .position import FenError, Position, STARTING_FEN
from .search import SearchResult, search


class UciEngine:
    def __init__(self, output: TextIO | None = None) -> None:
        self.position = Position.from_fen(STARTING_FEN)
        self.output = output or sys.stdout
        self.output_lock = Lock()
        self.stop_event = Event()
        self.search_thread: Thread | None = None

    def run(self, input_stream: TextIO | None = None) -> int:
        stream = input_stream or sys.stdin
        for line in stream:
            if not self.handle(line.strip()):
                break
        self._stop_search()
        return 0

    def handle(self, command: str) -> bool:
        if not command:
            return True
        tokens = command.split()
        name = tokens[0]
        if name == "uci":
            self._emit("id name Trickfish 0.1")
            self._emit("id author ceemv22")
            self._emit("uciok")
        elif name == "isready":
            self._emit("readyok")
        elif name == "ucinewgame":
            self._stop_search()
            self.position = Position.from_fen(STARTING_FEN)
        elif name == "position":
            self._set_position(tokens[1:])
        elif name == "go":
            self._go(tokens[1:])
        elif name == "stop":
            self._stop_search()
        elif name == "quit":
            return False
        return True

    def _set_position(self, tokens: list[str]) -> None:
        self._stop_search()
        try:
            if not tokens:
                raise ValueError("position requires startpos or fen")
            if tokens[0] == "startpos":
                position = Position.from_fen(STARTING_FEN)
                move_index = 1
            elif tokens[0] == "fen":
                if len(tokens) < 7:
                    raise ValueError("position fen requires six FEN fields")
                position = Position.from_fen(" ".join(tokens[1:7]))
                move_index = 7
            else:
                raise ValueError("position requires startpos or fen")
            if move_index < len(tokens):
                if tokens[move_index] != "moves":
                    raise ValueError("expected moves after position")
                for text in tokens[move_index + 1:]:
                    move = next(
                        (candidate for candidate in position.legal_moves() if candidate.to_uci() == text),
                        None,
                    )
                    if move is None:
                        raise ValueError(f"illegal move {text}")
                    position = position.make_move(move)
            self.position = position
        except (FenError, ValueError) as error:
            self._emit(f"info string {error}")

    def _go(self, tokens: list[str]) -> None:
        parameters = self._parameters(tokens)
        depth = parameters.get("depth")
        movetime = parameters.get("movetime")
        if movetime is None:
            movetime = self._clock_budget(parameters)
        if depth is None:
            depth = 64 if movetime is not None else 4
        self._start_search(depth, movetime)

    def _parameters(self, tokens: list[str]) -> dict[str, int]:
        parameters: dict[str, int] = {}
        names = {"depth", "movetime", "wtime", "btime", "winc", "binc", "movestogo"}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token in names and index + 1 < len(tokens):
                try:
                    parameters[token] = max(0, int(tokens[index + 1]))
                except ValueError:
                    self._emit(f"info string invalid go value for {token}")
                index += 2
            else:
                index += 1
        return parameters

    def _clock_budget(self, parameters: dict[str, int]) -> int | None:
        prefix = "w" if self.position.side_to_move == "w" else "b"
        remaining = parameters.get(f"{prefix}time")
        if remaining is None:
            return None
        increment = parameters.get(f"{prefix}inc", 0)
        moves_to_go = max(1, parameters.get("movestogo", 30))
        reserve = max(10, remaining // 20)
        available = max(1, remaining - reserve)
        return max(1, min(available, remaining // moves_to_go + increment // 2))

    def _start_search(self, depth: int, movetime: int | None) -> None:
        self._stop_search()
        self.stop_event = Event()
        position = self.position

        def run_search() -> None:
            result = search(position, depth, movetime, self.stop_event.is_set)
            self._emit_result(result)

        self.search_thread = Thread(target=run_search, daemon=True)
        self.search_thread.start()

    def _stop_search(self) -> None:
        thread = self.search_thread
        if thread is not None and thread.is_alive():
            self.stop_event.set()
            thread.join()
        self.search_thread = None

    def _emit_result(self, result: SearchResult) -> None:
        pv = " ".join(move.to_uci() for move in result.principal_variation)
        self._emit(
            f"info depth {result.completed_depth} score cp {result.score} "
            f"nodes {result.nodes} time {result.elapsed_ms} pv {pv}"
        )
        bestmove = result.best_move.to_uci() if result.best_move is not None else "0000"
        self._emit(f"bestmove {bestmove}")

    def _emit(self, text: str) -> None:
        with self.output_lock:
            print(text, file=self.output, flush=True)


def main() -> int:
    return UciEngine().run()


if __name__ == "__main__":
    raise SystemExit(main())
