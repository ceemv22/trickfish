#pragma once

#include "trickfish/position.hpp"

namespace trickfish {

struct ExchangeResult {
    int score = 0;
    std::uint64_t nodes = 0;
    std::uint64_t cutoffs = 0;
};

[[nodiscard]] ExchangeResult analyze_exchange(const Position& position, const Move& move, bool reference = false);

[[nodiscard]] int static_exchange_reference(const Position& position, const Move& move);

[[nodiscard]] int static_exchange(const Position& position, const Move& move);

}
