#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

trickfish::SearchResult run(trickfish::Position& position, int depth, bool table, bool pvs, int window,
    const trickfish::RepetitionHistory* history = nullptr, std::function<bool()> stop = {}) {
    return trickfish::iterative_search(position, depth, table, std::nullopt, std::nullopt, stop, history,
        trickfish::MoveCountDrawPolicy::automatic_only, pvs, window);
}

void verify_line(trickfish::Position position, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "aspiration PV too long");
    if (result.best_move) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "aspiration root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(position);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal aspiration PV");
        const auto undo = position.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
            "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
            "4k3/8/8/8/8/8/8/R3K3 w - - 150 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto key = position.key();
            const auto reference = run(position, 3, false, false, 0);
            require(reference.aspiration_fail_low == 0 && reference.aspiration_fail_high == 0,
                "disabled aspiration recorded retries");
            for (bool table : {false, true}) {
                for (bool pvs : {false, true}) {
                    for (int window : {1, 25, 100001}) {
                        const auto result = run(position, 3, table, pvs, window);
                        require(result.score == reference.score && result.completed_depth == reference.completed_depth &&
                            !result.stopped, "aspiration/full-window score mismatch");
                        verify_line(position, result);
                    }
                }
            }
            require(position.to_fen() == fen && position.key() == key, "aspiration changed root");
        }
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        const auto exercised = run(root, 3, false, true, 1);
        require(exercised.aspiration_fail_low > 0 && exercised.aspiration_fail_high > 0,
            "both aspiration failure directions were not exercised");
        trickfish::RepetitionHistory history(root);
        for (bool table : {false, true}) {
            const auto reference = run(root, 2, table, true, 0, &history);
            const auto candidate = run(root, 2, table, true, 1, &history);
            require(candidate.score == reference.score && candidate.transposition_hits == 0,
                "history-aware aspiration mismatch");
            const auto first = run(root, 1, table, true, 1, &history);
            int root_visits = 0;
            const auto stopped = run(root, 2, table, true, 1, &history, [&] {
                if (root.key() == key) ++root_visits;
                return root_visits >= 3;
            });
            require(stopped.stopped && stopped.completed_depth == 1 && stopped.score == first.score &&
                stopped.best_move == first.best_move && stopped.aspiration_fail_low > 0 &&
                stopped.nodes > first.nodes, "interrupted aspiration retry replaced completed result");
            verify_line(root, stopped);
            require(root.to_fen() == fen && root.key() == key && history.size() == 1 && history.current_count() == 1,
                "aspiration retry interruption changed root/history");
        }
        for (int invalid : {-1, 100002}) {
            bool rejected = false;
            try { static_cast<void>(run(root, 2, true, true, invalid)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && root.to_fen() == fen && root.key() == key, "invalid aspiration window accepted");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
