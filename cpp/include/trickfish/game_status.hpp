#pragma once

#include "trickfish/movegen.hpp"

namespace trickfish {

enum class GameStatus {
    ongoing,
    check,
    checkmate,
    stalemate
};

[[nodiscard]] inline GameStatus game_status(Position& position) {
    if (generate_legal_moves(position).size() != 0) {
        return position.in_check(position.side_to_move()) ? GameStatus::check : GameStatus::ongoing;
    }
    return position.in_check(position.side_to_move()) ? GameStatus::checkmate : GameStatus::stalemate;
}

}
