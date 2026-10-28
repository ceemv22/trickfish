#include "trickfish/search.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>
#include <utility>

#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

struct SearchStopped {};

struct SearchBudget {
    std::optional<std::uint64_t> limit;
    std::optional<std::chrono::steady_clock::time_point> deadline;
    std::function<bool()> stop_requested;
    RepetitionHistory* history = nullptr;
    MoveCountDrawPolicy draw_policy = MoveCountDrawPolicy::automatic_only;
    std::uint64_t nodes = 0;
    std::uint64_t hits = 0;
    std::uint64_t pvs_probes = 0;
    std::uint64_t pvs_researches = 0;
    bool use_killers = true;
    std::array<std::array<std::optional<Move>, 2>, 64> killers{};
    std::uint64_t killer_cutoffs = 0;
    std::uint64_t killer_moves_searched = 0;
};

MoveCountDrawPolicy draw_policy(const SearchBudget* budget) {
    return budget != nullptr ? budget->draw_policy : MoveCountDrawPolicy::automatic_only;
}

std::uint64_t search_key(const Position& position, const SearchBudget* budget) {
    const auto clock = static_cast<std::uint64_t>(std::min(position.halfmove_clock(), 150));
    const auto policy = draw_policy(budget) == MoveCountDrawPolicy::claim_fifty_moves
        ? 0xd1b54a32d192ed03ULL : 0ULL;
    return position.key() ^ (clock * 0x9e3779b97f4a7c15ULL) ^ policy;
}

bool is_repetition(const SearchBudget* budget) {
    return budget != nullptr && budget->history != nullptr && budget->history->can_claim_threefold_repetition();
}

void visit(std::uint64_t& nodes, SearchBudget* budget) {
    if (budget != nullptr) {
        if ((budget->limit && budget->nodes >= *budget->limit) ||
            (budget->deadline && std::chrono::steady_clock::now() >= *budget->deadline) ||
            (budget->stop_requested && budget->stop_requested())) {
            throw SearchStopped{};
        }
        ++budget->nodes;
    }
    ++nodes;
}

class MoveScope {
public:
    MoveScope(Position& position, const Move& move, RepetitionHistory* history)
        : position_(position), move_(move), undo_(position.make_move(move)), history_(history) {
        try {
            if (history_ != nullptr) history_->push(position_);
        } catch (...) {
            position_.unmake_move(move_, undo_);
            throw;
        }
    }
    ~MoveScope() {
        if (history_ != nullptr) history_->pop();
        position_.unmake_move(move_, undo_);
    }
    MoveScope(const MoveScope&) = delete;
    MoveScope& operator=(const MoveScope&) = delete;
private:
    Position& position_;
    Move move_;
    UndoState undo_;
    RepetitionHistory* history_;
};

bool is_quiet(const Position& position, const Move& move) {
    return position.piece_at(move.to) == '.' && !move.en_passant && move.promotion == '\0';
}

int killer_priority(const Position& position, const Move& move, const SearchBudget* budget, int ply) {
    if (budget == nullptr || !budget->use_killers || ply < 0 || ply >= 64 || !is_quiet(position, move)) return 0;
    const auto& slots = budget->killers[static_cast<std::size_t>(ply)];
    if (move == slots[0]) return 5000;
    if (move == slots[1]) return 4000;
    return 0;
}

void record_killer(const Position& position, const Move& move, SearchBudget* budget, int ply) {
    if (budget == nullptr || !budget->use_killers || ply < 0 || ply >= 64 || !is_quiet(position, move)) return;
    ++budget->killer_cutoffs;
    auto& slots = budget->killers[static_cast<std::size_t>(ply)];
    if (move != slots[0]) {
        slots[1] = slots[0];
        slots[0] = move;
    }
}

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

void order_moves(const Position& position, MoveList& moves, std::optional<Move> preferred = std::nullopt,
    const SearchBudget* budget = nullptr, int ply = 0) {
    std::sort(moves.begin(), moves.end(), [&position, preferred, budget, ply](const Move& left, const Move& right) {
        if ((left == preferred) != (right == preferred)) return left == preferred;
        const auto left_priority = move_priority(position, left) + killer_priority(position, left, budget, ply);
        const auto right_priority = move_priority(position, right) + killer_priority(position, right, budget, ply);
        if (left_priority != right_priority) {
            return left_priority > right_priority;
        }
        if (left.from != right.from) return left.from < right.from;
        if (left.to != right.to) return left.to < right.to;
        return left.promotion < right.promotion;
    });
}

int static_for_side(const Position& position) {
    const auto score = evaluate_static(position);
    return position.side_to_move() == Color::white ? score : -score;
}

int quiescence(Position& position, int ply, int qdepth, int alpha, int beta, std::uint64_t& nodes, SearchBudget* budget) {
    visit(nodes, budget);
    auto moves = generate_legal_moves(position);
    const bool in_check = position.in_check(position.side_to_move());
    if (moves.empty()) {
        return in_check ? -mate_score + ply : 0;
    }
    if (is_move_count_draw(position, draw_policy(budget))) {
        return 0;
    }
    if (position.is_insufficient_material() || is_repetition(budget)) {
        return 0;
    }
    if (qdepth >= 32) {
        return static_for_side(position);
    }
    int best = -mate_score - 1;
    if (!in_check) {
        best = static_for_side(position);
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
            MoveScope scope(position, move, budget != nullptr ? budget->history : nullptr);
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
    std::uint64_t& nodes, std::uint64_t& hits, TranspositionTable* table, std::optional<Move>* best_move, std::vector<Move>& pv, SearchBudget* budget, bool use_pvs) {
    if (depth == 0) {
        return quiescence(position, ply, 0, alpha, beta, nodes, budget);
    }
    visit(nodes, budget);
    auto moves = generate_legal_moves(position);
    if (moves.empty()) {
        return position.in_check(position.side_to_move()) ? -mate_score + ply : 0;
    }
    if (is_move_count_draw(position, draw_policy(budget))) {
        return 0;
    }
    if (position.is_insufficient_material() || is_repetition(budget)) {
        if (best_move != nullptr) {
            *best_move = moves[0];
            pv.push_back(moves[0]);
        }
        return 0;
    }
    const int original_alpha = alpha;
    std::optional<Move> preferred;
    if (table != nullptr) {
        if (const auto* entry = table->probe(search_key(position, budget))) {
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
    order_moves(position, moves, preferred, budget, ply);
    int best = -mate_score - 1;
    std::optional<Move> selected;
    for (const auto& move : moves) {
        if (killer_priority(position, move, budget, ply) != 0) ++budget->killer_moves_searched;
        std::vector<Move> child_pv;
        int score = 0;
        {
            MoveScope scope(position, move, budget != nullptr ? budget->history : nullptr);
            if (use_pvs && selected && beta > alpha + 1) {
                ++budget->pvs_probes;
                score = -negamax(position, depth - 1, ply + 1, -alpha - 1, -alpha,
                    nodes, hits, table, nullptr, child_pv, budget, use_pvs);
                if (score > alpha && score < beta) {
                    ++budget->pvs_researches;
                    child_pv.clear();
                    score = -negamax(position, depth - 1, ply + 1, -beta, -alpha,
                        nodes, hits, table, nullptr, child_pv, budget, use_pvs);
                }
            } else {
                score = -negamax(position, depth - 1, ply + 1, -beta, -alpha,
                    nodes, hits, table, nullptr, child_pv, budget, use_pvs);
            }
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
            record_killer(position, move, budget, ply);
            break;
        }
    }
    if (table != nullptr) {
        const auto bound = best <= original_alpha ? Bound::upper : best >= beta ? Bound::lower : Bound::exact;
        table->store({search_key(position, budget), depth, score_to_table(best, ply), bound, selected});
    }
    return best;
}

}

SearchResult search_impl(Position& position, int depth, TranspositionTable* table, SearchBudget* budget = nullptr, bool use_pvs = true,
    int alpha = -mate_score - 1, int beta = mate_score + 1, bool use_killers = true) {
    if (depth < 1 || depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    SearchBudget local_budget;
    local_budget.use_killers = use_killers;
    if (budget == nullptr) budget = &local_budget;
    SearchResult result;
    result.score = negamax(position, depth, 0, alpha, beta,
        result.nodes, result.transposition_hits, table, &result.best_move, result.principal_variation, budget, use_pvs);
    result.completed_depth = depth;
    result.pvs_probes = budget->pvs_probes;
    result.pvs_researches = budget->pvs_researches;
    result.killer_cutoffs = budget->killer_cutoffs;
    result.killer_moves_searched = budget->killer_moves_searched;
    return result;
}

SearchResult search(Position& position, int depth, bool use_table, bool use_pvs, bool use_killers) {
    if (!use_table) {
        return search_impl(position, depth, nullptr, nullptr, use_pvs, -mate_score - 1, mate_score + 1, use_killers);
    }
    TranspositionTable table;
    return search_impl(position, depth, &table, nullptr, use_pvs, -mate_score - 1, mate_score + 1, use_killers);
}

SearchResult search(Position& position, int depth, TranspositionTable& table, bool use_pvs, bool use_killers) {
    return search_impl(position, depth, &table, nullptr, use_pvs, -mate_score - 1, mate_score + 1, use_killers);
}

SearchResult iterative_search(Position& position, int max_depth, bool use_table,
    std::optional<std::uint64_t> node_limit,
    std::optional<std::chrono::steady_clock::time_point> deadline,
    std::function<bool()> stop_requested, const RepetitionHistory* history, MoveCountDrawPolicy draw_policy, bool use_pvs, int aspiration_window, bool use_killers) {
    if (max_depth < 1 || max_depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    if (aspiration_window < 0 || aspiration_window > mate_score + 1) {
        throw std::invalid_argument("aspiration window must be between 0 and 100001");
    }
    std::optional<RepetitionHistory> active_history;
    if (history != nullptr) {
        if (history->current_key() != position.key()) {
            throw std::invalid_argument("repetition history does not end at the root position");
        }
        active_history.emplace(*history);
    }
    std::optional<TranspositionTable> table;
    if (use_table && history == nullptr) {
        table.emplace();
    }
    SearchBudget budget{node_limit, deadline, stop_requested, active_history ? &*active_history : nullptr, draw_policy};
    budget.use_killers = use_killers;
    SearchResult result;
    const auto legal = generate_legal_moves(position);
    if (!legal.empty()) {
        result.best_move = legal[0];
    }
    result.score = evaluate_for_side_to_move(position);
    if (is_move_count_draw(position, draw_policy)) {
        result.score = 0;
        result.best_move.reset();
    }
    std::uint64_t fail_low = 0;
    std::uint64_t fail_high = 0;
    for (int depth = 1; depth <= max_depth; ++depth) {
        try {
            int radius = aspiration_window;
            const int center = result.score;
            const bool narrow = depth > 1 && radius > 0 && std::abs(center) < mate_threshold;
            int alpha = narrow ? std::max(-mate_score - 1, center - radius) : -mate_score - 1;
            int beta = narrow ? std::min(mate_score + 1, center + radius) : mate_score + 1;
            while (true) {
                auto candidate = search_impl(position, depth, table ? &*table : nullptr, &budget, use_pvs, alpha, beta);
                if (candidate.score > alpha && candidate.score < beta) {
                    result = std::move(candidate);
                    break;
                }
                if (candidate.score <= alpha) ++fail_low;
                else ++fail_high;
                radius = std::min(2 * (mate_score + 1), radius * 2);
                alpha = std::max(-mate_score - 1, center - radius);
                beta = std::min(mate_score + 1, center + radius);
            }
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
    result.pvs_probes = budget.pvs_probes;
    result.pvs_researches = budget.pvs_researches;
    result.aspiration_fail_low = fail_low;
    result.aspiration_fail_high = fail_high;
    result.killer_cutoffs = budget.killer_cutoffs;
    result.killer_moves_searched = budget.killer_moves_searched;
    return result;
}

}
