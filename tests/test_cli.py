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
        self.assertEqual(
            output.splitlines(),
            [
                "b1a3", "b1c3", "g1f3", "g1h3", "a2a3", "a2a4",
                "b2b3", "b2b4", "c2c3", "c2c4", "d2d3", "d2d4",
                "e2e3", "e2e4", "f2f3", "f2f4", "g2g3", "g2g4",
                "h2h3", "h2h4",
            ],
        )

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

    def test_moves_filters_pinned_piece_while_pseudo_moves_keeps_it(self) -> None:
        fen = "k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1"
        _, legal_output = self.invoke(["moves", fen])
        _, pseudo_output = self.invoke(["pseudo-moves", fen])
        self.assertNotIn("e2c1", legal_output.splitlines())
        self.assertIn("e2c1", pseudo_output.splitlines())

    def test_perft_reports_the_node_count(self) -> None:
        result, output = self.invoke(["perft", "2"])
        self.assertEqual(result, 0)
        self.assertEqual(output, "400\n")

    def test_divide_reports_each_root_move(self) -> None:
        result, output = self.invoke(["divide", "2"])
        self.assertEqual(result, 0)
        self.assertEqual(len(output.splitlines()), 20)
        self.assertEqual(set(output.splitlines()), {
            "a2a3: 20", "a2a4: 20", "b1a3: 20", "b1c3: 20", "b2b3: 20",
            "b2b4: 20", "c2c3: 20", "c2c4: 20", "d2d3: 20", "d2d4: 20",
            "e2e3: 20", "e2e4: 20", "f2f3: 20", "f2f4: 20", "g1f3: 20",
            "g1h3: 20", "g2g3: 20", "g2g4: 20", "h2h3: 20", "h2h4: 20",
        })

    def test_status_reports_checkmate(self) -> None:
        result, output = self.invoke(
            ["status", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"]
        )
        self.assertEqual(result, 0)
        self.assertEqual(output, "checkmate\n")

    def test_fen_without_a_command_still_renders_the_position(self) -> None:
        result, output = self.invoke(["8/8/8/8/8/8/K7/7k w - - 0 1"])
        self.assertEqual(result, 0)
        self.assertIn("2  K . . . . . . .", output)
