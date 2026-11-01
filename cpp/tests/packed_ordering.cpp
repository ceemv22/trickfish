#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>

#include "trickfish/packed_ordering.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

struct Rank {
    Move move;
    bool preferred;
    bool tactical;
    int exchange;
    int priority;
    int history;
};

bool before(const Rank& left, const Rank& right, bool exchange) {
    if (left.preferred != right.preferred) return left.preferred;
    if (exchange) {
        if (left.tactical != right.tactical) return left.tactical;
        if (left.tactical && left.exchange != right.exchange) return left.exchange > right.exchange;
    }
    if (left.priority != right.priority) return left.priority > right.priority;
    if (left.history != right.history) return left.history > right.history;
    if (left.move.from != right.move.from) return left.move.from < right.move.from;
    if (left.move.to != right.move.to) return left.move.to < right.move.to;
    return left.move.promotion < right.move.promotion;
}

void permutation(const std::vector<unsigned>& order) {
    MoveList moves;
    std::array<PackedMoveKey, MoveList::capacity> keys;
    for (std::size_t index = 0; index < order.size(); ++index) {
        const auto source = order[index];
        const Move move(static_cast<std::uint8_t>(source % 64), static_cast<std::uint8_t>((source % 64 + source / 64 + 1) % 64),
            source % 2 ? 'n' : '\0', source % 3 == 0, source % 5 == 0);
        moves.push(move);
        keys[index] = packed_move_key(move, index, false, false, false, 0, -static_cast<int>(source), 0);
    }
    auto expected = moves;
    std::sort(expected.begin(), expected.end(), [&order](const Move& a, const Move& b) {
        const auto source = [&order](const Move& move) {
            return *std::find_if(order.begin(), order.end(), [&move](unsigned value) {
                return value % 64 == move.from && (value % 64 + value / 64 + 1) % 64 == move.to;
            });
        };
        return source(a) < source(b);
    });
    apply_packed_order(moves, keys);
    require(std::equal(moves.begin(), moves.end(), expected.begin(), expected.end()), "cycle permutation lost a Move field");
}

int main() {
    try {
        for (unsigned size = 0; size <= 8; ++size) {
            std::vector<unsigned> order;
            for (unsigned i = 0; i < size; ++i) order.push_back(i);
            do { permutation(order); } while (std::next_permutation(order.begin(), order.end()));
        }
        std::mt19937 random(20261101);
        std::vector<unsigned> full;
        for (unsigned i = 0; i < 256; ++i) full.push_back(i);
        for (int repeat = 0; repeat < 20; ++repeat) {
            std::shuffle(full.begin(), full.end(), random);
            permutation(full);
        }
        std::vector<Rank> ranks;
        constexpr std::array edge = {std::numeric_limits<int>::min(), -32768, -1, 0, 1, 32768, std::numeric_limits<int>::max()};
        for (std::size_t i = 0; i < 512; ++i) {
            ranks.push_back({Move(static_cast<std::uint8_t>(i % 64), static_cast<std::uint8_t>((i % 64 + 1) % 64), i % 3 ? 'q' : '\0'),
                i % 5 == 0, i % 7 == 0, edge[i % edge.size()], edge[(i / 7) % edge.size()], edge[(i / 49) % edge.size()]});
        }
        for (bool exchange : {false, true}) {
            for (const auto& left : ranks) for (const auto& right : ranks) {
                const auto a = packed_move_key(left.move, 0, left.preferred, exchange, left.tactical, left.exchange, left.priority, left.history);
                const auto b = packed_move_key(right.move, 255, right.preferred, exchange, right.tactical, right.exchange, right.priority, right.history);
                require(packed_before(a, b) == before(left, right, exchange), "packed comparator changed signed or tie ordering");
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
