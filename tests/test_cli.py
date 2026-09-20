import io
import unittest
from contextlib import redirect_stdout

from trickfish.cli import main


class CliTest(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(arguments)
        return result, output.getvalue()

    def test_moves_uses_the_starting_position_by_default(self) -> None:
        result, output = self.invoke(["moves"])
        self.assertEqual(result, 0)
        self.assertEqual(output.splitlines(), ["b1a3", "b1c3", "g1f3", "g1h3"])

    def test_moves_accepts_a_fen(self) -> None:
        result, output = self.invoke(
            ["moves", "8/7k/8/8/3B4/8/K7/8 w - - 0 1"]
        )
        self.assertEqual(result, 0)
        self.assertEqual(
            set(output.splitlines()),
            {
                "d4a1", "d4a7", "d4b2", "d4b6", "d4c3", "d4c5",
                "d4e3", "d4e5", "d4f2", "d4f6", "d4g1", "d4g7", "d4h8",
                "a2a1", "a2a3", "a2b1", "a2b2", "a2b3",
            },
        )

    def test_fen_without_a_command_still_renders_the_position(self) -> None:
        result, output = self.invoke(["8/8/8/8/8/8/K7/7k w - - 0 1"])
        self.assertEqual(result, 0)
        self.assertIn("2  K . . . . . . .", output)
