#include "trickfish/pawn_cache.hpp"

#include <stdexcept>

#include "trickfish/evaluation.hpp"

namespace trickfish {

PawnEvaluationCache::PawnEvaluationCache(std::size_t capacity) : capacity_(capacity) {
    if (capacity == 0) throw std::invalid_argument("pawn cache capacity must be positive");
}

int PawnEvaluationCache::evaluate(const Position& position) {
    if (entries_.empty()) entries_.resize(capacity_);
    const auto key = position.pawn_key();
    const int phase = game_phase(position);
    const auto index = (key ^ (static_cast<std::uint64_t>(phase) * 0x9e3779b97f4a7c15ULL)) % capacity_;
    auto& entry = entries_[index];
    if (entry.phase == phase && entry.key == key) {
        ++hits_;
    } else {
        ++misses_;
        entry = {key, phase, detail::pawn_structure_total(position, phase)};
    }
    return detail::breakdown_with_pawns(position, phase, entry.score).total();
}

void PawnEvaluationCache::clear() {
    entries_.clear();
    hits_ = 0;
    misses_ = 0;
}

}
