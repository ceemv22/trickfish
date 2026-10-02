#include "trickfish/search.hpp"

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

struct SearchStopped {};

struct SearchBudget {
    std::optional<std::uint64_t> limit;
    std::uint64_t nodes = 0;
    std::uint64_t hits = 0;
};

void visit(std::uint64_t& nodes, SearchBudget* budget) {
    if (budget != nullptr) {
        if (budget->limit && budget->nodes >= *budget->limit) {
            throw SearchStopped{};
        }
        ++budget->nodes;
    }
    ++nodes;
}

class MoveScope {
public:
    MoveScope(Position& position, const Move& move)
        : position_(position), move_(move), undo_(position.make_move(move)) {}
    ~MoveScope() { position_.unmake_move(move_, undo_); }
    MoveScope(const MoveScope&) = delete;
    MoveScope& operator=(const MoveScope&) = delete;
private:
    Position& position_;
    Move move_;
    UndoState undo_;
};

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

int quiescence(Position& position, int ply, int qdepth, int alpha, int beta, std::uint64_t& nodes, SearchBudget* budget) {
    visit(nodes, budget);
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
        int score = 0;
        {
            MoveScope scope(position, move);
            score = -quiescence(position, ply + 1, qdepth + 1, -beta, -alpha, nodes, budget);
        }
        best = std::max(best, score);
        alpha = std::max(alpha, score);
        if (alpha >= beta) {
            break;
        }
    }
    return best;
}

int negamax(Position& position, int depth, int ply, int alpha, int beta,
    std::uint64_t& nodes, std::uint64_t& hits, TranspositionTable* table, std::optional<Move>* best_move, std::vector<Move>& pv, SearchBudget* budget) {
    if (depth == 0) {
        return quiescence(position, ply, 0, alpha, beta, nodes, budget);
    }
    visit(nodes, budget);
    auto moves = generate_legal_moves(position);
    if (moves.empty()) {
        return position.in_check(position.side_to_move()) ? -mate_score + ply : 0;
    }
    if (position.is_insufficient_material()) {
        if (best_move != nullptr) {
            *best_move = moves[0];
            pv.push_back(moves[0]);
        }
        return 0;
    }
    const int original_alpha = alpha;
    std::optional<Move> preferred;
    if (table != nullptr) {
        if (const auto* entry = table->probe(position.key())) {
            ++hits;
            if (budget != nullptr) ++budget->hits;
            preferred = entry->best_move;
            const bool legal_preferred = preferred && std::find(moves.begin(), moves.end(), *preferred) != moves.end();
            const int score = score_from_table(entry->score, ply);
            if (entry->depth >= depth && (best_move == nullptr || legal_preferred) &&
                (entry->bound == Bound::exact || (entry->bound == Bound::lower && score >= beta) ||
                    (entry->bound == Bound::upper && score <= alpha))) {
                if (best_move != nullptr) *best_move = preferred;
                if (legal_preferred) pv.push_back(*preferred);
                return score;
            }
        }
    }
    order_moves(position, moves, preferred);
    int best = -mate_score - 1;
    std::optional<Move> selected;
    for (const auto& move : moves) {
        std::vector<Move> child_pv;
        int score = 0;
        {
            MoveScope scope(position, move);
            score = -negamax(position, depth - 1, ply + 1, -beta, -alpha, nodes, hits, table, nullptr, child_pv, budget);
        }
        if (score > best) {
            best = score;
            selected = move;
            pv.clear();
            pv.push_back(move);
            pv.insert(pv.end(), child_pv.begin(), child_pv.end());
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

SearchResult search_impl(Position& position, int depth, TranspositionTable* table, SearchBudget* budget = nullptr) {
    if (depth < 1 || depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    SearchResult result;
    result.score = negamax(position, depth, 0, -mate_score - 1, mate_score + 1,
        result.nodes, result.transposition_hits, table, &result.best_move, result.principal_variation, budget);
    result.completed_depth = depth;
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

SearchResult iterative_search(Position& position, int max_depth, bool use_table,
    std::optional<std::uint64_t> node_limit) {
    if (max_depth < 1 || max_depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    std::optional<TranspositionTable> table;
    if (use_table) {
        table.emplace();
    }
    SearchBudget budget{node_limit};
    SearchResult result;
    const auto legal = generate_legal_moves(position);
    if (!legal.empty()) {
        result.best_move = legal[0];
    }
    result.score = evaluate_for_side_to_move(position);
    for (int depth = 1; depth <= max_depth; ++depth) {
        try {
            result = search_impl(position, depth, table ? &*table : nullptr, &budget);
        } catch (const SearchStopped&) {
            result.stopped = true;
            break;
        }
        if (!result.best_move) {
            break;
        }
    }
    result.nodes = budget.nodes;
    result.transposition_hits = budget.hits;
    return result;
}

}
