#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <type_traits>

#include "trickfish/move_list.hpp"

namespace trickfish {

struct PackedMoveKey { std::uint64_t major; std::uint64_t minor; };
static_assert(std::is_trivially_default_constructible_v<PackedMoveKey>);
static_assert(sizeof(PackedMoveKey) == 16);

[[nodiscard]] constexpr PackedMoveKey packed_move_key(const Move& move, std::size_t source, bool preferred,
    bool exchange_ordering, bool tactical, int exchange, int priority, int history) {
    const auto biased = [](int value) { return static_cast<std::uint32_t>(value) ^ 0x80000000U; };
    const auto coordinate = (static_cast<std::uint32_t>(move.from) << 13) |
        (static_cast<std::uint32_t>(move.to) << 7) | static_cast<unsigned char>(move.promotion);
    const auto p = biased(priority);
    return {(static_cast<std::uint64_t>(preferred) << 63) |
            (static_cast<std::uint64_t>(exchange_ordering && tactical) << 62) |
            (static_cast<std::uint64_t>(exchange_ordering && tactical ? biased(exchange) : 0) << 30) | (p >> 2),
        (static_cast<std::uint64_t>(p & 3) << 62) | (static_cast<std::uint64_t>(biased(history)) << 30) |
            (static_cast<std::uint64_t>(0x7ffffU - coordinate) << 8) | source};
}

[[nodiscard]] constexpr bool packed_before(const PackedMoveKey& left, const PackedMoveKey& right) {
    return left.major != right.major ? left.major > right.major : (left.minor >> 8) > (right.minor >> 8);
}

inline void apply_packed_order(MoveList& moves, std::array<PackedMoveKey, MoveList::capacity>& keys) {
    std::sort(keys.begin(), keys.begin() + moves.size(), packed_before);
    for (std::size_t index = 0; index < moves.size(); ++index) {
        if ((keys[index].minor & 255) == index) continue;
        const Move saved = moves[index];
        auto current = index;
        while ((keys[current].minor & 255) != index) {
            const auto next = static_cast<std::size_t>(keys[current].minor & 255);
            moves[current] = moves[next];
            keys[current].minor = (keys[current].minor & ~255ULL) | current;
            current = next;
        }
        moves[current] = saved;
        keys[current].minor = (keys[current].minor & ~255ULL) | current;
    }
}

}
