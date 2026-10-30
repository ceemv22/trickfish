#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/evaluation.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "MDP PV too long");
    if (!result.principal_variation.empty()) {
        require(result.best_move && *result.best_move == result.principal_variation.front(), "MDP root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal MDP PV");
        static_cast<void>(root.make_move(move));
    }
}

int main() {
    try {
        for (const auto fen : {
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
            "8/8/8/8/8/5kq1/8/7K b - - 0 1",
            "7k/8/5K1Q/8/8/8/8/8 b - - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            trickfish::RepetitionHistory history(root);
            for (const bool table : {false, true}) {
                for (const bool played : {false, true}) {
                    trickfish::SearchOptions baseline;
                    baseline.use_table = table;
                    require(!baseline.use_mate_distance, "MDP must default off");
                    auto enabled = baseline;
                    enabled.use_mate_distance = true;
                    const auto* active = played ? &history : nullptr;
                    const auto reference = trickfish::iterative_search(root, 3, baseline, {}, active);
                    const auto result = trickfish::iterative_search(root, 3, enabled, {}, active);
                    require(reference.score == result.score && result.completed_depth == 3 && !result.stopped &&
                        reference.mate_distance_cutoffs == 0, "MDP changed completed search score/depth");
                    verify_line(root, result);
                    const auto stopped = trickfish::iterative_search(root, 3, enabled, {0, {}, {}}, active);
                    require(stopped.stopped && stopped.completed_depth == 0 && stopped.best_move,
                        "MDP changed zero-node fallback");
                    require(root.to_fen() == fen && root.key() == key && history.size() == 1,
                        "MDP search changed root/history");
                }
            }
        }
        auto mate_in_one = trickfish::Position::from_fen("7k/8/5KQ1/8/8/8/8/8 w - - 0 1");
        trickfish::SearchOptions reference;
        reference.use_table = false;
        reference.use_pvs = false;
        reference.aspiration_window = 0;
        auto enabled = reference;
        enabled.use_mate_distance = true;
        const auto normal = trickfish::iterative_search(mate_in_one, 2, reference);
        const auto bounded = trickfish::iterative_search(mate_in_one, 2, enabled);
        require(normal.score == trickfish::mate_score - 1 && bounded.score == normal.score && bounded.nodes < normal.nodes,
            "MDP failed the bounded mate-in-one work regression");
        verify_line(mate_in_one, bounded);
        for (const auto fen : {
            "7k/6Q1/6K1/8/8/8/8/8 b - - 150 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 150 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto result = trickfish::iterative_search(root, 3, enabled);
            const auto baseline = trickfish::iterative_search(root, 3, reference);
            require(result.score == baseline.score && !result.best_move && result.mate_distance_cutoffs == 0,
                "MDP overrode terminal/draw precedence");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
