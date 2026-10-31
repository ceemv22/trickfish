#pragma once

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>

#include "trickfish/bitboard.hpp"
#include "trickfish/piece.hpp"

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

template<std::size_t Size>
constexpr Bitboard sliding_attacks_for(
    std::uint8_t square,
    Bitboard occupancy,
    const std::array<std::pair<int, int>, Size>& directions
) {
    const int rank = square / 8;
    const int file = square % 8;
    Bitboard attacks = 0;
    for (const auto [rank_step, file_step] : directions) {
        int target_rank = rank + rank_step;
        int target_file = file + file_step;
        while (target_rank >= 0 && target_rank < 8 && target_file >= 0 && target_file < 8) {
            const auto target = static_cast<std::uint8_t>(target_rank * 8 + target_file);
            const auto target_bit = square_bit(target);
            attacks |= target_bit;
            if ((occupancy & target_bit) != 0) {
                break;
            }
            target_rank += rank_step;
            target_file += file_step;
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

consteval std::array<Bitboard, 64> make_pawn_attack_table(Color color) {
    std::array<Bitboard, 64> table{};
    const int rank_offset = color == Color::white ? -1 : 1;
    for (std::uint8_t square = 0; square < 64; ++square) {
        const int rank = square / 8;
        const int file = square % 8;
        const int target_rank = rank + rank_offset;
        if (target_rank < 0 || target_rank >= 8) {
            continue;
        }
        if (file > 0) {
            table[square] |= Bitboard{1} << (target_rank * 8 + file - 1);
        }
        if (file < 7) {
            table[square] |= Bitboard{1} << (target_rank * 8 + file + 1);
        }
    }
    return table;
}

inline constexpr auto knight_attack_table = make_knight_attack_table();
inline constexpr auto king_attack_table = make_king_attack_table();
inline constexpr auto white_pawn_attack_table = make_pawn_attack_table(Color::white);
inline constexpr auto black_pawn_attack_table = make_pawn_attack_table(Color::black);
inline constexpr std::array bishop_directions = {
    std::pair{-1, -1}, std::pair{-1, 1}, std::pair{1, -1}, std::pair{1, 1}
};
inline constexpr std::array rook_directions = {
    std::pair{-1, 0}, std::pair{1, 0}, std::pair{0, -1}, std::pair{0, 1}
};

template<std::size_t Size>
consteval auto make_sliding_rays(const std::array<std::pair<int, int>, Size>& directions) {
    std::array<std::array<Bitboard, 64>, Size> rays{};
    for (std::size_t direction = 0; direction < Size; ++direction) {
        for (std::uint8_t square = 0; square < 64; ++square) {
            const std::array single = {directions[direction]};
            rays[direction][square] = sliding_attacks_for(square, 0, single);
        }
    }
    return rays;
}

inline constexpr auto bishop_rays = make_sliding_rays(bishop_directions);
inline constexpr auto rook_rays = make_sliding_rays(rook_directions);

template<std::size_t Size>
consteval std::array<Bitboard, 64> make_alignment_masks(const std::array<std::array<Bitboard, 64>, Size>& rays) {
    std::array<Bitboard, 64> masks{};
    for (std::size_t square = 0; square < masks.size(); ++square) {
        for (const auto& ray : rays) masks[square] |= ray[square];
    }
    return masks;
}

inline constexpr auto bishop_alignment = make_alignment_masks(bishop_rays);
inline constexpr auto rook_alignment = make_alignment_masks(rook_rays);

template<std::size_t Size>
constexpr Bitboard ray_attacks_for(std::uint8_t square, Bitboard occupancy,
    const std::array<std::pair<int, int>, Size>& directions,
    const std::array<std::array<Bitboard, 64>, Size>& rays) {
    Bitboard attacks = 0;
    for (std::size_t direction = 0; direction < Size; ++direction) {
        const auto ray = rays[direction][square];
        const auto blockers = ray & occupancy;
        if (blockers == 0) {
            attacks |= ray;
        } else {
            const auto [rank_step, file_step] = directions[direction];
            const auto blocker = static_cast<std::uint8_t>(rank_step * 8 + file_step > 0
                ? std::countr_zero(blockers) : 63 - std::countl_zero(blockers));
            attacks |= ray ^ rays[direction][blocker];
        }
    }
    return attacks;
}

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

inline constexpr Bitboard pawn_attacks(Color color, std::uint8_t square) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return color == Color::white
        ? detail::white_pawn_attack_table[square]
        : detail::black_pawn_attack_table[square];
}

inline constexpr Bitboard bishop_attacks_reference(std::uint8_t square, Bitboard occupancy) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return detail::sliding_attacks_for(square, occupancy, detail::bishop_directions);
}

inline constexpr Bitboard rook_attacks_reference(std::uint8_t square, Bitboard occupancy) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    return detail::sliding_attacks_for(square, occupancy, detail::rook_directions);
}

inline constexpr Bitboard bishop_attacks_ray(std::uint8_t square, Bitboard occupancy) {
    if (square >= 64) throw std::invalid_argument("square must be between 0 and 63");
    return detail::ray_attacks_for(square, occupancy, detail::bishop_directions, detail::bishop_rays);
}

inline constexpr Bitboard rook_attacks_ray(std::uint8_t square, Bitboard occupancy) {
    if (square >= 64) throw std::invalid_argument("square must be between 0 and 63");
    return detail::ray_attacks_for(square, occupancy, detail::rook_directions, detail::rook_rays);
}

#ifdef TRICKFISH_RAY_SLIDERS
inline constexpr bool use_ray_sliders = true;
#else
inline constexpr bool use_ray_sliders = false;
#endif

inline constexpr Bitboard bishop_attacks(std::uint8_t square, Bitboard occupancy) {
    if constexpr (use_ray_sliders) return bishop_attacks_ray(square, occupancy);
    else return bishop_attacks_reference(square, occupancy);
}

inline constexpr Bitboard rook_attacks(std::uint8_t square, Bitboard occupancy) {
    if constexpr (use_ray_sliders) return rook_attacks_ray(square, occupancy);
    else return rook_attacks_reference(square, occupancy);
}

inline constexpr Bitboard queen_attacks(std::uint8_t square, Bitboard occupancy) {
    return bishop_attacks(square, occupancy) | rook_attacks(square, occupancy);
}

}
