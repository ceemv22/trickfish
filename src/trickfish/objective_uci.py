import hashlib
import pathlib
import queue
import subprocess
import threading
import time

from .position import Position
from .objective_score import ObjectiveScore


class UciObjective:
    def __init__(self, command, depth=10, timeout=30.0):
        if not command or type(depth) is not int or depth < 1 or not 0 < timeout < float("inf"):
            raise ValueError("command, positive depth and finite timeout are required")
        self.command = list(command)
        self.depth = depth
        self.timeout = timeout
        self.records = []
        self.cache = {}
        self.identity = []
        self.lines = queue.Queue()
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self._send("uci")
            for line in self._until("uciok"):
                if line.startswith("id "):
                    self.identity.append(line)
            self._send("isready")
            self._until("readyok")
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                self.lines.put(line.strip())
        finally:
            self.lines.put(None)

    def _send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _until(self, token):
        deadline = time.monotonic() + self.timeout
        output = []
        while True:
            try:
                line = self.lines.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as error:
                raise TimeoutError("UCI engine did not complete " + token) from error
            if line is None:
                raise RuntimeError("UCI engine exited before " + token)
            output.append(line)
            if line == token or line.startswith(token + " "):
                return output

    def __call__(self, position: Position, perspective: str) -> float:
        score = self.evaluate(position, perspective)
        if score.cp is None:
            self.close()
            raise ValueError("mate cannot be represented by the legacy centipawn objective")
        return float(score.cp)

    def evaluate(self, position: Position, perspective: str) -> ObjectiveScore:
        if perspective not in {"w", "b"}:
            raise ValueError("perspective must be w or b")
        fen = position.to_fen()
        if fen not in self.cache:
            status = position.game_status()
            if status == "checkmate":
                score = ObjectiveScore(mate_moves=0, winning=False)
                self.records.append({"fen": fen, "score_side_to_move": score.as_dict(), "terminal": status})
            elif status == "stalemate" or position.is_insufficient_material():
                score = ObjectiveScore(cp=0)
                self.records.append({"fen": fen, "cp_side_to_move": 0, "score_side_to_move": score.as_dict(), "terminal": status})
            else:
                try:
                    self._send("ucinewgame")
                    self._send("isready")
                    self._until("readyok")
                    self._send("position fen " + fen)
                    self._send("go depth " + str(self.depth))
                    output = self._until("bestmove")
                    final = None
                    for line in output:
                        fields = line.split()
                        if not fields or fields[0] != "info" or "score" not in fields or "depth" not in fields:
                            continue
                        if "multipv" in fields and fields[fields.index("multipv") + 1] != "1":
                            continue
                        index = fields.index("score")
                        completed = int(fields[fields.index("depth") + 1])
                        final = (completed, fields[index + 1], int(fields[index + 2]),
                                 "lowerbound" in fields or "upperbound" in fields, line)
                    if final is None or final[0] < self.depth or final[1] not in {"cp", "mate"} or final[3]:
                        raise ValueError("objective requires a completed exact cp or mate score; bounds are unsupported")
                    if final[1] == "mate" and final[2] == 0:
                        raise ValueError("nonterminal position cannot report mate zero")
                    legal = {move.to_uci() for move in position.legal_moves()}
                    if output[-1].split()[1] not in legal:
                        raise ValueError("engine returned an illegal bestmove")
                    score = (ObjectiveScore(cp=final[2]) if final[1] == "cp" else
                             ObjectiveScore(mate_moves=abs(final[2]), winning=final[2] > 0))
                    self.records.append({"fen": fen, "cp_side_to_move": score.cp,
                                         "score_side_to_move": score.as_dict(), "info": final[4], "bestmove": output[-1]})
                except BaseException:
                    self.close()
                    raise
            self.cache[fen] = score
        score = self.cache[fen]
        return score if perspective == position.side_to_move else score.inverted()

    def provenance(self):
        executable = pathlib.Path(self.command[0]).resolve(strict=True)
        return {"command": self.command, "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "identity": self.identity, "depth": self.depth, "timeout_seconds": self.timeout,
                "options": "engine defaults; ucinewgame before every uncached position", "evaluations": self.records}

    def close(self):
        if self.process.poll() is None:
            try:
                self._send("quit")
                self.process.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        self.reader.join(timeout=1)
        for stream in (self.process.stdin, self.process.stdout):
            try:
                stream.close()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
