#include "trickfish/exchange.hpp"

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/attacks.hpp"
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

MoveList legal_recaptures(Position& position, std::uint8_t target) {
    MoveList moves;
    const auto victim = position.piece_at(target);
    const auto color = position.side_to_move();
    if (victim == '.' || color_from_symbol(victim) == color || piece_type_from_symbol(victim) == PieceType::king) return moves;
    const auto occupied = position.occupancy();
    auto attackers = pawn_attacks(opposite(color), target) & position.pieces(color, PieceType::pawn);
    attackers |= knight_attacks(target) & position.pieces(color, PieceType::knight);
    attackers |= king_attacks(target) & position.pieces(color, PieceType::king);
    attackers |= bishop_attacks(target, occupied) &
        (position.pieces(color, PieceType::bishop) | position.pieces(color, PieceType::queen));
    attackers |= rook_attacks(target, occupied) &
        (position.pieces(color, PieceType::rook) | position.pieces(color, PieceType::queen));
    const auto append = [&](const Move& move) {
        const auto undo = position.make_move(move);
        const bool legal = !position.in_check(color);
        position.unmake_move(move, undo);
        if (legal) moves.push(move);
    };
    while (attackers != 0) {
        const auto from = pop_lsb(attackers);
        const bool promotes = piece_type_from_symbol(position.piece_at(from)) == PieceType::pawn &&
            target / 8 == (color == Color::white ? 0 : 7);
        if (promotes) {
            for (char promotion : {'q', 'r', 'b', 'n'}) append(Move(from, target, promotion));
        } else {
            append(Move(from, target));
        }
    }
    return moves;
}

int recapture_gain(const Position& position, std::uint8_t target, bool targeted,
    int alpha, int beta, ExchangeResult& result) {
    ++result.nodes;
    if (targeted && beta <= 0) {
        ++result.cutoffs;
        return 0;
    }
    alpha = std::max(alpha, 0);
    auto current = position;
    const auto legal = targeted ? legal_recaptures(current, target) : generate_legal_moves(current);
    int best = 0;
    for (const auto& move : legal) {
        if (move.to != target || current.piece_at(target) == '.') continue;
        const int gain = material_gain(current, move);
        if (targeted && gain <= best) {
            ++result.cutoffs;
            continue;
        }
        auto child = current;
        const auto undo = child.make_move(move);
        static_cast<void>(undo);
        best = std::max(best, gain - recapture_gain(child, target, targeted,
            gain - beta, gain - alpha, result));
        if (targeted && best >= beta) {
            ++result.cutoffs;
            break;
        }
        alpha = std::max(alpha, best);
    }
    return best;
}

ExchangeResult exchange_impl(const Position& position, const Move& move, bool targeted) {
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
    ExchangeResult result;
    result.score = gain - recapture_gain(current, move.to, targeted, -1000000, 1000000, result);
    return result;
}

}

ExchangeResult analyze_exchange(const Position& position, const Move& move, bool reference) {
    return exchange_impl(position, move, !reference);
}

int static_exchange_reference(const Position& position, const Move& move) {
    return analyze_exchange(position, move, true).score;
}

int static_exchange(const Position& position, const Move& move) {
    return analyze_exchange(position, move).score;
}

}
