import unittest
from dataclasses import FrozenInstanceError

from trickfish import Move, Position, STARTING_FEN


class MoveTest(unittest.TestCase):
    def test_uci_coordinates(self) -> None:
        self.assertEqual(Move(57, 42).to_uci(), "b1c3")
        self.assertEqual(Move(6, 23).to_uci(), "g8h6")

    def test_invalid_squares(self) -> None:
        for source, target in ((-1, 0), (0, 64), (64, 0), (0, -1), (5, 5)):
            with self.subTest(source=source, target=target):
                with self.assertRaises(ValueError):
                    Move(source, target)

    def test_immutable_value(self) -> None:
        move = Move(57, 42)
        self.assertEqual(move, Move(57, 42))
        with self.assertRaises(FrozenInstanceError):
            move.to_square = 40


class KnightMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_knight_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_starting_position_both_colors(self) -> None:
        self.assert_moves(STARTING_FEN, {"b1a3", "b1c3", "g1f3", "g1h3"})
        self.assert_moves(
            STARTING_FEN.replace(" w ", " b "),
            {"b8a6", "b8c6", "g8f6", "g8h6"},
        )

    def test_center(self) -> None:
        self.assert_moves(
            "7k/8/8/8/3N4/8/8/K7 w - - 0 1",
            {"d4b3", "d4b5", "d4c2", "d4c6", "d4e2", "d4e6", "d4f3", "d4f5"},
        )

    def test_corners_do_not_wrap(self) -> None:
        cases = (
            ("N6k/8/8/8/8/8/8/7K w - - 0 1", {"a8b6", "a8c7"}),
            ("k6N/8/8/8/8/8/8/K7 w - - 0 1", {"h8f7", "h8g6"}),
            ("7k/8/8/8/8/8/8/N6K w - - 0 1", {"a1b3", "a1c2"}),
            ("k7/8/8/8/8/8/8/K6N w - - 0 1", {"h1f2", "h1g3"}),
        )
        for fen, expected in cases:
            with self.subTest(fen=fen):
                self.assert_moves(fen, expected)

    def test_friendly_piece_blocks_and_enemy_piece_can_be_captured(self) -> None:
        self.assert_moves("7k/8/8/8/8/1P6/2p5/N6K w - - 0 1", {"a1c2"})
        self.assert_moves("n6k/2P5/1p6/8/8/8/8/7K b - - 0 1", {"a8c7"})

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves("8/8/8/8/8/1k6/8/N6K w - - 0 1", {"a1c2"})

    def test_pinned_knight_still_has_pseudo_legal_moves(self) -> None:
        self.assert_moves(
            "k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1",
            {"e2c1", "e2c3", "e2d4", "e2f4", "e2g1", "e2g3"},
        )

    def test_no_knights(self) -> None:
        self.assert_moves("7k/8/8/8/8/8/8/K7 w - - 0 1", set())


class BishopMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_bishop_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_center(self) -> None:
        self.assert_moves(
            "8/7k/8/8/3B4/8/K7/8 w - - 0 1",
            {
                "d4a1", "d4a7", "d4b2", "d4b6", "d4c3", "d4c5",
                "d4e3", "d4e5", "d4f2", "d4f6", "d4g1", "d4g7", "d4h8",
            },
        )

    def test_blocking_and_captures(self) -> None:
        self.assert_moves(
            "8/7k/1p6/8/3B4/8/K4P2/8 w - - 0 1",
            {
                "d4a1", "d4b2", "d4b6", "d4c3", "d4c5",
                "d4e3", "d4e5", "d4f6", "d4g7", "d4h8",
            },
        )

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves(
            "8/8/8/8/3B4/2k5/K7/8 w - - 0 1",
            {
                "d4a7", "d4b6", "d4c5", "d4e3", "d4e5", "d4f2",
                "d4f6", "d4g1", "d4g7", "d4h8",
            },
        )

    def test_black_bishop(self) -> None:
        self.assert_moves(
            "7k/8/8/1B6/8/3b4/8/K7 b - - 0 1",
            {"d3b1", "d3b5", "d3c2", "d3c4", "d3e2", "d3e4", "d3f1", "d3f5", "d3g6", "d3h7"},
        )


class RookMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_rook_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_center(self) -> None:
        self.assert_moves(
            "8/7k/8/8/3R4/8/K7/8 w - - 0 1",
            {
                "d4a4", "d4b4", "d4c4", "d4d1", "d4d2", "d4d3",
                "d4d5", "d4d6", "d4d7", "d4d8", "d4e4", "d4f4",
                "d4g4", "d4h4",
            },
        )

    def test_blocking_and_captures(self) -> None:
        self.assert_moves(
            "7k/8/8/8/2pR1P2/8/K7/8 w - - 0 1",
            {
                "d4c4", "d4d1", "d4d2", "d4d3", "d4d5", "d4d6",
                "d4d7", "d4d8", "d4e4",
            },
        )

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves(
            "8/8/8/8/3Rk3/8/K7/8 w - - 0 1",
            {"d4a4", "d4b4", "d4c4", "d4d1", "d4d2", "d4d3", "d4d5", "d4d6", "d4d7", "d4d8"},
        )

    def test_black_rook(self) -> None:
        self.assert_moves(
            "7k/8/8/8/8/3r4/K7/8 b - - 0 1",
            {
                "d3a3", "d3b3", "d3c3", "d3d1", "d3d2", "d3d4",
                "d3d5", "d3d6", "d3d7", "d3d8", "d3e3", "d3f3",
                "d3g3", "d3h3",
            },
        )


class QueenMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_queen_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_center(self) -> None:
        self.assert_moves(
            "8/7k/8/8/3Q4/8/K7/8 w - - 0 1",
            {
                "d4a1", "d4a4", "d4a7", "d4b2", "d4b4", "d4b6",
                "d4c3", "d4c4", "d4c5", "d4d1", "d4d2", "d4d3",
                "d4d5", "d4d6", "d4d7", "d4d8", "d4e3", "d4e4",
                "d4e5", "d4f2", "d4f4", "d4f6", "d4g1", "d4g4",
                "d4g7", "d4h4", "d4h8",
            },
        )

    def test_blocking_and_captures(self) -> None:
        self.assert_moves(
            "8/7k/1p6/8/2pQ1P2/8/K7/8 w - - 0 1",
            {
                "d4a1", "d4b2", "d4b6", "d4c3", "d4c4",
                "d4c5", "d4d1", "d4d2", "d4d3", "d4d5", "d4d6",
                "d4d7", "d4d8", "d4e3", "d4e4", "d4e5", "d4f2",
                "d4f6", "d4g1", "d4g7", "d4h8",
            },
        )

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves(
            "8/8/8/8/3Qk3/8/K7/8 w - - 0 1",
            {
                "d4a1", "d4a4", "d4a7", "d4b2", "d4b4", "d4b6",
                "d4c3", "d4c4", "d4c5", "d4d1", "d4d2", "d4d3",
                "d4d5", "d4d6", "d4d7", "d4d8", "d4e3", "d4e5",
                "d4f2", "d4f6", "d4g1", "d4g7", "d4h8",
            },
        )

    def test_black_queen(self) -> None:
        self.assert_moves(
            "7k/8/8/1Q6/8/3q4/8/K7 b - - 0 1",
            {
                "d3a3", "d3b1", "d3b3", "d3b5", "d3c2", "d3c3",
                "d3c4", "d3d1", "d3d2", "d3d4", "d3d5", "d3d6",
                "d3d7", "d3d8", "d3e2", "d3e3", "d3e4", "d3f1",
                "d3f3", "d3f5", "d3g3", "d3g6", "d3h3", "d3h7",
            },
        )


class KingMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_king_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_center(self) -> None:
        self.assert_moves(
            "8/7k/8/8/3K4/8/8/8 w - - 0 1",
            {"d4c3", "d4c4", "d4c5", "d4d3", "d4d5", "d4e3", "d4e4", "d4e5"},
        )

    def test_corner_does_not_wrap(self) -> None:
        self.assert_moves("7k/8/8/8/8/8/8/K7 w - - 0 1", {"a1a2", "a1b1", "a1b2"})

    def test_blocking_and_captures(self) -> None:
        self.assert_moves(
            "8/7k/8/8/2pKp3/3P4/8/8 w - - 0 1",
            {"d4c3", "d4c4", "d4c5", "d4d5", "d4e3", "d4e4", "d4e5"},
        )

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves(
            "8/8/8/8/3Kk3/8/8/8 w - - 0 1",
            {"d4c3", "d4c4", "d4c5", "d4d3", "d4d5", "d4e3", "d4e5"},
        )

    def test_black_king(self) -> None:
        self.assert_moves(
            "8/8/8/8/3k4/8/7K/8 b - - 0 1",
            {"d4c3", "d4c4", "d4c5", "d4d3", "d4d5", "d4e3", "d4e4", "d4e5"},
        )


class PawnMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_pawn_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertEqual(len(moves), len(expected))
        self.assertEqual(position.to_fen(), fen)

    def test_white_and_black_single_steps(self) -> None:
        self.assert_moves("7k/8/8/8/3P4/8/8/K7 w - - 0 1", {"d4d5"})
        self.assert_moves("7k/8/8/3p4/8/8/K7/8 b - - 0 1", {"d5d4"})

    def test_white_and_black_starting_double_steps(self) -> None:
        self.assert_moves("7k/8/8/8/8/8/3P4/K7 w - - 0 1", {"d2d3", "d2d4"})
        self.assert_moves("7k/3p4/8/8/8/8/K7/8 b - - 0 1", {"d7d6", "d7d5"})

    def test_double_step_requires_two_empty_squares(self) -> None:
        self.assert_moves("7k/8/8/8/3n4/8/3P4/K7 w - - 0 1", {"d2d3"})
        self.assert_moves("7k/3p4/8/3N4/8/8/K7/8 b - - 0 1", {"d7d6"})

    def test_white_blocking_and_captures(self) -> None:
        self.assert_moves(
            "7k/8/8/2pNp3/3P4/8/8/K7 w - - 0 1",
            {"d4c5", "d4e5"},
        )

    def test_black_blocking_and_captures(self) -> None:
        self.assert_moves(
            "7k/8/8/3p4/2NnN3/8/K7/8 b - - 0 1",
            {"d5c4", "d5e4"},
        )

    def test_enemy_king_cannot_be_captured(self) -> None:
        self.assert_moves(
            "8/8/8/2k1n3/3P4/8/8/K7 w - - 0 1",
            {"d4d5", "d4e5"},
        )

    def test_promotion_rank_waits_for_promotion_support(self) -> None:
        self.assert_moves("7k/3P4/8/8/8/8/8/K7 w - - 0 1", set())
