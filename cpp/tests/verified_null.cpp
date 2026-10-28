#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "null PV too long");
    if (result.best_move && result.completed_depth > 0) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "null root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "null probe leaked synthetic PV move");
        const auto undo = root.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        for (const auto fen : {"r3k3/8/8/8/8/8/8/R3K3 w - - 0 1",
            "4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            for (bool table : {false, true}) {
                trickfish::SearchOptions options;
                options.use_table = table;
                const auto reference = trickfish::iterative_search(root, 4, options);
                require(reference.null_probes == 0 && reference.null_cutoffs == 0, "default search used null probes");
                options.use_null_move = true;
                const auto verified = trickfish::iterative_search(root, 4, options);
                require(verified.score == reference.score && !verified.stopped, "verified null score mismatch");
                verify_line(root, verified);
                trickfish::RepetitionHistory history(root);
                const auto historical = trickfish::iterative_search(root, 4, options, {}, &history);
                require(historical.score == reference.score && historical.transposition_hits == 0 &&
                    history.size() == 1 && history.current_count() == 1, "null probe polluted played history");
                require(root.to_fen() == fen && root.key() == key, "null search failed root restoration");
            }
        }
        auto root = trickfish::Position::from_fen("r3k3/8/8/8/8/8/8/R3K3 w - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::SearchOptions options;
        options.use_null_move = true;
        options.root_moves = {trickfish::Move(56, 0), trickfish::Move(60, 59)};
        const auto exercised = trickfish::iterative_search(root, 4, options);
        require(exercised.null_probes > 0 && exercised.null_verifications > 0 && exercised.null_cutoffs > 0,
            "null probe/verification/cutoff paths were not exercised");
        auto synthetic = root;
        const auto king_undo = synthetic.make_move(trickfish::Move(60, 59));
        const auto null_undo = synthetic.make_null_move();
        static_cast<void>(king_undo);
        static_cast<void>(null_undo);
        const auto synthetic_key = synthetic.key();
        trickfish::RepetitionHistory history(root);
        trickfish::SearchLimits limits;
        limits.stop_requested = [&] { return root.key() == synthetic_key; };
        const auto stopped = trickfish::iterative_search(root, 4, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == 3 && stopped.null_probes > 0 &&
            root.to_fen() == fen && root.key() == key && history.size() == 1,
            "interrupted synthetic null branch changed root/history or completed depth");
        verify_line(root, stopped);
        auto pawns = trickfish::Position::from_fen("4k3/8/8/8/8/8/P7/4K3 w - - 0 1");
        options.root_moves.clear();
        const auto pawn_guard = trickfish::iterative_search(pawns, 4, options);
        require(pawn_guard.null_probes == 0, "null probe bypassed pawn-only guard");
        auto clock = trickfish::Position::from_fen("r3k3/8/8/8/8/8/8/R3K3 w - - 149 1");
        const auto clock_guard = trickfish::iterative_search(clock, 4, options);
        require(clock_guard.null_probes == 0, "null probe bypassed move-count guard");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
