#pragma once

#include <cassert>
#include <cstdint>
#include <limits>
#include <span>
#include <type_traits>

#include "trickfish/move_list.hpp"

namespace trickfish::detail {

struct CachedMoveKey {
    std::uint32_t tie;
    int priority;
    int history;
    int exchange;
    std::uint16_t source;
    bool preferred;
    bool tactical;
};

static_assert(std::is_trivially_default_constructible_v<CachedMoveKey>);
static_assert(std::is_trivially_copyable_v<CachedMoveKey>);
static_assert(MoveList::capacity - 1 <= std::numeric_limits<std::uint16_t>::max());

[[nodiscard]] constexpr std::uint32_t move_order_tie(const Move& move) {
    return (std::uint32_t{move.from} << 16) | (std::uint32_t{move.to} << 8) |
        static_cast<unsigned char>(move.promotion);
}

[[nodiscard]] constexpr bool cached_move_less(const CachedMoveKey& left, const CachedMoveKey& right,
    bool exchange_ordering) {
    if (left.preferred != right.preferred) return left.preferred;
    if (exchange_ordering) {
        if (left.tactical != right.tactical) return left.tactical;
        if (left.tactical && left.exchange != right.exchange) return left.exchange > right.exchange;
    }
    if (left.priority != right.priority) return left.priority > right.priority;
    if (left.history != right.history) return left.history > right.history;
    return left.tie < right.tie;
}

inline void apply_cached_move_order(MoveList& moves, std::span<CachedMoveKey> keys) {
    assert(keys.size() == moves.size());
    for (std::size_t index = 0; index < keys.size(); ++index) {
        if (keys[index].source == index) continue;
        const Move saved = moves[index];
        auto current = index;
        while (keys[current].source != index) {
            const auto source = keys[current].source;
            assert(source < keys.size());
            moves[current] = moves[source];
            keys[current].source = static_cast<std::uint16_t>(current);
            current = source;
        }
        moves[current] = saved;
        keys[current].source = static_cast<std::uint16_t>(current);
    }
}

}
