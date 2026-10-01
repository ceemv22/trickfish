#pragma once

#include <cstdint>
#include <optional>

#include "trickfish/position.hpp"

namespace trickfish {

struct SearchResult {
    std::optional<Move> best_move;
    int score = 0;
    std::uint64_t nodes = 0;
};

[[nodiscard]] SearchResult search(Position& position, int depth);

}
