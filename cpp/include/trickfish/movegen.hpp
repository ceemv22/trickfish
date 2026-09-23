#pragma once

#include "trickfish/move_list.hpp"
#include "trickfish/position.hpp"

namespace trickfish {

[[nodiscard]] MoveList generate_non_pawn_pseudo_legal_moves(const Position& position);
[[nodiscard]] MoveList generate_pawn_pseudo_legal_moves(const Position& position);
[[nodiscard]] MoveList generate_pseudo_legal_moves(const Position& position);
[[nodiscard]] MoveList generate_legal_moves(Position& position);

}
