#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>

#include "trickfish/bitboard.hpp"
#include "trickfish/piece.hpp"

namespace trickfish {

class Position {
public:
    static Position from_fen(std::string_view fen);

    [[nodiscard]] std::string to_fen() const;
    [[nodiscard]] char piece_at(std::uint8_t square) const;
    [[nodiscard]] Bitboard pieces(Color color, PieceType type) const;
    [[nodiscard]] Bitboard occupancy(Color color) const;
    [[nodiscard]] Bitboard occupancy() const;
    [[nodiscard]] Bitboard attacks_by(Color color) const;
    [[nodiscard]] bool in_check(Color color) const;
    [[nodiscard]] Color side_to_move() const;
    [[nodiscard]] std::uint8_t castling_rights() const;
    [[nodiscard]] std::int8_t en_passant_square() const;
    [[nodiscard]] int halfmove_clock() const;
    [[nodiscard]] int fullmove_number() const;

private:
    std::array<Bitboard, 12> pieces_{};
    Color side_to_move_ = Color::white;
    std::uint8_t castling_rights_ = 0;
    std::int8_t en_passant_square_ = -1;
    int halfmove_clock_ = 0;
    int fullmove_number_ = 1;
};

}
