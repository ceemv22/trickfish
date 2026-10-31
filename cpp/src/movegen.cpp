#include "trickfish/movegen.hpp"

#include <array>

#include "trickfish/attacks.hpp"
#include "trickfish/bitboard.hpp"
#include "trickfish/piece.hpp"

namespace trickfish {
namespace {

constexpr std::array promotion_pieces = {'q', 'r', 'b', 'n'};

template<typename AttackFunction>
void append_moves(
    MoveList& moves,
    Bitboard sources,
    Bitboard own_occupancy,
    AttackFunction&& attacks
) {
    while (sources != 0) {
        const auto from = pop_lsb(sources);
        Bitboard destinations = attacks(from) & ~own_occupancy;
        while (destinations != 0) {
            moves.push(Move(from, pop_lsb(destinations)));
        }
    }
}

void append_pawn_move(MoveList& moves, std::uint8_t from, std::uint8_t to, bool promotion) {
    if (promotion) {
        for (const char piece : promotion_pieces) {
            moves.push(Move(from, to, piece));
        }
    } else {
        moves.push(Move(from, to));
    }
}

void append_castling_moves(MoveList& moves, const Position& position) {
    const auto color = position.side_to_move();
    const auto enemy_attacks = position.attacks_by(opposite(color));
    const auto occupied = position.occupancy();
    const std::uint8_t king_square = color == Color::white ? 60 : 4;
    const std::uint8_t kingside_rook = color == Color::white ? 63 : 7;
    const std::uint8_t queenside_rook = color == Color::white ? 56 : 0;
    const auto king = position.pieces(color, PieceType::king);
    const auto rooks = position.pieces(color, PieceType::rook);

    if ((king & square_bit(king_square)) == 0 || (enemy_attacks & square_bit(king_square)) != 0) {
        return;
    }

    const auto kingside_path = square_bit(static_cast<std::uint8_t>(king_square + 1)) |
        square_bit(static_cast<std::uint8_t>(king_square + 2));
    if (position.has_castling_right(color, true) &&
        (rooks & square_bit(kingside_rook)) != 0 &&
        (occupied & kingside_path) == 0 &&
        (enemy_attacks & kingside_path) == 0) {
        moves.push(Move(king_square, static_cast<std::uint8_t>(king_square + 2), '\0', false, true));
    }

    const auto queenside_empty = square_bit(static_cast<std::uint8_t>(king_square - 1)) |
        square_bit(static_cast<std::uint8_t>(king_square - 2)) |
        square_bit(static_cast<std::uint8_t>(king_square - 3));
    const auto queenside_king_path = square_bit(static_cast<std::uint8_t>(king_square - 1)) |
        square_bit(static_cast<std::uint8_t>(king_square - 2));
    if (position.has_castling_right(color, false) &&
        (rooks & square_bit(queenside_rook)) != 0 &&
        (occupied & queenside_empty) == 0 &&
        (enemy_attacks & queenside_king_path) == 0) {
        moves.push(Move(king_square, static_cast<std::uint8_t>(king_square - 2), '\0', false, true));
    }
}

void append_non_pawn_moves(MoveList& moves, const Position& position) {
    const auto color = position.side_to_move();
    const auto own_occupancy = position.occupancy(color);
    const auto occupancy = position.occupancy();

    append_moves(
        moves,
        position.pieces(color, PieceType::knight),
        own_occupancy,
        [](std::uint8_t square) { return knight_attacks(square); }
    );
    append_moves(
        moves,
        position.pieces(color, PieceType::bishop),
        own_occupancy,
        [occupancy](std::uint8_t square) { return bishop_attacks(square, occupancy); }
    );
    append_moves(
        moves,
        position.pieces(color, PieceType::rook),
        own_occupancy,
        [occupancy](std::uint8_t square) { return rook_attacks(square, occupancy); }
    );
    append_moves(
        moves,
        position.pieces(color, PieceType::queen),
        own_occupancy,
        [occupancy](std::uint8_t square) { return queen_attacks(square, occupancy); }
    );
    append_moves(
        moves,
        position.pieces(color, PieceType::king),
        own_occupancy,
        [](std::uint8_t square) { return king_attacks(square); }
    );
    append_castling_moves(moves, position);
}

void append_pawn_moves(MoveList& moves, const Position& position) {
    const auto color = position.side_to_move();
    const auto occupied = position.occupancy();
    const auto enemy_occupancy = position.occupancy(opposite(color));
    const int push = color == Color::white ? -8 : 8;
    const int start_rank = color == Color::white ? 6 : 1;
    const int promotion_rank = color == Color::white ? 0 : 7;
    const int en_passant = position.en_passant_square();
    Bitboard pawns = position.pieces(color, PieceType::pawn);

    while (pawns != 0) {
        const auto from = pop_lsb(pawns);
        const int from_rank = from / 8;
        const int single = static_cast<int>(from) + push;
        if (single >= 0 && single < 64 && (occupied & square_bit(static_cast<std::uint8_t>(single))) == 0) {
            const bool promotion = single / 8 == promotion_rank;
            append_pawn_move(moves, from, static_cast<std::uint8_t>(single), promotion);
            const int double_push = single + push;
            if (from_rank == start_rank && (occupied & square_bit(static_cast<std::uint8_t>(double_push))) == 0) {
                moves.push(Move(from, static_cast<std::uint8_t>(double_push)));
            }
        }

        Bitboard captures = pawn_attacks(color, from) & enemy_occupancy;
        while (captures != 0) {
            const auto to = pop_lsb(captures);
            append_pawn_move(moves, from, to, to / 8 == promotion_rank);
        }

        if (en_passant >= 0) {
            const auto target = static_cast<std::uint8_t>(en_passant);
            const int captured_square = en_passant - push;
            const bool target_is_empty = (occupied & square_bit(target)) == 0;
            const bool target_is_attacked = (pawn_attacks(color, from) & square_bit(target)) != 0;
            const bool captured_pawn_exists = captured_square >= 0 && captured_square < 64 &&
                (position.pieces(opposite(color), PieceType::pawn) &
                    square_bit(static_cast<std::uint8_t>(captured_square))) != 0;
            if (target_is_empty && target_is_attacked && captured_pawn_exists) {
                moves.push(Move(from, target, '\0', true));
            }
        }
    }
}

}

MoveList generate_non_pawn_pseudo_legal_moves(const Position& position) {
    MoveList moves;
    append_non_pawn_moves(moves, position);
    return moves;
}

MoveList generate_pawn_pseudo_legal_moves(const Position& position) {
    MoveList moves;
    append_pawn_moves(moves, position);
    return moves;
}

MoveList generate_pseudo_legal_moves(const Position& position) {
    MoveList moves;
    append_non_pawn_moves(moves, position);
    append_pawn_moves(moves, position);
    return moves;
}

MoveList generate_legal_moves(Position& position) {
    MoveList legal_moves;
    const auto moving_color = position.side_to_move();
    const auto pseudo_legal_moves = generate_pseudo_legal_moves(position);
    for (const auto& move : pseudo_legal_moves) {
        const auto undo = position.make_move(move);
        const bool legal = !position.in_check(moving_color);
        position.unmake_move(move, undo);
        if (legal) {
            legal_moves.push(move);
        }
    }
    return legal_moves;
}

}
