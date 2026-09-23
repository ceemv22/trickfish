#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>

#include "trickfish/bitboard.hpp"

namespace trickfish {
namespace detail {

template<std::size_t Size>
consteval Bitboard jump_attacks_for(
    std::uint8_t square,
    const std::array<std::pair<int, int>, Size>& offsets
) {
    const int rank = square / 8;
    const int file = square % 8;
    Bitboard attacks = 0;
    for (const auto [rank_offset, file_offset] : offsets) {
        const int target_rank = rank + rank_offset;
        const int target_file = file + file_offset;
        if (target_rank >= 0 && target_rank < 8 && target_file >= 0 && target_file < 8) {
            attacks |= Bitboard{1} << (target_rank * 8 + target_file);
        }
    }
    return attacks;
}

consteval std::array<Bitboard, 64> make_knight_attack_table() {
    constexpr std::array offsets = {
        std::pair{-2, -1}, std::pair{-2, 1}, std::pair{-1, -2}, std::pair{-1, 2},
        std::pair{1, -2}, std::pair{1, 2}, std::pair{2, -1}, std::pair{2, 1}
    };
    std::array<Bitboard, 64> table{};
    for (std::uint8_t square = 0; square < 64; ++square) {
        table[square] = jump_attacks_for(square, offsets);
    }
    return table;
}

consteval std::array<Bitboard, 64> make_king_attack_table() {
    constexpr std::array offsets = {
        std::pair{-1, -1}, std::pair{-1, 0}, std::pair{-1, 1}, std::pair{0, -1},
        std::pair{0, 1}, std::pair{1, -1}, std::pair{1, 0}, std::pair{1, 1}
    };
    std::array<Bitboard, 64> table{};
    for (std::uint8_t square = 0; square < 64; ++square) {
        table[square] = jump_attacks_for(square, offsets);
    }
    return table;
}

inline constexpr auto knight_attack_table = make_knight_attack_table();
inline constexpr auto king_attack_table = make_king_attack_table();

}

inline constexpr Bitboard knight_attacks(std::uint8_t square) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return detail::knight_attack_table[square];
}

inline constexpr Bitboard king_attacks(std::uint8_t square) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return detail::king_attack_table[square];
}

}
