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
    std::uint64_t killer_cutoffs = 0;
    std::uint64_t killer_moves_searched = 0;
    std::uint64_t history_rewards = 0;
    std::uint64_t history_penalties = 0;
    std::uint64_t history_moves_searched = 0;
    std::uint64_t exchange_evaluations = 0;
    std::uint64_t exchange_nodes = 0;
    std::uint64_t exchange_cutoffs = 0;
    std::uint64_t continuation_updates = 0;
    std::uint64_t continuation_moves_searched = 0;
};

struct SearchOptions {
    bool use_table = true;
    bool use_pvs = true;
    bool use_killers = true;
    int aspiration_window = 25;
    MoveCountDrawPolicy draw_policy = MoveCountDrawPolicy::automatic_only;
    bool use_history = true;
    bool use_exchange_ordering = false;
    bool use_continuation = true;
    std::vector<Move> root_moves;
};

struct SearchLimits {
    std::optional<std::uint64_t> nodes;
    std::optional<std::chrono::steady_clock::time_point> deadline;
    std::function<bool()> stop_requested;
};

[[nodiscard]] SearchResult iterative_search(Position& position, int max_depth,
    const SearchOptions& options, const SearchLimits& limits = {}, const RepetitionHistory* history = nullptr);

[[nodiscard]] SearchResult search(Position& position, int depth, bool use_table = true, bool use_pvs = true, bool use_killers = true);
[[nodiscard]] SearchResult iterative_search(Position& position, int max_depth, bool use_table = true,
    std::optional<std::uint64_t> node_limit = std::nullopt,
    std::optional<std::chrono::steady_clock::time_point> deadline = std::nullopt,
    std::function<bool()> stop_requested = {},
    const RepetitionHistory* history = nullptr,
    MoveCountDrawPolicy draw_policy = MoveCountDrawPolicy::automatic_only, bool use_pvs = true, int aspiration_window = 25, bool use_killers = true);
[[nodiscard]] SearchResult search(Position& position, int depth, TranspositionTable& table, bool use_pvs = true, bool use_killers = true);

}
