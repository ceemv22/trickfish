#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>
#include <string_view>

namespace trickfish {

inline std::uint8_t square_from_name(std::string_view name) {
    if (name.size() != 2 || name[0] < 'a' || name[0] > 'h' || name[1] < '1' || name[1] > '8') {
        throw std::invalid_argument("invalid square name");
    }
    const auto file = static_cast<std::uint8_t>(name[0] - 'a');
    const auto rank = static_cast<std::uint8_t>(8 - (name[1] - '0'));
    return static_cast<std::uint8_t>(rank * 8 + file);
}

inline std::string square_name(std::uint8_t square) {
    if (square >= 64) {
        throw std::invalid_argument("square must be between 0 and 63");
    }
    std::string name(2, ' ');
    name[0] = static_cast<char>('a' + square % 8);
    name[1] = static_cast<char>('8' - square / 8);
    return name;
}

}
