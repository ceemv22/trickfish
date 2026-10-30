#pragma once

#include <algorithm>
#include <cstdint>

#include "trickfish/piece.hpp"

namespace trickfish {

inline constexpr int additive_piece_activity(Color color, PieceType type, std::uint8_t square) {
    const int rank = square / 8;
    const int file = square % 8;
    if (type == PieceType::pawn) {
        const int advance = color == Color::white ? 6 - rank : rank - 1;
        return 5 * advance + (file == 3 || file == 4 ? 6 : 0);
    }
    const int file_offset = 2 * file - 7;
    const int rank_offset = 2 * rank - 7;
    const int distance = (file_offset < 0 ? -file_offset : file_offset) + (rank_offset < 0 ? -rank_offset : rank_offset);
    if (type == PieceType::knight) return std::max(0, 28 - 2 * distance);
    if (type == PieceType::bishop) return std::max(0, 16 - distance);
    return 0;
}

}
