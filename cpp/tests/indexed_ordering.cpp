#include <algorithm>
#include <array>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <tuple>
#include <vector>

#include "trickfish/ordering.hpp"

using trickfish::Move;
using trickfish::MoveList;
using trickfish::detail::CachedMoveKey;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

MoveList fixture(std::size_t size) {
    MoveList moves;
    constexpr std::array<char, 5> promotions{'\0', 'b', 'n', 'q', 'r'};
    for (std::size_t index = 0; index < size; ++index) {
        moves.push(Move{static_cast<std::uint8_t>(index / 4),
            static_cast<std::uint8_t>((index / 4 + 1 + index % 4) % 64),
            promotions[index % promotions.size()], index % 3 == 0, index % 7 == 0});
    }
    return moves;
}

void permutation(const std::vector<std::uint16_t>& sources) {
    auto moves = fixture(sources.size());
    const auto original = moves;
    std::array<CachedMoveKey, MoveList::capacity> keys;
    for (std::size_t index = 0; index < sources.size(); ++index) {
        keys[index] = {0, 0, 0, 0, sources[index], false, false};
    }
    trickfish::detail::apply_cached_move_order(moves, std::span{keys}.first(sources.size()));
    require(moves.size() == original.size(), "permutation changed list size");
    for (std::size_t index = 0; index < sources.size(); ++index) {
        require(moves[index] == original[sources[index]], "permutation lost or altered a move");
        require(keys[index].source == index, "permutation did not consume cycle");
    }
}

void comparator() {
    std::mt19937 random(20261031);
    for (const bool exchange : {false, true}) {
        for (int round = 0; round < 128; ++round) {
            auto moves = fixture(round % 2 == 0 ? MoveList::capacity : random() % MoveList::capacity);
            const auto original = moves;
            std::array<CachedMoveKey, MoveList::capacity> keys;
            for (std::size_t index = 0; index < moves.size(); ++index) {
                keys[index] = {trickfish::detail::move_order_tie(moves[index]),
                    static_cast<int>(random() % 9) - 4, static_cast<int>(random() % 9) - 4,
                    static_cast<int>(random() % 9) - 4, static_cast<std::uint16_t>(index),
                    random() % 4 == 0, random() % 2 == 0};
            }
            std::array<CachedMoveKey, MoveList::capacity> expected;
            std::copy_n(keys.begin(), moves.size(), expected.begin());
            const auto reference_less = [&original, exchange](const auto& left, const auto& right) {
                const auto& a = original[left.source];
                const auto& b = original[right.source];
                return std::tuple{!left.preferred, exchange && !left.tactical,
                    exchange && left.tactical ? -left.exchange : 0, -left.priority, -left.history,
                    a.from, a.to, a.promotion} <
                    std::tuple{!right.preferred, exchange && !right.tactical,
                    exchange && right.tactical ? -right.exchange : 0, -right.priority, -right.history,
                    b.from, b.to, b.promotion};
            };
            std::sort(expected.begin(), expected.begin() + moves.size(), reference_less);
            std::sort(keys.begin(), keys.begin() + moves.size(), [exchange](const auto& a, const auto& b) {
                return trickfish::detail::cached_move_less(a, b, exchange);
            });
            trickfish::detail::apply_cached_move_order(moves, std::span{keys}.first(moves.size()));
            for (std::size_t index = 0; index < moves.size(); ++index) {
                require(moves[index] == original[expected[index].source], "encoded comparator changed move order");
            }
        }
    }
    for (const char left : {'\0', 'b', 'n', 'q', 'r'}) {
        for (const char right : {'\0', 'b', 'n', 'q', 'r'}) {
            const Move a{48, 56, left};
            const Move b{48, 56, right};
            require((trickfish::detail::move_order_tie(a) < trickfish::detail::move_order_tie(b)) ==
                (left < right), "promotion tie order changed");
        }
    }
}

int main() {
    try {
        for (std::size_t size = 0; size <= 8; ++size) {
            std::vector<std::uint16_t> sources(size);
            std::iota(sources.begin(), sources.end(), std::uint16_t{0});
            do { permutation(sources); } while (std::next_permutation(sources.begin(), sources.end()));
        }
        std::vector<std::uint16_t> sources(MoveList::capacity);
        std::iota(sources.begin(), sources.end(), std::uint16_t{0});
        permutation(sources);
        std::reverse(sources.begin(), sources.end());
        permutation(sources);
        std::iota(sources.begin(), sources.end(), std::uint16_t{0});
        std::rotate(sources.begin(), sources.begin() + 1, sources.end());
        permutation(sources);
        comparator();
        std::cout << "indexed ordering checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
