#include "trickfish/multipv.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <tuple>
#include <utility>

#include "trickfish/movegen.hpp"

namespace trickfish {
namespace {

MultiPVResult single_result(SearchResult line) {
    MultiPVResult result;
    result.completed_depth = line.completed_depth;
    result.stopped = line.stopped;
    result.nodes = line.nodes;
    result.lines.push_back(std::move(line));
    return result;
}

bool ranked_before(const SearchResult& left, const SearchResult& right) {
    if (left.score != right.score) return left.score > right.score;
    const auto& a = *left.best_move;
    const auto& b = *right.best_move;
    return std::tie(a.from, a.to, a.promotion) < std::tie(b.from, b.to, b.promotion);
}

}

MultiPVResult iterative_multi_pv(Position& position, int max_depth, int count,
    const SearchOptions& options, const SearchLimits& limits, const RepetitionHistory* history) {
    if (count < 1 || count > maximum_multi_pv) throw std::invalid_argument("MultiPV must be between 1 and 16");
    if (max_depth < 1 || max_depth > 64) throw std::invalid_argument("search depth must be between 1 and 64");
    if (count == 1) return single_result(iterative_search(position, max_depth, options, limits, history));
    SearchLimits fallback_limits;
    fallback_limits.nodes = 0;
    auto fallback = iterative_search(position, 1, options, fallback_limits, history);
    const auto legal = generate_legal_moves(position);
    if (legal.empty() || position.is_insufficient_material() || is_move_count_draw(position, options.draw_policy) ||
        (history != nullptr && history->can_claim_threefold_repetition())) {
        return single_result(iterative_search(position, max_depth, options, limits, history));
    }
    std::vector<Move> allowed = options.root_moves;
    if (allowed.empty()) allowed.assign(legal.begin(), legal.end());
    const auto requested = std::min(static_cast<std::size_t>(count), allowed.size());
    MultiPVResult result;
    result.lines.push_back(std::move(fallback));
    auto shared_stop = limits.stop_requested;
    for (int depth = 1; depth <= max_depth; ++depth) {
        auto remaining = allowed;
        std::vector<SearchResult> batch;
        batch.reserve(requested);
        for (std::size_t rank = 0; rank < requested; ++rank) {
            if (limits.nodes && result.nodes >= *limits.nodes) {
                result.stopped = true;
                return result;
            }
            auto local_limits = limits;
            if (shared_stop) local_limits.stop_requested = [&shared_stop] { return shared_stop(); };
            if (limits.nodes) local_limits.nodes = *limits.nodes - result.nodes;
            auto local_options = options;
            local_options.root_moves = remaining;
            auto candidate = iterative_search(position, depth, local_options, local_limits, history);
            if (candidate.nodes > std::numeric_limits<std::uint64_t>::max() - result.nodes) {
                throw std::overflow_error("MultiPV node counter overflow");
            }
            result.nodes += candidate.nodes;
            if (candidate.stopped || candidate.completed_depth != depth) {
                result.stopped = true;
                return result;
            }
            if (!candidate.best_move) throw std::logic_error("MultiPV root search returned no move");
            const auto selected = std::find(remaining.begin(), remaining.end(), *candidate.best_move);
            if (selected == remaining.end()) throw std::logic_error("MultiPV root search escaped allowed moves");
            remaining.erase(selected);
            batch.push_back(std::move(candidate));
        }
        std::sort(batch.begin(), batch.end(), ranked_before);
        result.lines = std::move(batch);
        result.completed_depth = depth;
    }
    return result;
}

}
