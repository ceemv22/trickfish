#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

trickfish::SearchResult run(trickfish::Position& root, int depth, bool enabled, bool table, bool optimized,
    const trickfish::RepetitionHistory* history = nullptr, std::optional<std::uint64_t> nodes = std::nullopt) {
    trickfish::SearchOptions options;
    options.use_table = table;
    options.use_pvs = optimized;
    options.use_killers = optimized;
    options.aspiration_window = optimized ? 25 : 0;
    options.use_history = enabled;
    trickfish::SearchLimits limits;
    limits.nodes = nodes;
    return trickfish::iterative_search(root, depth, options, limits, history);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "history PV too long");
    if (result.best_move) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "history root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "history ordering returned illegal PV");
        const auto undo = root.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/ppp2ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/R3K2R w KQkq - 0 1",
            "r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            const auto reference = run(root, 3, false, false, false);
            require(reference.history_rewards == 0 && reference.history_penalties == 0 &&
                reference.history_moves_searched == 0, "disabled history touched statistics");
            for (bool table : {false, true}) {
                for (bool optimized : {false, true}) {
                    const auto result = run(root, 3, true, table, optimized);
                    require(result.score == reference.score && !result.stopped, "quiet-history score parity mismatch");
                    verify_line(root, result);
                }
            }
            require(root.to_fen() == fen && root.key() == key, "quiet-history search changed root");
        }
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        const auto first = run(root, 3, true, false, false);
        const auto second = run(root, 3, true, false, false);
        require(first.history_rewards > 0 && first.history_penalties > 0 && first.history_moves_searched > 0,
            "history reward/penalty/reuse paths were not exercised");
        require(first.nodes == second.nodes && first.best_move == second.best_move &&
            first.principal_variation == second.principal_variation && first.history_rewards == second.history_rewards &&
            first.history_penalties == second.history_penalties && first.history_moves_searched == second.history_moves_searched,
            "history state leaked between searches");
        trickfish::RepetitionHistory history(root);
        const auto reference = run(root, 2, false, true, true, &history);
        const auto ordered = run(root, 2, true, true, true, &history);
        require(reference.score == ordered.score && ordered.transposition_hits == 0, "repetition/history ordering mismatch");
        const auto completed = run(root, 1, true, true, true, &history);
        const auto stopped = run(root, 3, true, true, true, &history, completed.nodes + 3);
        require(stopped.stopped && stopped.completed_depth == 1 && stopped.score == completed.score &&
            stopped.best_move == completed.best_move, "quiet-history interruption lost completed iteration");
        verify_line(root, stopped);
        require(root.to_fen() == fen && root.key() == key && history.size() == 1 && history.current_count() == 1,
            "quiet-history interruption changed root/history");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
