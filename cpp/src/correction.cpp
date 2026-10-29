#include "trickfish/correction.hpp"

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/zobrist.hpp"

namespace trickfish {
namespace {

std::uint64_t pawn_context_key(const Position& position) {
    std::uint64_t key = position.side_to_move() == Color::black ? zobrist::keys.side : 0;
    for (const auto color : {Color::white, Color::black}) {
        auto pawns = position.pieces(color, PieceType::pawn);
        while (pawns != 0) key ^= zobrist::keys.pieces[piece_index(color, PieceType::pawn)][pop_lsb(pawns)];
    }
    return key;
}

std::size_t correction_slot(std::uint64_t key) {
    return (key ^ (key >> 32)) & 1023U;
}

}

int CorrectionHistory::adjustment(const Position& position) const {
    if (entries_.empty()) return 0;
    const auto key = pawn_context_key(position);
    const auto& entry = entries_[correction_slot(key)];
    return entry.occupied && entry.key == key ? entry.value : 0;
}

bool CorrectionHistory::update(const Position& position, int target, int raw, int depth) {
    if (depth < 1 || depth > 64) throw std::invalid_argument("correction depth must be between 1 and 64");
    constexpr int ordinary_limit = mate_score - 128;
    if (target <= -ordinary_limit || target >= ordinary_limit || raw <= -ordinary_limit || raw >= ordinary_limit) return false;
    const auto error = static_cast<int>(std::clamp<std::int64_t>(static_cast<std::int64_t>(target) - raw, -256, 256));
    if (entries_.empty()) entries_.resize(1024);
    const auto key = pawn_context_key(position);
    auto& entry = entries_[correction_slot(key)];
    if (!entry.occupied || entry.key != key) entry = {key, 0, true};
    const int weight = std::min(depth, 16);
    entry.value = (entry.value * (32 - weight) + error * weight) / 32;
    entry.value = std::clamp(entry.value, -256, 256);
    return true;
}

void CorrectionHistory::clear() { entries_.clear(); }

}
