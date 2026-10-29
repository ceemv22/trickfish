#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "futility PV too long");
    require(result.best_move && !result.principal_variation.empty() &&
        result.principal_variation.front() == *result.best_move, "futility root/PV mismatch");
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "futility returned illegal PV");
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
        options.futility_margin = 0;
        const auto reference = trickfish::iterative_search(root, 3, options);
        require(reference.futility_pruned == 0, "default search enabled futility");
        options.use_futility = true;
        const auto shallow = trickfish::iterative_search(root, 1, options);
        require(shallow.futility_pruned == 0, "futility bypassed root guard");
        trickfish::RepetitionHistory history(root);
        const auto active = trickfish::iterative_search(root, 3, options, {}, &history);
        require(active.futility_pruned > 0 && !active.stopped, "futility skip path was not exercised");
        verify_line(root, active);
        const auto repeat = trickfish::iterative_search(root, 3, options, {}, &history);
        require(active.score == repeat.score && active.nodes == repeat.nodes && active.best_move == repeat.best_move &&
            active.principal_variation == repeat.principal_variation && active.futility_pruned == repeat.futility_pruned,
            "futility is not deterministic across searches");
        trickfish::SearchLimits limits;
        limits.nodes = active.nodes - 1;
        const auto stopped = trickfish::iterative_search(root, 3, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == 2 && root.to_fen() == fen && root.key() == key &&
            history.size() == 1 && history.current_count() == 1, "futility interruption changed root/history");
        verify_line(root, stopped);
        auto mate = trickfish::Position::from_fen("7k/8/5KQ1/8/8/8/8/8 w - - 0 1");
        const auto mating = trickfish::iterative_search(mate, 2, options);
        require(mating.score == 99999 && mating.best_move, "futility lost immediate mate");
        const auto undo = mate.make_move(*mating.best_move);
        static_cast<void>(undo);
        require(mate.in_check(mate.side_to_move()) && trickfish::generate_legal_moves(mate).empty(), "futility selected non-mating move");
        for (int margin : {-1, 10001}) {
            options.futility_margin = margin;
            bool rejected = false;
            try { static_cast<void>(trickfish::iterative_search(root, 2, options)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && root.to_fen() == fen && root.key() == key, "invalid futility margin accepted or mutated root");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
