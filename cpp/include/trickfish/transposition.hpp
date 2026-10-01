#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <vector>

#include "trickfish/move.hpp"
#include "trickfish/evaluation.hpp"

namespace trickfish {

inline constexpr int mate_threshold = mate_score - 128;

[[nodiscard]] constexpr int score_to_table(int score, int ply) {
    if (score >= mate_threshold) return score + ply;
    if (score <= -mate_threshold) return score - ply;
    return score;
}

[[nodiscard]] constexpr int score_from_table(int score, int ply) {
    if (score >= mate_threshold) return score - ply;
    if (score <= -mate_threshold) return score + ply;
    return score;
}

enum class Bound {
    exact,
    lower,
    upper
};

struct TranspositionEntry {
    std::uint64_t key = 0;
    int depth = 0;
    int score = 0;
    Bound bound = Bound::exact;
    std::optional<Move> best_move;
};

class TranspositionTable {
public:
    explicit TranspositionTable(std::size_t capacity = 65536) : slots_(capacity) {
        if (capacity == 0) {
            throw std::invalid_argument("transposition table capacity must be positive");
        }
    }

    [[nodiscard]] std::size_t capacity() const { return slots_.size(); }

    [[nodiscard]] const TranspositionEntry* probe(std::uint64_t key) const {
        const auto& slot = slots_[key % slots_.size()];
        return slot && slot->key == key ? &*slot : nullptr;
    }

    void store(const TranspositionEntry& entry) {
        auto& slot = slots_[entry.key % slots_.size()];
        if (slot && slot->key == entry.key && slot->depth > entry.depth) {
            return;
        }
        slot = entry;
    }

    void clear() {
        for (auto& slot : slots_) {
            slot.reset();
        }
    }

private:
    std::vector<std::optional<TranspositionEntry>> slots_;
};

}
