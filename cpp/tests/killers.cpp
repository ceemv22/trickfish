#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

trickfish::SearchResult run(trickfish::Position& position, int depth, bool killers,
    const trickfish::RepetitionHistory* history = nullptr, std::optional<std::uint64_t> limit = std::nullopt) {
    return trickfish::iterative_search(position, depth, true, limit, std::nullopt, {}, history,
        trickfish::MoveCountDrawPolicy::automatic_only, true, 25, killers);
}

void verify_line(trickfish::Position position, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "killer PV too long");
    if (result.best_move) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "killer root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(position);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "killer ordering produced illegal PV");
        const auto undo = position.make_move(move);
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
            auto position = trickfish::Position::from_fen(fen);
            const auto key = position.key();
            const auto reference = trickfish::search(position, 3, false, false, false);
            for (bool table : {false, true}) {
                const auto result = trickfish::search(position, 3, table, true, true);
                require(result.score == reference.score, "killer/full-window score mismatch");
                verify_line(position, result);
            }
            const auto iterative = run(position, 3, true);
            const auto repeated = run(position, 3, true);
            const auto disabled = run(position, 3, false);
            require(iterative.score == reference.score && disabled.score == reference.score,
                "iterative killer score mismatch");
            require(disabled.killer_cutoffs == 0 && disabled.killer_moves_searched == 0,
                "disabled ordering used killer state");
            require(iterative.nodes == repeated.nodes && iterative.best_move == repeated.best_move &&
                iterative.principal_variation == repeated.principal_variation &&
                iterative.killer_cutoffs == repeated.killer_cutoffs &&
                iterative.killer_moves_searched == repeated.killer_moves_searched,
                "killer state leaked between searches");
            verify_line(position, iterative);
            require(position.to_fen() == fen && position.key() == key, "killer search changed root");
        }
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        const auto activity = run(root, 3, true);
        require(activity.killer_cutoffs > 0 && activity.killer_moves_searched > 0,
            "killer storage/reuse paths were not exercised");
        trickfish::RepetitionHistory history(root);
        const auto plain = run(root, 2, false, &history);
        const auto ordered = run(root, 2, true, &history);
        require(plain.score == ordered.score && ordered.transposition_hits == 0, "history-mode killer parity mismatch");
        const auto first = run(root, 1, true, &history);
        const auto stopped = run(root, 3, true, &history, first.nodes + 3);
        require(stopped.stopped && stopped.completed_depth == 1 && stopped.score == first.score &&
            stopped.best_move == first.best_move, "killer interruption lost completed iteration");
        verify_line(root, stopped);
        require(root.to_fen() == fen && root.key() == key && history.size() == 1 && history.current_count() == 1,
            "killer interruption changed root/history");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
