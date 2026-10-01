#pragma once

#include <array>
#include <bit>
#include <cstddef>

#include "trickfish/position.hpp"

namespace trickfish {

[[nodiscard]] inline int evaluate_material(const Position& position) {
    constexpr std::array values = {100, 320, 330, 500, 900, 0};
    int score = 0;
    for (std::size_t type = 0; type < values.size(); ++type) {
        const auto piece = static_cast<PieceType>(type);
        score += values[type] * (std::popcount(position.pieces(Color::white, piece)) -
            std::popcount(position.pieces(Color::black, piece)));
    }
    return score;
}

}
