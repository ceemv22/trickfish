#include "trickfish/exchange.hpp"

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

int material_gain(const Position& position, const Move& move) {
    const auto captured = position.piece_at(move.to);
    int gain = move.en_passant ? piece_values[static_cast<std::size_t>(PieceType::pawn)] :
        captured == '.' ? 0 : piece_values[static_cast<std::size_t>(piece_type_from_symbol(captured))];
    if (move.promotion != '\0') {
        gain += piece_values[static_cast<std::size_t>(piece_type_from_symbol(move.promotion))] -
            piece_values[static_cast<std::size_t>(PieceType::pawn)];
    }
    return gain;
}

int recapture_gain(const Position& position, std::uint8_t target) {
    auto current = position;
    const auto legal = generate_legal_moves(current);
    int best = 0;
    for (const auto& move : legal) {
        if (move.to != target || current.piece_at(target) == '.') continue;
        const int gain = material_gain(current, move);
        auto child = current;
        const auto undo = child.make_move(move);
        static_cast<void>(undo);
        best = std::max(best, gain - recapture_gain(child, target));
    }
    return best;
}

}

int static_exchange(const Position& position, const Move& move) {
    auto current = position;
    const auto legal = generate_legal_moves(current);
    if (std::find(legal.begin(), legal.end(), move) == legal.end()) {
        throw std::invalid_argument("exchange move must be legal");
    }
    if (current.piece_at(move.to) == '.' && !move.en_passant && move.promotion == '\0') {
        throw std::invalid_argument("exchange move must capture or promote");
    }
    const int gain = material_gain(current, move);
    const auto undo = current.make_move(move);
    static_cast<void>(undo);
    return gain - recapture_gain(current, move.to);
}

}
