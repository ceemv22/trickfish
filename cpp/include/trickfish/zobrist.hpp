#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace trickfish {
namespace zobrist {

consteval std::uint64_t splitmix64(std::uint64_t& state) {
    state += 0x9e3779b97f4a7c15ULL;
    auto value = state;
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

struct Keys {
    std::array<std::array<std::uint64_t, 64>, 12> pieces{};
    std::uint64_t side = 0;
    std::array<std::uint64_t, 16> castling{};
    std::array<std::uint64_t, 8> en_passant_file{};
};

consteval Keys make_keys() {
    Keys keys;
    std::uint64_t state = 0x747269636b666973ULL;
    for (auto& piece : keys.pieces) {
        for (auto& square : piece) {
            square = splitmix64(state);
        }
    }
    keys.side = splitmix64(state);
    for (auto& castling : keys.castling) {
        castling = splitmix64(state);
    }
    for (auto& file : keys.en_passant_file) {
        file = splitmix64(state);
    }
    return keys;
}

inline constexpr auto keys = make_keys();

}
}
