#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        auto root = trickfish::Position::from_fen("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::SearchOptions options;
        options.root_moves = {trickfish::Move(60, 59)};
        const auto restricted = trickfish::iterative_search(root, 2, options);
        const auto full = trickfish::iterative_search(root, 2);
        require(restricted.best_move == options.root_moves[0] && !restricted.principal_variation.empty() &&
            restricted.principal_variation.front() == options.root_moves[0] && restricted.transposition_hits == 0 &&
            restricted.score < full.score, "restricted root leaked excluded winning move or TT score");
        trickfish::SearchLimits limits;
        limits.nodes = 0;
        const auto fallback = trickfish::iterative_search(root, 2, options, limits);
        require(fallback.stopped && fallback.completed_depth == 0 && fallback.nodes == 0 &&
            fallback.best_move == options.root_moves[0], "restricted fallback escaped allowed root moves");
        options.root_moves.push_back(trickfish::Move(56, 48));
        const auto subset = trickfish::iterative_search(root, 2, options);
        require(subset.score == full.score && subset.best_move == trickfish::Move(56, 48), "root subset missed best allowed move");
        options.root_moves = {trickfish::Move(56, 48), trickfish::Move(56, 48)};
        for (int invalid = 0; invalid < 2; ++invalid) {
            bool rejected = false;
            try { static_cast<void>(trickfish::iterative_search(root, 1, options)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected, "illegal or duplicate root moves accepted");
            options.root_moves = {trickfish::Move(56, 0)};
        }
        require(root.to_fen() == fen && root.key() == key, "root restriction mutated caller position");
        auto promotion = trickfish::Position::from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1");
        options.root_moves = {trickfish::Move(8, 0, 'n')};
        trickfish::RepetitionHistory history(promotion);
        const auto promoted = trickfish::iterative_search(promotion, 2, options, {}, &history);
        require(promoted.best_move == options.root_moves[0] && promoted.score == 0 &&
            promoted.transposition_hits == 0 && history.size() == 1, "restricted underpromotion/history mismatch");
        auto initial = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        options.root_moves.clear();
        options.use_table = false;
        const auto reference = trickfish::iterative_search(initial, 2, options);
        const auto legal = trickfish::generate_legal_moves(initial);
        options.root_moves.assign(legal.begin(), legal.end());
        const auto all = trickfish::iterative_search(initial, 2, options);
        require(all.score == reference.score && all.transposition_hits == 0, "all-legal restriction changed score");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
