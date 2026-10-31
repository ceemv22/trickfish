#pragma once

#include <cstdint>
#include <vector>

#include "trickfish/search.hpp"

namespace trickfish {

inline constexpr int maximum_multi_pv = 16;

struct MultiPVResult {
    std::vector<SearchResult> lines;
    int completed_depth = 0;
    bool stopped = false;
    std::uint64_t nodes = 0;
};

[[nodiscard]] MultiPVResult iterative_multi_pv(Position& position, int max_depth, int count,
    const SearchOptions& options = {}, const SearchLimits& limits = {}, const RepetitionHistory* history = nullptr);

}
