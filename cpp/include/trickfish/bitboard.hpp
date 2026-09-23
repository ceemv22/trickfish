#pragma once

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

}
