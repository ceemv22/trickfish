#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "trickfish/position.hpp"

namespace trickfish {

class PawnEvaluationCache {
public:
    explicit PawnEvaluationCache(std::size_t capacity = 4096);
    [[nodiscard]] int evaluate(const Position& position);
    [[nodiscard]] std::size_t capacity() const { return capacity_; }
    [[nodiscard]] std::uint64_t hits() const { return hits_; }
    [[nodiscard]] std::uint64_t misses() const { return misses_; }
    void clear();
private:
    struct Entry {
        std::uint64_t key = 0;
        int phase = -1;
        int score = 0;
    };
    std::size_t capacity_;
    std::vector<Entry> entries_;
    std::uint64_t hits_ = 0;
    std::uint64_t misses_ = 0;
};

}
