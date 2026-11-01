#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "trickfish/position.hpp"

namespace trickfish {

class RepetitionHistory {
public:
    explicit RepetitionHistory(const Position& initial) : keys_{initial.key()}, counts_{{initial.key(), 1}} {}

    void push(const Position& position) {
        keys_.push_back(position.key());
        try {
            ++counts_[position.key()];
        } catch (...) {
            keys_.pop_back();
            throw;
        }
    }

    void pop() {
        if (keys_.size() == 1) {
            throw std::underflow_error("cannot remove the initial repetition position");
        }
        const auto entry = counts_.find(keys_.back());
        if (--entry->second == 0) counts_.erase(entry);
        keys_.pop_back();
    }

    [[nodiscard]] std::size_t size() const { return keys_.size(); }
    [[nodiscard]] std::uint64_t current_key() const { return keys_.back(); }

    [[nodiscard]] std::size_t current_count() const {
        return counts_.at(keys_.back());
    }

    [[nodiscard]] bool can_claim_threefold_repetition() const { return current_count() >= 3; }

private:
    std::vector<std::uint64_t> keys_;
    std::unordered_map<std::uint64_t, std::size_t> counts_;
};

}
