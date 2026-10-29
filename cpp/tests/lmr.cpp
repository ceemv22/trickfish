#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "LMR PV too long");
    if (result.best_move) {
        require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
            "LMR root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "LMR returned illegal PV");
        const auto undo = root.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::SearchOptions options;
        options.use_table = false;
        options.use_killers = false;
        options.use_history = false;
        options.use_continuation = false;
        const auto reference = trickfish::iterative_search(root, 2, options);
        require(reference.lmr_reductions == 0 && reference.lmr_researches == 0, "default search enabled LMR");
        options.use_lmr = true;
        const auto shallow = trickfish::iterative_search(root, 2, options);
        require(shallow.score == reference.score && shallow.lmr_reductions == 0, "LMR bypassed depth/root guards");
        trickfish::RepetitionHistory history(root);
        int depth = 4;
        auto active = trickfish::iterative_search(root, depth, options, {}, &history);
        if (active.lmr_reductions == 0) active = trickfish::iterative_search(root, ++depth, options, {}, &history);
        require(active.lmr_reductions > 0 && active.lmr_researches <= active.lmr_reductions && !active.stopped,
            "LMR path/counter mismatch");
        verify_line(root, active);
        const auto repeated = trickfish::iterative_search(root, depth, options, {}, &history);
        require(active.score == repeated.score && active.nodes == repeated.nodes && active.best_move == repeated.best_move &&
            active.principal_variation == repeated.principal_variation && active.lmr_reductions == repeated.lmr_reductions &&
            active.lmr_researches == repeated.lmr_researches, "LMR is not repeatable across fresh searches");
        trickfish::SearchLimits limits;
        limits.nodes = active.nodes - 1;
        const auto stopped = trickfish::iterative_search(root, depth, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == depth - 1 && stopped.lmr_reductions > 0 &&
            history.size() == 1 && history.current_count() == 1 && root.to_fen() == fen && root.key() == key,
            "LMR interruption failed state/history restoration or completed-depth fallback");
        verify_line(root, stopped);
        options.use_table = true;
        const auto cached = trickfish::iterative_search(root, 4, options);
        verify_line(root, cached);
        require(root.to_fen() == fen && root.key() == key, "LMR search changed caller root");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
