#pragma once

#include <bit>
#include <cstdint>
#include <stdexcept>

namespace trickfish {

using Bitboard = std::uint64_t;

inline constexpr Bitboard square_bit(std::uint8_t square) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return Bitboard{1} << square;
}

inline constexpr std::uint8_t pop_lsb(Bitboard& bitboard) {
    if (bitboard == 0) {
        throw std::invalid_argument("cannot pop an empty bitboard");
    }
    const auto square = static_cast<std::uint8_t>(std::countr_zero(bitboard));
    bitboard &= bitboard - 1;
    return square;
}

}
