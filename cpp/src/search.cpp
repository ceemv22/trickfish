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

void order_moves(const Position& position, MoveList& moves, std::optional<Move> preferred = std::nullopt) {
    std::sort(moves.begin(), moves.end(), [&position, preferred](const Move& left, const Move& right) {
        if ((left == preferred) != (right == preferred)) return left == preferred;
        const auto left_priority = move_priority(position, left);
        const auto right_priority = move_priority(position, right);
        if (left_priority != right_priority) {
            return left_priority > right_priority;
        }
        if (left.from != right.from) return left.from < right.from;
        if (left.to != right.to) return left.to < right.to;
        return left.promotion < right.promotion;
    });
}

int material_for_side(const Position& position) {
    const auto score = evaluate_material(position);
    return position.side_to_move() == Color::white ? score : -score;
}

int quiescence(Position& position, int ply, int qdepth, int alpha, int beta, std::uint64_t& nodes) {
    ++nodes;
    auto moves = generate_legal_moves(position);
    const bool in_check = position.in_check(position.side_to_move());
    if (moves.empty()) {
        return in_check ? -mate_score + ply : 0;
    }
    if (position.is_insufficient_material()) {
        return 0;
    }
    if (qdepth >= 32) {
        return material_for_side(position);
    }
    int best = -mate_score - 1;
    if (!in_check) {
        best = material_for_side(position);
        if (best >= beta) {
            return best;
        }
        alpha = std::max(alpha, best);
    }
    order_moves(position, moves);
    for (const auto& move : moves) {
        if (!in_check && position.piece_at(move.to) == '.' && !move.en_passant && move.promotion == '\0') {
            continue;
        }
        const auto undo = position.make_move(move);
        const int score = -quiescence(position, ply + 1, qdepth + 1, -beta, -alpha, nodes);
        position.unmake_move(move, undo);
        best = std::max(best, score);
        alpha = std::max(alpha, score);
        if (alpha >= beta) {
            break;
        }
    }
    return best;
}

int negamax(Position& position, int depth, int ply, int alpha, int beta,
    std::uint64_t& nodes, std::uint64_t& hits, TranspositionTable* table, std::optional<Move>* best_move) {
    if (depth == 0) {
        return quiescence(position, ply, 0, alpha, beta, nodes);
    }
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
    const int original_alpha = alpha;
    std::optional<Move> preferred;
    if (table != nullptr) {
        if (const auto* entry = table->probe(position.key())) {
            ++hits;
            preferred = entry->best_move;
            const bool legal_preferred = preferred && std::find(moves.begin(), moves.end(), *preferred) != moves.end();
            const int score = score_from_table(entry->score, ply);
            if (entry->depth >= depth && (best_move == nullptr || legal_preferred) &&
                (entry->bound == Bound::exact || (entry->bound == Bound::lower && score >= beta) ||
                    (entry->bound == Bound::upper && score <= alpha))) {
                if (best_move != nullptr) *best_move = preferred;
                return score;
            }
        }
    }
    order_moves(position, moves, preferred);
    int best = -mate_score - 1;
    std::optional<Move> selected;
    for (const auto& move : moves) {
        const auto undo = position.make_move(move);
        const int score = -negamax(position, depth - 1, ply + 1, -beta, -alpha, nodes, hits, table, nullptr);
        position.unmake_move(move, undo);
        if (score > best) {
            best = score;
            selected = move;
            if (best_move != nullptr) {
                *best_move = move;
            }
        }
        alpha = std::max(alpha, score);
        if (alpha >= beta) {
            break;
        }
    }
    if (table != nullptr) {
        const auto bound = best <= original_alpha ? Bound::upper : best >= beta ? Bound::lower : Bound::exact;
        table->store({position.key(), depth, score_to_table(best, ply), bound, selected});
    }
    return best;
}

}

SearchResult search_impl(Position& position, int depth, TranspositionTable* table) {
    if (depth < 1 || depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    SearchResult result;
    result.score = negamax(position, depth, 0, -mate_score - 1, mate_score + 1,
        result.nodes, result.transposition_hits, table, &result.best_move);
    return result;
}

SearchResult search(Position& position, int depth, bool use_table) {
    if (!use_table) {
        return search_impl(position, depth, nullptr);
    }
    TranspositionTable table;
    return search_impl(position, depth, &table);
}

SearchResult search(Position& position, int depth, TranspositionTable& table) {
    return search_impl(position, depth, &table);
}

}
