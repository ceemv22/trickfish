#include "trickfish/search.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <utility>

#include "trickfish/evaluation.hpp"
#include "trickfish/exchange.hpp"
#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

struct SearchStopped {};

struct ContinuationEntry {
    std::uint32_t key = 0xffffffffU;
    int score = 0;
};

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
    bool use_history = true;
    std::array<std::array<std::array<int, 64>, 64>, 2> quiet_history{};
    std::uint64_t history_rewards = 0;
    std::uint64_t history_penalties = 0;
    std::uint64_t history_moves_searched = 0;
    bool use_exchange_ordering = false;
    std::uint64_t exchange_evaluations = 0;
    std::uint64_t exchange_nodes = 0;
    std::uint64_t exchange_cutoffs = 0;
    bool use_continuation = true;
    std::vector<ContinuationEntry> continuation;
    std::uint64_t continuation_updates = 0;
    std::uint64_t continuation_moves_searched = 0;
    const std::vector<Move>* root_moves = nullptr;
    bool use_null_move = false;
    int synthetic_null = 0;
    std::uint64_t null_probes = 0;
    std::uint64_t null_verifications = 0;
    std::uint64_t null_cutoffs = 0;
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
    return budget != nullptr && budget->synthetic_null == 0 && budget->history != nullptr && budget->history->can_claim_threefold_repetition();
}

void check_stop(SearchBudget* budget) {
    if (budget != nullptr && ((budget->limit && budget->nodes >= *budget->limit) ||
        (budget->deadline && std::chrono::steady_clock::now() >= *budget->deadline) ||
        (budget->stop_requested && budget->stop_requested()))) {
        throw SearchStopped{};
    }
}

void visit(std::uint64_t& nodes, SearchBudget* budget) {
    check_stop(budget);
    if (budget != nullptr) ++budget->nodes;
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

class NullScope {
public:
    NullScope(Position& position, SearchBudget& budget)
        : position_(position), budget_(budget), undo_(position.make_null_move()) { ++budget_.synthetic_null; }
    ~NullScope() { --budget_.synthetic_null; position_.unmake_null_move(undo_); }
    NullScope(const NullScope&) = delete;
    NullScope& operator=(const NullScope&) = delete;
private:
    Position& position_;
    SearchBudget& budget_;
    NullUndoState undo_;
};

bool is_quiet(const Position& position, const Move& move) {
    return position.piece_at(move.to) == '.' && !move.en_passant && move.promotion == '\0';
}

int history_priority(const Position& position, const Move& move, const SearchBudget* budget) {
    if (budget == nullptr || !budget->use_history || !is_quiet(position, move)) return 0;
    return budget->quiet_history[static_cast<std::size_t>(position.side_to_move())][move.from][move.to];
}

void update_history(const Position& position, const Move& move, SearchBudget* budget, int bonus) {
    if (budget == nullptr || budget->synthetic_null != 0 || !budget->use_history || !is_quiet(position, move)) return;
    auto& score = budget->quiet_history[static_cast<std::size_t>(position.side_to_move())][move.from][move.to];
    score += bonus - score * std::abs(bonus) / 16384;
    score = std::clamp(score, -16384, 16384);
    if (bonus > 0) ++budget->history_rewards;
    else ++budget->history_penalties;
}

std::optional<std::uint32_t> continuation_key(const Position& position, const Move& move,
    const std::optional<Move>& previous) {
    if (!previous || !is_quiet(position, move)) return std::nullopt;
    const auto prior = position.piece_at(previous->to);
    if (prior == '.') return std::nullopt;
    const auto prior_type = static_cast<std::uint32_t>(piece_type_from_symbol(prior));
    const auto current_type = static_cast<std::uint32_t>(piece_type_from_symbol(position.piece_at(move.from)));
    return (static_cast<std::uint32_t>(position.side_to_move()) << 18) |
        (prior_type << 15) | (static_cast<std::uint32_t>(previous->to) << 9) |
        (current_type << 6) | move.to;
}

std::size_t continuation_slot(std::uint32_t key) {
    return (key * 0x9e3779b9U) >> 18;
}

int continuation_priority(const Position& position, const Move& move, const SearchBudget* budget,
    const std::optional<Move>& previous) {
    if (budget == nullptr || !budget->use_continuation || budget->continuation.empty()) return 0;
    const auto key = continuation_key(position, move, previous);
    if (!key) return 0;
    const auto& entry = budget->continuation[continuation_slot(*key)];
    return entry.key == *key ? entry.score : 0;
}

void update_continuation(const Position& position, const Move& move, SearchBudget* budget,
    const std::optional<Move>& previous, int bonus) {
    if (budget == nullptr || budget->synthetic_null != 0 || !budget->use_continuation) return;
    const auto key = continuation_key(position, move, previous);
    if (!key) return;
    if (budget->continuation.empty()) budget->continuation.resize(16384);
    auto& entry = budget->continuation[continuation_slot(*key)];
    if (entry.key != *key) entry = {*key, 0};
    entry.score += bonus - entry.score * std::abs(bonus) / 16384;
    entry.score = std::clamp(entry.score, -16384, 16384);
    ++budget->continuation_updates;
}

int killer_priority(const Position& position, const Move& move, const SearchBudget* budget, int ply) {
    if (budget == nullptr || !budget->use_killers || ply < 0 || ply >= 64 || !is_quiet(position, move)) return 0;
    const auto& slots = budget->killers[static_cast<std::size_t>(ply)];
    if (move == slots[0]) return 5000;
    if (move == slots[1]) return 4000;
    return 0;
}

void record_killer(const Position& position, const Move& move, SearchBudget* budget, int ply) {
    if (budget == nullptr || budget->synthetic_null != 0 || !budget->use_killers || ply < 0 || ply >= 64 || !is_quiet(position, move)) return;
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
    SearchBudget* budget = nullptr, int ply = 0, std::optional<Move> previous = std::nullopt) {
    if (budget != nullptr && budget->use_exchange_ordering) {
        struct RankedMove { Move move; int exchange = 0; bool tactical = false; };
        std::array<RankedMove, MoveList::capacity> ranked{};
        for (std::size_t index = 0; index < moves.size(); ++index) {
            const auto& move = moves[index];
            ranked[index] = {move, 0, !is_quiet(position, move)};
            if (ranked[index].tactical) {
                const auto exchange = analyze_exchange(position, move, false, [budget] { check_stop(budget); });
                ranked[index].exchange = exchange.score;
                ++budget->exchange_evaluations;
                budget->exchange_nodes += exchange.nodes;
                budget->exchange_cutoffs += exchange.cutoffs;
            }
        }
        std::sort(ranked.begin(), ranked.begin() + moves.size(),
            [&position, preferred, budget, ply, previous](const RankedMove& left, const RankedMove& right) {
                if ((left.move == preferred) != (right.move == preferred)) return left.move == preferred;
                if (left.tactical != right.tactical) return left.tactical;
                if (left.tactical && left.exchange != right.exchange) return left.exchange > right.exchange;
                const int left_priority = move_priority(position, left.move) + killer_priority(position, left.move, budget, ply);
                const int right_priority = move_priority(position, right.move) + killer_priority(position, right.move, budget, ply);
                if (left_priority != right_priority) return left_priority > right_priority;
                const int left_history = history_priority(position, left.move, budget) + continuation_priority(position, left.move, budget, previous);
                const int right_history = history_priority(position, right.move, budget) + continuation_priority(position, right.move, budget, previous);
                if (left_history != right_history) return left_history > right_history;
                if (left.move.from != right.move.from) return left.move.from < right.move.from;
                if (left.move.to != right.move.to) return left.move.to < right.move.to;
                return left.move.promotion < right.move.promotion;
            });
        for (std::size_t index = 0; index < moves.size(); ++index) moves[index] = ranked[index].move;
        return;
    }
    std::sort(moves.begin(), moves.end(), [&position, preferred, budget, ply, previous](const Move& left, const Move& right) {
        if ((left == preferred) != (right == preferred)) return left == preferred;
        const auto left_priority = move_priority(position, left) + killer_priority(position, left, budget, ply);
        const auto right_priority = move_priority(position, right) + killer_priority(position, right, budget, ply);
        if (left_priority != right_priority) {
            return left_priority > right_priority;
        }
        const auto left_history = history_priority(position, left, budget) + continuation_priority(position, left, budget, previous);
        const auto right_history = history_priority(position, right, budget) + continuation_priority(position, right, budget, previous);
        if (left_history != right_history) return left_history > right_history;
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
    if ((budget == nullptr || budget->synthetic_null == 0) && is_move_count_draw(position, draw_policy(budget))) {
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
            MoveScope scope(position, move, budget != nullptr && budget->synthetic_null == 0 ? budget->history : nullptr);
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
    std::uint64_t& nodes, std::uint64_t& hits, TranspositionTable* table, std::optional<Move>* best_move, std::vector<Move>& pv, SearchBudget* budget, bool use_pvs, std::optional<Move> previous, bool allow_null) {
    if (depth == 0) {
        return quiescence(position, ply, 0, alpha, beta, nodes, budget);
    }
    visit(nodes, budget);
    auto moves = generate_legal_moves(position);
    if (moves.empty()) {
        return position.in_check(position.side_to_move()) ? -mate_score + ply : 0;
    }
    if (ply == 0 && budget->root_moves != nullptr) {
        MoveList allowed;
        for (const auto& move : moves) {
            if (std::find(budget->root_moves->begin(), budget->root_moves->end(), move) != budget->root_moves->end()) {
                allowed.push(move);
            }
        }
        moves = allowed;
    }
    if ((budget == nullptr || budget->synthetic_null == 0) && is_move_count_draw(position, draw_policy(budget))) {
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
    const auto color = position.side_to_move();
    const auto non_pawns = position.pieces(color, PieceType::knight) | position.pieces(color, PieceType::bishop) |
        position.pieces(color, PieceType::rook) | position.pieces(color, PieceType::queen);
    const int draw_limit = draw_policy(budget) == MoveCountDrawPolicy::claim_fifty_moves ? 100 : 150;
    if (budget->use_null_move && allow_null && budget->synthetic_null == 0 && ply > 0 && depth >= 3 &&
        beta == alpha + 1 && std::abs(beta) < mate_threshold && !position.in_check(color) && non_pawns != 0 &&
        position.halfmove_clock() < draw_limit - depth - 32 &&
        position.fullmove_number() < std::numeric_limits<int>::max() - 128 && static_for_side(position) >= beta) {
        ++budget->null_probes;
        std::vector<Move> ignored;
        int probe = 0;
        {
            NullScope scope(position, *budget);
            probe = -negamax(position, depth - 3, ply + 1, -beta, -beta + 1,
                nodes, hits, nullptr, nullptr, ignored, budget, use_pvs, std::nullopt, false);
        }
        if (probe >= beta) {
            ++budget->null_verifications;
            ignored.clear();
            const int verified = negamax(position, depth, ply, alpha, beta,
                nodes, hits, nullptr, nullptr, ignored, budget, use_pvs, previous, false);
            if (verified >= beta) {
                ++budget->null_cutoffs;
                pv = std::move(ignored);
                return verified;
            }
        }
    }
    order_moves(position, moves, preferred, budget, ply, previous);
    int best = -mate_score - 1;
    std::optional<Move> selected;
    MoveList searched_quiets;
    for (const auto& move : moves) {
        if (killer_priority(position, move, budget, ply) != 0) ++budget->killer_moves_searched;
        if (history_priority(position, move, budget) != 0) ++budget->history_moves_searched;
        if (continuation_priority(position, move, budget, previous) != 0) ++budget->continuation_moves_searched;
        std::vector<Move> child_pv;
        int score = 0;
        {
            MoveScope scope(position, move, budget != nullptr && budget->synthetic_null == 0 ? budget->history : nullptr);
            if (use_pvs && selected && beta > alpha + 1) {
                ++budget->pvs_probes;
                score = -negamax(position, depth - 1, ply + 1, -alpha - 1, -alpha,
                    nodes, hits, table, nullptr, child_pv, budget, use_pvs, move, allow_null);
                if (score > alpha && score < beta) {
                    ++budget->pvs_researches;
                    child_pv.clear();
                    score = -negamax(position, depth - 1, ply + 1, -beta, -alpha,
                        nodes, hits, table, nullptr, child_pv, budget, use_pvs, move, allow_null);
                }
            } else {
                score = -negamax(position, depth - 1, ply + 1, -beta, -alpha,
                    nodes, hits, table, nullptr, child_pv, budget, use_pvs, move, allow_null);
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
            if (is_quiet(position, move)) {
                const int bonus = std::min(512, depth * depth);
                update_history(position, move, budget, bonus);
                update_continuation(position, move, budget, previous, bonus);
                for (const auto& quiet : searched_quiets) {
                    update_history(position, quiet, budget, -bonus);
                    update_continuation(position, quiet, budget, previous, -bonus);
                }
            }
            break;
        }
        if (is_quiet(position, move)) searched_quiets.push(move);
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
        result.nodes, result.transposition_hits, table, &result.best_move, result.principal_variation, budget, use_pvs, std::nullopt, true);
    result.completed_depth = depth;
    result.pvs_probes = budget->pvs_probes;
    result.pvs_researches = budget->pvs_researches;
    result.killer_cutoffs = budget->killer_cutoffs;
    result.killer_moves_searched = budget->killer_moves_searched;
    result.history_rewards = budget->history_rewards;
    result.history_penalties = budget->history_penalties;
    result.history_moves_searched = budget->history_moves_searched;
    result.continuation_updates = budget->continuation_updates;
    result.continuation_moves_searched = budget->continuation_moves_searched;
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
    SearchOptions options;
    options.use_table = use_table;
    options.use_pvs = use_pvs;
    options.use_killers = use_killers;
    options.aspiration_window = aspiration_window;
    options.draw_policy = draw_policy;
    const SearchLimits limits{node_limit, deadline, std::move(stop_requested)};
    return iterative_search(position, max_depth, options, limits, history);
}

SearchResult iterative_search(Position& position, int max_depth, const SearchOptions& options,
    const SearchLimits& limits, const RepetitionHistory* history) {
    if (max_depth < 1 || max_depth > 64) {
        throw std::invalid_argument("search depth must be between 1 and 64");
    }
    if (options.aspiration_window < 0 || options.aspiration_window > mate_score + 1) {
        throw std::invalid_argument("aspiration window must be between 0 and 100001");
    }
    const auto root_legal = generate_legal_moves(position);
    for (std::size_t index = 0; index < options.root_moves.size(); ++index) {
        const auto& move = options.root_moves[index];
        if (std::find(root_legal.begin(), root_legal.end(), move) == root_legal.end() ||
            std::find(options.root_moves.begin(), options.root_moves.begin() + index, move) != options.root_moves.begin() + index) {
            throw std::invalid_argument("root moves must be unique legal moves");
        }
    }
    std::optional<RepetitionHistory> active_history;
    if (history != nullptr) {
        if (history->current_key() != position.key()) {
            throw std::invalid_argument("repetition history does not end at the root position");
        }
        active_history.emplace(*history);
    }
    std::optional<TranspositionTable> table;
    if (options.use_table && history == nullptr && options.root_moves.empty()) {
        table.emplace();
    }
    SearchBudget budget{limits.nodes, limits.deadline, limits.stop_requested, active_history ? &*active_history : nullptr, options.draw_policy};
    budget.use_killers = options.use_killers;
    budget.use_history = options.use_history;
    budget.use_exchange_ordering = options.use_exchange_ordering;
    budget.use_continuation = options.use_continuation;
    budget.use_null_move = options.use_null_move;
    if (!options.root_moves.empty()) budget.root_moves = &options.root_moves;
    SearchResult result;
    if (!root_legal.empty()) {
        result.best_move = options.root_moves.empty() ? root_legal[0] : options.root_moves.front();
    }
    result.score = evaluate_for_side_to_move(position);
    if (is_move_count_draw(position, options.draw_policy)) {
        result.score = 0;
        result.best_move.reset();
    }
    std::uint64_t fail_low = 0;
    std::uint64_t fail_high = 0;
    for (int depth = 1; depth <= max_depth; ++depth) {
        try {
            int radius = options.aspiration_window;
            const int center = result.score;
            const bool narrow = depth > 1 && radius > 0 && std::abs(center) < mate_threshold;
            int alpha = narrow ? std::max(-mate_score - 1, center - radius) : -mate_score - 1;
            int beta = narrow ? std::min(mate_score + 1, center + radius) : mate_score + 1;
            while (true) {
                auto candidate = search_impl(position, depth, table ? &*table : nullptr, &budget, options.use_pvs, alpha, beta);
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
    result.history_rewards = budget.history_rewards;
    result.history_penalties = budget.history_penalties;
    result.history_moves_searched = budget.history_moves_searched;
    result.exchange_evaluations = budget.exchange_evaluations;
    result.exchange_nodes = budget.exchange_nodes;
    result.exchange_cutoffs = budget.exchange_cutoffs;
    result.continuation_updates = budget.continuation_updates;
    result.continuation_moves_searched = budget.continuation_moves_searched;
    result.null_probes = budget.null_probes;
    result.null_verifications = budget.null_verifications;
    result.null_cutoffs = budget.null_cutoffs;
    return result;
}

}
