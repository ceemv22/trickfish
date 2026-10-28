import pathlib
import queue
import subprocess
import sys
import threading
import time
import unittest

BINARY = str(pathlib.Path(sys.argv.pop(1)).resolve())
WHITE_MOVES = {f"{file}2{file}{rank}" for file in "abcdefgh" for rank in "34"} | {"b1a3", "b1c3", "g1f3", "g1h3"}
BLACK_MOVES = {f"{file}7{file}{rank}" for file in "abcdefgh" for rank in "65"} | {"b8a6", "b8c6", "g8f6", "g8h6"}

class UciProcessTests(unittest.TestCase):
    def setUp(self):
        self.process = subprocess.Popen([BINARY, "--uci"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.events = queue.Queue()
        self.transcript = []
        def read():
            for line in self.process.stdout:
                self.events.put(line.rstrip("\r\n"))
            self.events.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def send(self, text):
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()

    def until(self, prefix):
        deadline = time.monotonic() + 10
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.fail(f"timeout waiting for {prefix}: {self.transcript}")
            try:
                line = self.events.get(timeout=remaining)
            except queue.Empty:
                self.fail(f"timeout waiting for {prefix}: {self.transcript}")
            if line is None:
                self.fail(f"engine exited before {prefix}: {self.transcript}")
            self.transcript.append(line)
            if line.startswith(prefix):
                return line

    def tearDown(self):
        try:
            if self.process.poll() is None:
                self.send("quit")
            self.process.wait(timeout=5)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait(timeout=5)
        finally:
            self.process.stdin.close()
            self.reader.join(timeout=1)
            self.process.stdout.close()
        self.assertEqual(self.process.returncode, 0, self.transcript)

    def test_handshake_and_completed_depth(self):
        self.send("uci")
        self.until("uciok")
        self.assertIn("id name Trickfish C++", self.transcript)
        self.send("isready")
        self.until("readyok")
        self.send("position startpos")
        self.send("go depth 1")
        best = self.until("bestmove ").split()[1]
        self.assertIn(best, WHITE_MOVES)
        self.assertTrue(any(line.startswith("info depth 1 ") and " score cp " in line for line in self.transcript))

    def test_readiness_during_infinite_search(self):
        self.send("go infinite")
        self.send("isready")
        self.until("readyok")
        self.assertFalse(any(line.startswith("bestmove ") for line in self.transcript))
        self.send("stop")
        self.assertIn(self.until("bestmove ").split()[1], WHITE_MOVES)
        self.send("stop")
        self.send("isready")
        self.until("readyok")
        self.assertEqual(sum(line.startswith("bestmove ") for line in self.transcript), 1)

    def test_transactional_position_and_zero_budget(self):
        self.send("position startpos moves e2e4")
        self.send("position startpos moves d2d4 d7d5 g1z9")
        self.until("info string error:")
        self.send("go nodes 0")
        self.assertIn(self.until("bestmove ").split()[1], BLACK_MOVES)
        self.assertTrue(any(line.startswith("info depth 0 nodes 0") for line in self.transcript))

    def test_movetime_and_new_game(self):
        self.send("position startpos moves e2e4")
        self.send("ucinewgame")
        self.send("go movetime 0")
        self.assertIn(self.until("bestmove ").split()[1], WHITE_MOVES)
        self.assertTrue(any(line.startswith("info depth 0 nodes 0") for line in self.transcript))

    def test_mate_reporting(self):
        self.send("position fen 7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
        self.send("go depth 1")
        self.assertNotEqual(self.until("bestmove "), "bestmove 0000")
        self.assertTrue(any(" score mate 1" in line for line in self.transcript))

    def test_game_history_reaches_search(self):
        self.send("position fen rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 "
            "moves g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8")
        self.send("go depth 1")
        self.until("bestmove ")
        self.assertTrue(any(" score cp 0" in line for line in self.transcript))
        self.assertFalse(any("error:" in line for line in self.transcript))

    def test_default_entrypoint(self):
        result = subprocess.run([BINARY], input="uci\nisready\nquit\n", text=True,
            capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("uciok\n", result.stdout)
        self.assertIn("readyok\n", result.stdout)

    def test_invalid_limits_keep_session_alive(self):
        for command in ["go depth 0", "go nodes -1", "go movetime 18446744073709551615", "go depth"]:
            self.send(command)
            self.until("info string error:")
        self.send("isready")
        self.until("readyok")
        self.assertFalse(any(line.startswith("bestmove ") for line in self.transcript))

    def test_unsupported_clock_is_explicit(self):
        self.send("go wtime 1000 btime 1000")
        self.assertIn("unsupported go parameter: wtime", self.until("info string error:"))
        self.send("isready")
        self.until("readyok")

if __name__ == "__main__":
    unittest.main()
