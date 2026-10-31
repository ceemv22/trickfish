#include <algorithm>
#include <chrono>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

#include "trickfish/movegen.hpp"
#include "trickfish/multipv.hpp"
#include "trickfish/reporting.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void equivalent(const SearchResult& left, const SearchResult& right) {
    require(left.best_move == right.best_move && left.score == right.score &&
        left.principal_variation == right.principal_variation && left.completed_depth == right.completed_depth &&
        left.nodes == right.nodes && left.stopped == right.stopped && left.transposition_hits == right.transposition_hits &&
        left.aspiration_fail_low == right.aspiration_fail_low && left.aspiration_fail_high == right.aspiration_fail_high &&
        left.pvs_probes == right.pvs_probes && left.pvs_researches == right.pvs_researches &&
        left.pawn_cache_hits == right.pawn_cache_hits && left.pawn_cache_misses == right.pawn_cache_misses &&
        left.quiescence_ordering_calls == right.quiescence_ordering_calls &&
        left.quiescence_ordered_moves == right.quiescence_ordered_moves &&
        left.quiescence_filtered_quiet_moves == right.quiescence_filtered_quiet_moves,
        "observer changed search result or cumulative counters");
}

void legal_lines(const Position& root, const MultiPVResult& progress) {
    require(progress.completed_depth > 0 && !progress.stopped && !progress.lines.empty(), "observer published incomplete iteration");
    for (const auto& line : progress.lines) {
        require(line.completed_depth == progress.completed_depth && !line.stopped, "observer mixed completed depths");
        auto position = root;
        for (const auto& move : line.principal_variation) {
            const auto legal = generate_legal_moves(position);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "observer PV is illegal");
            const auto undo = position.make_move(move);
            static_cast<void>(undo);
        }
    }
}

int main() {
    try {
        const auto zero = search_timing(100, std::chrono::milliseconds(0));
        const auto negative = search_timing(100, std::chrono::milliseconds(-1));
        require(zero.milliseconds == 0 && zero.nodes_per_second == 0 && negative.milliseconds == 0 &&
            negative.nodes_per_second == 0, "zero/negative timing wrapped or divided by zero");
        const auto regular = search_timing(1234, std::chrono::milliseconds(500));
        require(regular.milliseconds == 500 && regular.nodes_per_second == 2468, "ordinary NPS conversion changed scale");
        const auto maximum = std::numeric_limits<std::uint64_t>::max();
        require(search_timing(maximum, std::chrono::milliseconds(1)).nodes_per_second == maximum,
            "NPS overflow did not saturate");
        require(search_timing(1, std::chrono::milliseconds(2000)).nodes_per_second == 0, "fractional NPS did not truncate");
        auto root = Position::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        const auto pawn_key = root.pawn_key();
        const auto phase = root.phase_units();
        RepetitionHistory history(root);
        SearchOptions options;
        options.aspiration_window = 1;
        options.use_pawn_cache = true;
        const auto unchanged = [&] {
            require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && root.phase_units() == phase &&
                history.size() == 1 && history.current_key() == key && history.current_count() == 1,
                "observer boundary did not restore root/history");
        };
        for (const bool with_history : {false, true}) {
            const auto* supplied = with_history ? &history : nullptr;
            const auto reference = iterative_search(root, 3, options, {}, supplied);
            std::vector<SearchResult> events;
            const auto observed = iterative_search(root, 3, options, {}, supplied, [&](const SearchResult& progress) {
                unchanged();
                require(progress.completed_depth == static_cast<int>(events.size() + 1) && !progress.stopped,
                    "single observer duplicated/skipped a completed depth");
                if (!events.empty()) require(progress.nodes > events.back().nodes, "single observer lost cumulative work");
                events.push_back(progress);
            });
            equivalent(reference, observed);
            require(events.size() == 3, "single observer event count mismatch");
            equivalent(events.back(), observed);
        }
        const auto reference = iterative_multi_pv(root, 2, 3, options, {}, &history);
        std::vector<MultiPVResult> batches;
        const auto observed = iterative_multi_pv(root, 2, 3, options, {}, &history, [&](const MultiPVResult& progress) {
            unchanged();
            legal_lines(root, progress);
            require(progress.completed_depth == static_cast<int>(batches.size() + 1) && progress.lines.size() == 3,
                "MultiPV observer leaked an inner or partial search");
            if (!batches.empty()) require(progress.nodes > batches.back().nodes, "MultiPV observer lost cumulative work");
            batches.push_back(progress);
        });
        require(batches.size() == 2 && observed.nodes == reference.nodes && observed.completed_depth == reference.completed_depth,
            "MultiPV observer changed aggregate trace");
        for (std::size_t index = 0; index < observed.lines.size(); ++index) {
            equivalent(reference.lines[index], observed.lines[index]);
            equivalent(batches.back().lines[index], observed.lines[index]);
        }
        for (const int count : {1, 3}) {
            std::vector<MultiPVResult> events;
            const auto first = iterative_multi_pv(root, 1, count, options, {}, &history);
            SearchLimits limits;
            limits.nodes = first.nodes + 1;
            const auto limited = iterative_multi_pv(root, 4, count, options, limits, &history,
                [&](const MultiPVResult& progress) { unchanged(); events.push_back(progress); });
            require(limited.stopped && limited.nodes == *limits.nodes && limited.completed_depth == 1 && events.size() == 1 &&
                events.front().completed_depth == 1 && events.front().nodes == first.nodes,
                "interrupted depth produced an observer event or lost work");
            events.clear();
            limits.nodes = 0;
            const auto fallback = iterative_multi_pv(root, 3, count, options, limits, &history,
                [&](const MultiPVResult& progress) { events.push_back(progress); });
            require(events.empty() && fallback.completed_depth == 0 && fallback.nodes == 0 && fallback.stopped,
                "fallback was reported as a completed iteration");
            limits = {};
            bool stop = false;
            limits.stop_requested = [&] { return stop; };
            const auto cancelled = iterative_multi_pv(root, 3, count, options, limits, &history, [&](const MultiPVResult& progress) {
                unchanged();
                events.push_back(progress);
                stop = true;
            });
            require(cancelled.stopped && events.size() == 1 && cancelled.completed_depth == 1 &&
                cancelled.nodes == events.back().nodes, "observer cancellation did not preserve completed batch");
            bool propagated = false;
            try {
                static_cast<void>(iterative_multi_pv(root, 3, count, options, {}, &history, [&](const MultiPVResult&) {
                    unchanged();
                    throw std::runtime_error("injected observer failure");
                }));
            } catch (const std::runtime_error&) { propagated = true; }
            require(propagated, "observer failure was swallowed");
            unchanged();
        }
        for (const auto terminal_fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"}) {
            auto terminal = Position::from_fen(terminal_fen);
            int calls = 0;
            const auto result = iterative_multi_pv(terminal, 3, 3, {}, {}, nullptr, [&](const MultiPVResult& progress) {
                legal_lines(terminal, progress);
                require(progress.lines.size() == 1 && progress.completed_depth == 1, "terminal observer emitted competing lines");
                ++calls;
            });
            require(calls == 1 && result.completed_depth == 1, "terminal progress was not delivered exactly once");
        }
        std::cout << "Iteration observer parity, counters, cancellation, exceptions and timing checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
