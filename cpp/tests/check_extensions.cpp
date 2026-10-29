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
        auto root = trickfish::Position::from_fen("7k/8/5K1Q/8/8/8/8/8 b - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::SearchOptions options;
        const auto baseline = trickfish::iterative_search(root, 1, options);
        require(baseline.check_extensions == 0 && baseline.score > -99872 &&
            baseline.principal_variation.size() == 1, "default search unexpectedly extended checked root");
        options.use_check_extensions = true;
        options.check_extension_limit = 0;
        const auto disabled = trickfish::iterative_search(root, 1, options);
        require(disabled.score == baseline.score && disabled.check_extensions == 0, "zero extension budget was ignored");
        options.check_extension_limit = 1;
        const auto active = trickfish::iterative_search(root, 1, options);
        require(active.completed_depth == 1 && active.score == -99998 && active.check_extensions == 1 &&
            active.transposition_hits == 0 && active.principal_variation.size() == 2,
            "checked-root extension did not expose forced mate with correct budget/depth");
        auto replay = root;
        for (const auto& move : active.principal_variation) {
            const auto legal = trickfish::generate_legal_moves(replay);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "extended PV is illegal");
            const auto undo = replay.make_move(move);
            static_cast<void>(undo);
        }
        require(replay.in_check(replay.side_to_move()) && trickfish::generate_legal_moves(replay).empty(),
            "extended horizon fixture PV did not end in mate");
        trickfish::RepetitionHistory history(root);
        trickfish::SearchLimits limits;
        limits.nodes = active.nodes - 1;
        const auto stopped = trickfish::iterative_search(root, 1, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == 0 && stopped.best_move && stopped.check_extensions > 0 &&
            root.to_fen() == fen && root.key() == key && history.size() == 1 && history.current_count() == 1,
            "extension interruption failed root/history restoration");
        options.check_extension_limit = 4;
        const auto capped = trickfish::iterative_search(root, 1, options);
        require(capped.score == active.score && capped.principal_variation.size() <= 5,
            "bounded extension horizon mismatch");
        auto mate = trickfish::Position::from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1");
        const auto terminal = trickfish::iterative_search(mate, 2, options);
        require(terminal.score == -100000 && !terminal.best_move && terminal.check_extensions == 0,
            "terminal mate was unnecessarily extended");
        for (int invalid : {-1, 5}) {
            options.check_extension_limit = invalid;
            bool rejected = false;
            try { static_cast<void>(trickfish::iterative_search(root, 1, options)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && root.to_fen() == fen && root.key() == key, "invalid extension limit mutated root");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
