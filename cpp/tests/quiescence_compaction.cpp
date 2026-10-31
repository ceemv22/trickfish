#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void same_trace(const trickfish::SearchResult& compact, const trickfish::SearchResult& reference) {
    require(compact.score == reference.score && compact.best_move == reference.best_move &&
        compact.principal_variation == reference.principal_variation && compact.completed_depth == reference.completed_depth &&
        compact.nodes == reference.nodes && compact.stopped == reference.stopped &&
        compact.transposition_hits == reference.transposition_hits, "quiescence changed search trace");
    require(compact.history_rewards == reference.history_rewards && compact.history_penalties == reference.history_penalties &&
        compact.continuation_updates == reference.continuation_updates && compact.exchange_evaluations == reference.exchange_evaluations &&
        compact.pawn_cache_hits == reference.pawn_cache_hits && compact.pawn_cache_misses == reference.pawn_cache_misses,
        "quiescence changed non-ordering heuristic work");
    require(reference.quiescence_filtered_quiet_moves == 0 &&
        compact.quiescence_ordering_calls <= reference.quiescence_ordering_calls &&
        compact.quiescence_ordered_moves <= reference.quiescence_ordered_moves,
        "quiescence did not preserve reference ordering-work bounds");
}

trickfish::SearchResult verify(trickfish::Position& root, int depth, trickfish::SearchOptions options,
    const trickfish::SearchLimits& limits = {}, const trickfish::RepetitionHistory* history = nullptr) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    const auto phase = root.phase_units();
    const auto history_size = history != nullptr ? history->size() : 0;
    const auto history_count = history != nullptr ? history->current_count() : 0;
    options.use_compact_quiescence = true;
    const auto compact = trickfish::iterative_search(root, depth, options, limits, history);
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && root.phase_units() == phase,
        "compact quiescence changed root");
    options.use_compact_quiescence = false;
    const auto reference = trickfish::iterative_search(root, depth, options, limits, history);
    same_trace(compact, reference);
    auto replay = root;
    for (const auto& move : compact.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(replay);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal compact quiescence PV");
        static_cast<void>(replay.make_move(move));
    }
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && root.phase_units() == phase,
        "reference quiescence changed root");
    if (history != nullptr) require(history->size() == history_size && history->current_count() == history_count,
        "quiescence changed supplied history");
    return compact;
}

int main() {
    try {
        trickfish::MoveList list;
        const trickfish::Move first(0, 8), replacement(1, 9);
        list.push(first);
        list.push(trickfish::Move(2, 10));
        list.truncate(1);
        list.push(replacement);
        require(list.size() == 2 && list[0] == first && list[1] == replacement, "truncation lost prefix or push overwrote wrong slot");
        bool rejected = false;
        try { list.truncate(3); } catch (const std::out_of_range&) { rejected = true; }
        require(rejected && list.size() == 2 && list[1] == replacement, "truncation growth changed list");
        list.truncate(0);
        require(list.empty() && list.begin() == list.end(), "empty truncation retained visible moves");
        for (const auto fen : {
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1",
                "4k3/4p3/8/3P4/8/8/8/4K3 b - - 0 1",
                "4k3/P7/8/8/8/8/8/4K3 b - - 0 1",
                "1r2k3/P7/8/8/8/8/8/4K3 b - - 0 1",
                "4k3/8/8/8/8/8/R7/7K w - - 0 1",
                "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
                "r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
                "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
                "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
                "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
                "4k3/8/8/8/8/8/R7/7K w - - 150 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            for (int mode = 0; mode < 7; ++mode) {
                trickfish::SearchOptions options;
                if (mode == 1) options.use_table = false;
                if (mode == 2) { options.use_pawn_cache = true; options.use_endgame_scaling = true; options.use_mate_distance = true; }
                if (mode == 3) { options.use_exchange_ordering = true; options.use_cached_ordering = false; }
                if (mode == 4) options.use_correction = true;
                if (mode == 5) {
                    options.use_null_move = true; options.use_lmr = true; options.use_futility = true;
                    options.use_razoring = true; options.use_check_extensions = true;
                }
                if (mode == 6) {
                    options.use_pvs = false; options.aspiration_window = 0; options.use_killers = false;
                    options.use_history = false; options.use_continuation = false;
                }
                verify(root, std::string_view(fen).starts_with("rnbq") && mode == 0 ? 3 : 2, options);
            }
            trickfish::RepetitionHistory history(root);
            verify(root, 2, {}, {}, &history);
        }
        auto opening = trickfish::Position::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto work = verify(opening, 1, {});
        require(work.quiescence_filtered_quiet_moves > 0, "opening did not exercise quiet filtering");
        for (const std::uint64_t limit : {0ULL, 1ULL, 19ULL, 200ULL}) {
            trickfish::SearchLimits limits;
            limits.nodes = limit;
            verify(opening, 4, {}, limits);
        }
        trickfish::SearchLimits stop;
        stop.stop_requested = [] { return true; };
        verify(opening, 4, {}, stop);
        trickfish::SearchLimits expired;
        expired.deadline = std::chrono::steady_clock::time_point::min();
        verify(opening, 4, {}, expired);
        trickfish::RepetitionHistory repeated(opening);
        repeated.push(opening);
        repeated.push(opening);
        require(verify(opening, 3, {}, {}, &repeated).score == 0, "quiescence changed repetition adjudication");
        std::cout << "opening_filtered_quiet_moves " << work.quiescence_filtered_quiet_moves << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
