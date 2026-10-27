#pragma once

#include "trickfish/game_status.hpp"

namespace trickfish {

enum class MoveCountDraw {
    none,
    fifty_move_claim_available,
    automatic_seventy_five_move
};

[[nodiscard]] inline MoveCountDraw move_count_draw_status(Position& position) {
    if (position.halfmove_clock() < 100) {
        return MoveCountDraw::none;
    }
    const auto status = game_status(position);
    if (status == GameStatus::checkmate || status == GameStatus::stalemate || position.is_insufficient_material()) {
        return MoveCountDraw::none;
    }
    return position.halfmove_clock() >= 150
        ? MoveCountDraw::automatic_seventy_five_move
        : MoveCountDraw::fifty_move_claim_available;
}

}
