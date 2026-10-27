#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "trickfish/position.hpp"

namespace trickfish {

class RepetitionHistory {
public:
    explicit RepetitionHistory(const Position& initial) : keys_{initial.key()} {}

    void push(const Position& position) { keys_.push_back(position.key()); }

    void pop() {
        if (keys_.size() == 1) {
            throw std::underflow_error("cannot remove the initial repetition position");
        }
        keys_.pop_back();
    }

    [[nodiscard]] std::size_t size() const { return keys_.size(); }
    [[nodiscard]] std::uint64_t current_key() const { return keys_.back(); }

    [[nodiscard]] std::size_t current_count() const {
        return static_cast<std::size_t>(std::count(keys_.begin(), keys_.end(), keys_.back()));
    }

    [[nodiscard]] bool can_claim_threefold_repetition() const { return current_count() >= 3; }

private:
    std::vector<std::uint64_t> keys_;
};

}
