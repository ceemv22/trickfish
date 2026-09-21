import unittest
from dataclasses import FrozenInstanceError

from trickfish import Move, Position, STARTING_FEN


class MoveTest(unittest.TestCase):
    def test_uci_coordinates(self) -> None:
        self.assertEqual(Move(57, 42).to_uci(), "b1c3")
        self.assertEqual(Move(6, 23).to_uci(), "g8h6")
        self.assertEqual(Move(11, 3, "q").to_uci(), "d7d8q")

    def test_invalid_squares(self) -> None:
        for source, target in ((-1, 0), (0, 64), (64, 0), (0, -1), (5, 5)):
            with self.subTest(source=source, target=target):
                with self.assertRaises(ValueError):
                    Move(source, target)
        for promotion in ("Q", "p", "x", "queen"):
            with self.subTest(promotion=promotion):
                with self.assertRaises(ValueError):
                    Move(11, 3, promotion)

    def test_immutable_value(self) -> None:
        move = Move(57, 42)
        self.assertEqual(move, Move(57, 42))
        self.assertFalse(move.en_passant)
        self.assertTrue(Move(60, 62, castling=True).castling)
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


class CastlingMovesTest(unittest.TestCase):
    def assert_moves(self, fen: str, expected: set[str]) -> None:
        position = Position.from_fen(fen)
        moves = position.pseudo_legal_castling_moves()
        self.assertEqual({move.to_uci() for move in moves}, expected)
        self.assertTrue(all(move.castling for move in moves))
        self.assertEqual(position.to_fen(), fen)

    def test_white_short_and_long_castling(self) -> None:
        self.assert_moves("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1", {"e1c1", "e1g1"})

    def test_black_short_and_long_castling(self) -> None:
        self.assert_moves("r3k2r/8/8/8/8/8/8/4K3 b kq - 0 1", {"e8c8", "e8g8"})

    def test_castling_requires_rights_king_rook_and_empty_path(self) -> None:
        self.assert_moves("4k3/8/8/8/8/8/8/R3K2R w - - 0 1", set())
        self.assert_moves("4k3/8/8/8/8/8/8/4K3 w KQ - 0 1", set())
        self.assert_moves("4k3/8/8/8/8/8/8/R3KNR1 w KQ - 0 1", {"e1c1"})
        self.assert_moves("4k3/8/8/8/8/8/8/R2K3R w KQ - 0 1", set())

    def test_legal_castling_rejects_attacked_king_squares(self) -> None:
        cases = (
            "k3r3/8/8/8/8/8/8/4K2R w K - 0 1",
            "k4r2/8/8/8/8/8/8/4K2R w K - 0 1",
            "k5r1/8/8/8/8/8/8/4K2R w K - 0 1",
            "4k2r/8/8/8/8/8/8/4KR2 b k - 0 1",
        )
        for fen in cases:
            with self.subTest(fen=fen):
                position = Position.from_fen(fen)
                self.assertEqual(position.legal_castling_moves(), tuple())

    def test_legal_castling_is_included_with_king_moves(self) -> None:
        position = Position.from_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
        self.assertEqual(
            {move.to_uci() for move in position.legal_castling_moves()},
            {"e1c1", "e1g1"},
        )
        self.assertTrue(
            {"e1c1", "e1g1"}.issubset(
                {move.to_uci() for move in position.pseudo_legal_king_moves()}
            )
        )


class AttackMapTest(unittest.TestCase):
    def square(self, name: str) -> int:
        return (8 - int(name[1])) * 8 + "abcdefgh".index(name[0])

    def assert_attacked(self, fen: str, square: str, by_side: str) -> None:
        position = Position.from_fen(fen)
        self.assertTrue(position.is_square_attacked(self.square(square), by_side))

    def assert_not_attacked(self, fen: str, square: str, by_side: str) -> None:
        position = Position.from_fen(fen)
        self.assertFalse(position.is_square_attacked(self.square(square), by_side))

    def test_pawn_attacks_for_both_colors(self) -> None:
        self.assert_attacked("7k/8/8/3P4/8/8/8/K7 w - - 0 1", "c6", "w")
        self.assert_attacked("7k/8/8/3P4/8/8/8/K7 w - - 0 1", "e6", "w")
        self.assert_not_attacked("7k/8/8/3P4/8/8/8/K7 w - - 0 1", "d6", "w")
        self.assert_attacked("7k/8/8/3p4/8/8/8/K7 b - - 0 1", "c4", "b")
        self.assert_attacked("7k/8/8/3p4/8/8/8/K7 b - - 0 1", "e4", "b")

    def test_knight_and_king_attacks(self) -> None:
        self.assert_attacked("7k/8/8/8/3N4/8/8/K7 w - - 0 1", "f5", "w")
        self.assert_not_attacked("7k/8/8/8/3N4/8/8/K7 w - - 0 1", "d5", "w")
        self.assert_attacked("7k/8/8/8/3K4/8/8/8 w - - 0 1", "e5", "w")

    def test_sliding_attacks_stop_at_a_blocker(self) -> None:
        self.assert_attacked("7k/8/8/8/3B4/8/8/K7 w - - 0 1", "h8", "w")
        self.assert_attacked("7k/8/8/8/3R4/8/8/K7 w - - 0 1", "d8", "w")
        self.assert_attacked("7k/8/8/8/3Q4/8/8/K7 w - - 0 1", "h4", "w")
        self.assert_not_attacked("7k/8/8/8/3B4/8/5P2/K7 w - - 0 1", "g1", "w")
        self.assert_not_attacked("7k/8/8/8/3R4/8/3P4/K7 w - - 0 1", "d1", "w")
        self.assert_attacked("3R3k/3P4/8/8/1R6/8/8/K7 w - - 0 1", "d4", "w")

    def test_invalid_attack_query(self) -> None:
        position = Position.from_fen("7k/8/8/8/8/8/8/K7 w - - 0 1")
        with self.assertRaises(ValueError):
            position.is_square_attacked(64, "w")
        with self.assertRaises(ValueError):
            position.is_square_attacked(0, "white")


class LegalMovesTest(unittest.TestCase):
    def test_starting_position_has_twenty_legal_moves(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        self.assertEqual(len(position.legal_moves()), 20)

    def test_pinned_knight_is_filtered(self) -> None:
        position = Position.from_fen("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1")
        self.assertTrue(any(move.from_square == 52 for move in position.pseudo_legal_moves()))
        self.assertFalse(any(move.from_square == 52 for move in position.legal_moves()))

    def test_king_cannot_move_into_attack(self) -> None:
        position = Position.from_fen("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertIn("e1e2", {move.to_uci() for move in position.pseudo_legal_moves()})
        self.assertNotIn("e1e2", {move.to_uci() for move in position.legal_moves()})

    def test_en_passant_that_exposes_king_is_filtered(self) -> None:
        position = Position.from_fen("k7/8/8/K2pP2r/8/8/8/8 w - d6 0 1")
        self.assertIn("e5d6", {move.to_uci() for move in position.pseudo_legal_moves()})
        self.assertNotIn("e5d6", {move.to_uci() for move in position.legal_moves()})


class PerftTest(unittest.TestCase):
    def test_starting_position_counts(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        self.assertEqual(position.perft(0), 1)
        self.assertEqual(position.perft(1), 20)
        self.assertEqual(position.perft(2), 400)
        self.assertEqual(position.perft(3), 8902)

    def test_standard_perft_positions(self) -> None:
        cases = (
            (
                "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
                (48, 2039, 97862),
            ),
            (
                "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
                (14, 191, 2812),
            ),
            (
                "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
                (6, 264, 9467),
            ),
            (
                "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
                (44, 1486, 62379),
            ),
        )
        for fen, expected in cases:
            with self.subTest(fen=fen):
                position = Position.from_fen(fen)
                self.assertEqual(
                    tuple(position.perft(depth) for depth in range(1, 4)), expected
                )

    def test_divide_sums_to_the_perft_count(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        divide = position.perft_divide(2)
        self.assertEqual(len(divide), 20)
        self.assertEqual(sum(nodes for _, nodes in divide), 400)
        self.assertTrue(all(nodes == 20 for _, nodes in divide))

    def test_negative_depth_is_rejected(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        with self.assertRaises(ValueError):
            position.perft(-1)

    def test_divide_rejects_depth_zero(self) -> None:
        position = Position.from_fen(STARTING_FEN)
        with self.assertRaises(ValueError):
            position.perft_divide(0)


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

    def test_white_and_black_promotions(self) -> None:
        self.assert_moves(
            "7k/3P4/8/8/8/8/8/K7 w - - 0 1",
            {"d7d8q", "d7d8r", "d7d8b", "d7d8n"},
        )
        self.assert_moves(
            "7k/8/8/8/8/8/3p4/K7 b - - 0 1",
            {"d2d1q", "d2d1r", "d2d1b", "d2d1n"},
        )

    def test_promotion_captures_and_enemy_king(self) -> None:
        self.assert_moves(
            "2k1n3/3P4/8/8/8/8/8/K7 w - - 0 1",
            {
                "d7d8q", "d7d8r", "d7d8b", "d7d8n",
                "d7e8q", "d7e8r", "d7e8b", "d7e8n",
            },
        )

    def test_white_and_black_en_passant(self) -> None:
        white_position = Position.from_fen(
            "7k/8/8/3pP3/8/8/8/K7 w - d6 0 1"
        )
        white_moves = white_position.pseudo_legal_pawn_moves()
        self.assertEqual({move.to_uci() for move in white_moves}, {"e5d6", "e5e6"})
        self.assertTrue(next(move for move in white_moves if move.to_uci() == "e5d6").en_passant)

        black_position = Position.from_fen(
            "7k/8/8/8/3Pp3/8/8/K7 b - d3 0 1"
        )
        black_moves = black_position.pseudo_legal_pawn_moves()
        self.assertEqual({move.to_uci() for move in black_moves}, {"e4d3", "e4e3"})
        self.assertTrue(next(move for move in black_moves if move.to_uci() == "e4d3").en_passant)

    def test_en_passant_requires_the_captured_pawn(self) -> None:
        position = Position.from_fen("7k/8/8/4P3/8/8/8/K7 w - d6 0 1")
        moves = position.pseudo_legal_pawn_moves()
        self.assertEqual({move.to_uci() for move in moves}, {"e5e6"})
