#pragma once

#include <algorithm>
#include <cstdint>
#include <optional>
#include <stdexcept>

#include "trickfish/piece.hpp"

namespace trickfish {

inline constexpr std::uint64_t default_move_overhead_ms = 10;

struct ClockControl {
    std::optional<std::uint64_t> white_time;
    std::optional<std::uint64_t> black_time;
    std::uint64_t white_increment = 0;
    std::uint64_t black_increment = 0;
    std::optional<std::uint64_t> moves_to_go;
};

[[nodiscard]] inline std::optional<std::uint64_t> allocate_clock_time(Color side, const ClockControl& clock,
    std::uint64_t overhead = default_move_overhead_ms) {
    if (clock.moves_to_go && *clock.moves_to_go == 0) {
        throw std::invalid_argument("movestogo must be positive");
    }
    const auto remaining = side == Color::white ? clock.white_time : clock.black_time;
    if (!remaining) return std::nullopt;
    const auto increment = side == Color::white ? clock.white_increment : clock.black_increment;
    const auto reserve = std::min(*remaining, std::max(overhead, *remaining / 20));
    const auto available = *remaining - reserve;
    if (available == 0) return 0;
    const auto base = std::min(available, *remaining / clock.moves_to_go.value_or(30));
    const auto added = std::min(available - base, increment / 2);
    return std::max(std::uint64_t{1}, base + added);
}

}
