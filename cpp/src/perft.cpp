#include "trickfish/perft.hpp"

#include <stdexcept>

#include "trickfish/movegen.hpp"

namespace trickfish {

std::uint64_t perft(Position& position, int depth) {
    if (depth < 0) {
        throw std::invalid_argument("perft depth must not be negative");
    }
    if (depth == 0) {
        return 1;
    }

    const auto moves = generate_legal_moves(position);
    if (depth == 1) {
        return moves.size();
    }

    std::uint64_t nodes = 0;
    for (const auto& move : moves) {
        const auto undo = position.make_move(move);
        nodes += perft(position, depth - 1);
        position.unmake_move(move, undo);
    }
    return nodes;
}

}
