#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position position, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "PV too long");
    if (result.best_move && result.completed_depth != 0) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "PVS root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(position);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "PVS returned illegal PV");
        const auto undo = position.make_move(move);
        static_cast<void>(undo);
    }
}

void compare(std::string_view fen) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    for (int depth = 1; depth <= 3; ++depth) {
        const auto reference = trickfish::search(position, depth, false, false);
        for (bool use_table : {false, true}) {
            const auto pvs = trickfish::search(position, depth, use_table, true);
            const auto iterative = trickfish::iterative_search(position, depth, use_table,
                std::nullopt, std::nullopt, {}, nullptr, trickfish::MoveCountDrawPolicy::automatic_only, true);
            const auto iterative_reference = trickfish::iterative_search(position, depth, use_table,
                std::nullopt, std::nullopt, {}, nullptr, trickfish::MoveCountDrawPolicy::automatic_only, false);
            for (const auto* result : {&reference, &pvs, &iterative, &iterative_reference}) {
                require(result->score == reference.score && !result->stopped, "PVS/full-window score mismatch");
                verify_line(position, *result);
            }
        }
        trickfish::TranspositionTable table(1);
        const auto collided = trickfish::search(position, depth, table, true);
        require(collided.score == reference.score, "PVS collision-table score mismatch");
        verify_line(position, collided);
        require(position.to_fen() == fen && position.key() == key, "PVS did not restore position");
    }
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
            "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
            "4k3/8/8/8/8/8/8/2B1K3 w - - 0 1"}) {
            compare(fen);
        }
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto pvs_activity = trickfish::search(root, 1, false, true);
        const auto full_window_activity = trickfish::search(root, 1, false, false);
        require(pvs_activity.pvs_probes > 0 && pvs_activity.pvs_researches > 0 &&
            full_window_activity.pvs_probes == 0 && full_window_activity.pvs_researches == 0,
            "PVS probes/re-searches were not exercised or reference used PVS");
        const auto root_fen = root.to_fen();
        const auto root_key = root.key();
        trickfish::RepetitionHistory history(root);
        for (bool use_pvs : {false, true}) {
            const auto plain = trickfish::iterative_search(root, 2, false,
                std::nullopt, std::nullopt, {}, nullptr, trickfish::MoveCountDrawPolicy::automatic_only, use_pvs);
            const auto history_result = trickfish::iterative_search(root, 2, true,
                std::nullopt, std::nullopt, {}, &history, trickfish::MoveCountDrawPolicy::automatic_only, use_pvs);
            require(plain.score == history_result.score && history_result.transposition_hits == 0,
                "PVS history-mode parity mismatch");
            const auto first = trickfish::iterative_search(root, 1, true,
                std::nullopt, std::nullopt, {}, &history, trickfish::MoveCountDrawPolicy::automatic_only, use_pvs);
            const auto interrupted = trickfish::iterative_search(root, 3, true,
                first.nodes + 3, std::nullopt, {}, &history, trickfish::MoveCountDrawPolicy::automatic_only, use_pvs);
            require(interrupted.stopped && interrupted.completed_depth == 1 &&
                interrupted.score == first.score && interrupted.best_move == first.best_move &&
                interrupted.nodes == first.nodes + 3, "PVS interrupted result lost completed iteration");
            verify_line(root, interrupted);
            require(root.to_fen() == root_fen && root.key() == root_key && history.size() == 1 &&
                history.current_count() == 1, "PVS interruption changed root/history");
        }
        for (const auto fen : {"4k3/8/8/8/8/8/P7/R3K3 w - - 99 1",
            "4k3/8/8/8/8/8/8/R3K3 w - - 150 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto reference = trickfish::iterative_search(position, 2, true,
                std::nullopt, std::nullopt, {}, nullptr, trickfish::MoveCountDrawPolicy::claim_fifty_moves, false);
            const auto pvs = trickfish::iterative_search(position, 2, true,
                std::nullopt, std::nullopt, {}, nullptr, trickfish::MoveCountDrawPolicy::claim_fifty_moves, true);
            require(reference.score == pvs.score && reference.best_move.has_value() == pvs.best_move.has_value(),
                "PVS draw-policy mismatch");
            verify_line(position, pvs);
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
