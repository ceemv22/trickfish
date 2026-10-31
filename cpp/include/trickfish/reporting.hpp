#pragma once

#include <chrono>
#include <cstdint>
#include <limits>

namespace trickfish {

struct SearchTiming {
    std::uint64_t milliseconds = 0;
    std::uint64_t nodes_per_second = 0;
};

[[nodiscard]] inline SearchTiming search_timing(std::uint64_t nodes, std::chrono::milliseconds elapsed) {
    if (elapsed.count() <= 0) return {};
    const auto milliseconds = static_cast<std::uint64_t>(elapsed.count());
    const long double rate = static_cast<long double>(nodes) * 1000.0L / static_cast<long double>(milliseconds);
    constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
    return {milliseconds, rate >= static_cast<long double>(maximum) ? maximum : static_cast<std::uint64_t>(rate)};
}

}
