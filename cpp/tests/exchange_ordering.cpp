#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/exchange.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "exchange PV too long");
    if (result.best_move && result.completed_depth > 0) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "exchange root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal exchange-order PV");
        const auto undo = root.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        for (const auto fen : {"4k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1", "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            for (bool table : {false, true}) {
                trickfish::SearchOptions options;
                options.use_table = table;
                const auto reference = trickfish::iterative_search(root, 2, options);
                require(reference.exchange_evaluations == 0 && reference.exchange_nodes == 0,
                    "default search unexpectedly evaluated exchanges");
                options.use_exchange_ordering = true;
                const auto ordered = trickfish::iterative_search(root, 2, options);
                require(ordered.score == reference.score && ordered.exchange_evaluations > 0 &&
                    ordered.exchange_nodes > 0, "exchange ordering score/work mismatch");
                verify_line(root, ordered);
                trickfish::RepetitionHistory history(root);
                const auto historical = trickfish::iterative_search(root, 2, options, {}, &history);
                require(historical.score == ordered.score && historical.transposition_hits == 0 && history.size() == 1,
                    "exchange ordering history-mode mismatch");
                require(root.to_fen() == fen && root.key() == key, "exchange ordering changed root");
            }
        }
        auto root = trickfish::Position::from_fen("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::RepetitionHistory history(root);
        trickfish::SearchOptions options;
        options.use_exchange_ordering = true;
        trickfish::SearchLimits limits;
        int checks = 0;
        limits.stop_requested = [&] { return ++checks >= 3; };
        const auto stopped = trickfish::iterative_search(root, 2, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == 0 && stopped.best_move && checks == 3 &&
            stopped.exchange_evaluations == 0 && root.to_fen() == fen && root.key() == key && history.size() == 1,
            "interrupted exchange work changed root/history or committed incomplete search");
        struct Interrupted {};
        checks = 0;
        bool interrupted = false;
        try {
            static_cast<void>(trickfish::analyze_exchange(root, trickfish::Move(56, 48), false, [&] {
                if (++checks == 2) throw Interrupted{};
            }));
        } catch (const Interrupted&) { interrupted = true; }
        require(interrupted && root.to_fen() == fen && root.key() == key, "exchange checkpoint failed root preservation");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
