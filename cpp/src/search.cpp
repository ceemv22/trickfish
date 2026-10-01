#include "trickfish/search.hpp"

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

int move_priority(const Position& position, const Move& move) {
    int priority = 0;
    const auto victim = position.piece_at(move.to);
    if (victim != '.' || move.en_passant) {
        const auto victim_type = move.en_passant ? PieceType::pawn : piece_type_from_symbol(victim);
        const auto attacker_type = piece_type_from_symbol(position.piece_at(move.from));
        priority = 10000 + 10 * piece_values[static_cast<std::size_t>(victim_type)] -
            piece_values[static_cast<std::size_t>(attacker_type)];
    }
    if (move.promotion != '\0') {
        priority += 10000 + piece_values[static_cast<std::size_t>(piece_type_from_symbol(move.promotion))];
    }
    return priority;
}

int negamax(Position& position, int depth, int ply, int alpha, int beta,
    std::uint64_t& nodes, std::optional<Move>* best_move) {
    ++nodes;
    auto moves = generate_legal_moves(position);
    if (moves.empty()) {
        return position.in_check(position.side_to_move()) ? -mate_score + ply : 0;
    }
    if (position.is_insufficient_material()) {
        if (best_move != nullptr) {
            *best_move = moves[0];
        }
        return 0;
    }
    if (depth == 0) {
        const auto score = evaluate_material(position);
        return position.side_to_move() == Color::white ? score : -score;
    }
    std::sort(moves.begin(), moves.end(), [&position](const Move& left, const Move& right) {
        const auto left_priority = move_priority(position, left);
        const auto right_priority = move_priority(position, right);
        if (left_priority != right_priority) {
            return left_priority > right_priority;
        }
        if (left.from != right.from) return left.from < right.from;
        if (left.to != right.to) return left.to < right.to;
        return left.promotion < right.promotion;
    });
    int best = -mate_score - 1;
    for (const auto& move : moves) {
        const auto undo = position.make_move(move);
        const int score = -negamax(position, depth - 1, ply + 1, -beta, -alpha, nodes, nullptr);
        position.unmake_move(move, undo);
        if (score > best) {
            best = score;
            if (best_move != nullptr) {
                *best_move = move;
            }
        }
        alpha = std::max(alpha, score);
        if (alpha >= beta) {
            break;
        }
    }
    return best;
}

}

SearchResult search(Position& position, int depth) {
    if (depth < 1 || depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    SearchResult result;
    result.score = negamax(position, depth, 0, -mate_score - 1, mate_score + 1,
        result.nodes, &result.best_move);
    return result;
}

}
