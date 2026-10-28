#pragma once

#include <cstdint>
#include <chrono>
#include <functional>
#include <optional>
#include <vector>

#include "trickfish/position.hpp"
#include "trickfish/history.hpp"
#include "trickfish/draw.hpp"
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
    std::uint64_t pvs_probes = 0;
    std::uint64_t pvs_researches = 0;
    std::uint64_t aspiration_fail_low = 0;
    std::uint64_t aspiration_fail_high = 0;
};

[[nodiscard]] SearchResult search(Position& position, int depth, bool use_table = true, bool use_pvs = true);
[[nodiscard]] SearchResult iterative_search(Position& position, int max_depth, bool use_table = true,
    std::optional<std::uint64_t> node_limit = std::nullopt,
    std::optional<std::chrono::steady_clock::time_point> deadline = std::nullopt,
    std::function<bool()> stop_requested = {},
    const RepetitionHistory* history = nullptr,
    MoveCountDrawPolicy draw_policy = MoveCountDrawPolicy::automatic_only, bool use_pvs = true, int aspiration_window = 25);
[[nodiscard]] SearchResult search(Position& position, int depth, TranspositionTable& table, bool use_pvs = true);

}
