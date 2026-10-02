#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "trickfish/position.hpp"
#include "trickfish/transposition.hpp"

namespace trickfish {

struct SearchResult {
    std::optional<Move> best_move;
    std::vector<Move> principal_variation;
    int score = 0;
    int completed_depth = 0;
    bool stopped = false;
    std::uint64_t nodes = 0;
    std::uint64_t transposition_hits = 0;
};

[[nodiscard]] SearchResult search(Position& position, int depth, bool use_table = true);
[[nodiscard]] SearchResult iterative_search(Position& position, int max_depth, bool use_table = true,
    std::optional<std::uint64_t> node_limit = std::nullopt);
[[nodiscard]] SearchResult search(Position& position, int depth, TranspositionTable& table);

}
