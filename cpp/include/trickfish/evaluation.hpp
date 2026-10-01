#pragma once

#include <array>
#include <bit>
#include <cstddef>

#include "trickfish/game_status.hpp"
#include "trickfish/position.hpp"

namespace trickfish {

inline constexpr int mate_score = 100000;
inline constexpr std::array piece_values = {100, 320, 330, 500, 900, 0};

[[nodiscard]] inline int evaluate_material(const Position& position) {
    int score = 0;
    for (std::size_t type = 0; type < piece_values.size(); ++type) {
        const auto piece = static_cast<PieceType>(type);
        score += piece_values[type] * (std::popcount(position.pieces(Color::white, piece)) -
            std::popcount(position.pieces(Color::black, piece)));
    }
    return score;
}

[[nodiscard]] inline int evaluate(Position& position) {
    const auto status = game_status(position);
    if (status == GameStatus::checkmate) {
        return position.side_to_move() == Color::white ? -mate_score : mate_score;
    }
    if (status == GameStatus::stalemate || position.is_insufficient_material()) {
        return 0;
    }
    return evaluate_material(position);
}

[[nodiscard]] inline int evaluate_for_side_to_move(Position& position) {
    const auto score = evaluate(position);
    return position.side_to_move() == Color::white ? score : -score;
}

}
