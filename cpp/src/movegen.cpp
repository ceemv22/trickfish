#include "trickfish/movegen.hpp"

#include "trickfish/attacks.hpp"
#include "trickfish/bitboard.hpp"
#include "trickfish/piece.hpp"

namespace trickfish {
namespace {

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

}

MoveList generate_non_pawn_pseudo_legal_moves(const Position& position) {
    MoveList moves;
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
    return moves;
}

}
