#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/evaluation_weights.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "rnbq1rk1/ppp2ppp/2np1n2/4p3/4P3/2NP1N2/PPP2PPP/R1BQK2R w KQ - 4 6",
            "4k3/8/8/8/8/8/4P3/4K3 b - - 0 1",
            "r3k2r/ppp2ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"}) {
            auto root = Position::from_fen(fen);
            const auto detail = evaluate_breakdown(root);
            const auto key = root.key();
            for (const EvaluationWeights weights : {EvaluationWeights{}, EvaluationWeights{0, 0, 0},
                    EvaluationWeights{200, 200, 200}, EvaluationWeights{73, 129, 87}}) {
                weights.validate();
                const int expected = detail.total() - detail.pawn_structure - detail.piece_activity - detail.king_safety +
                    detail.pawn_structure * weights.pawns / 100 + detail.piece_activity * weights.activity / 100 +
                    detail.king_safety * weights.king_safety / 100;
                require(weights.apply(root, detail.total()) == expected, "weighted breakdown arithmetic mismatch");
                SearchOptions options;
                options.eval_pawn_weight = weights.pawns;
                options.eval_activity_weight = weights.activity;
                options.eval_king_safety_weight = weights.king_safety;
                SearchLimits limits;
                limits.nodes = 0;
                const auto fallback = iterative_search(root, 3, options, limits);
                require(fallback.stopped && fallback.completed_depth == 0 &&
                    fallback.score == (root.side_to_move() == Color::white ? expected : -expected), "fallback ignored evaluation weights");
                const auto plain = iterative_search(root, 2, options);
                options.use_pawn_cache = true;
                const auto cached = iterative_search(root, 2, options);
                require(plain.score == cached.score && plain.nodes == cached.nodes && plain.principal_variation == cached.principal_variation,
                    "weighted pawn cache changed search trace");
                options.use_table = false;
                const auto reference = iterative_search(root, 2, options);
                require(reference.score == cached.score, "weighted TT changed score");
                options.use_endgame_scaling = true;
                const auto scaled = iterative_search(root, 2, options);
                require(scaled.best_move.has_value(), "weighted scaling lost root move");
                require(root.to_fen() == fen && root.key() == key, "weighted search changed root");
            }
        }
        auto root = Position::from_fen("4k3/8/8/8/8/8/4P3/4K3 b - - 0 1");
        SearchOptions invalid;
        for (const int value : {-1, 201}) {
            for (int SearchOptions::*member : {&SearchOptions::eval_pawn_weight, &SearchOptions::eval_activity_weight,
                    &SearchOptions::eval_king_safety_weight}) {
                invalid = {};
                invalid.*member = value;
                bool rejected = false;
                try { static_cast<void>(iterative_search(root, 1, invalid)); }
                catch (const std::invalid_argument&) { rejected = true; }
                require(rejected, "invalid evaluation weight accepted");
            }
        }
        for (const auto fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 150 1", "4k3/8/8/8/8/8/8/4K3 w - - 0 1"}) {
            auto terminal = Position::from_fen(fen);
            const auto standard = iterative_search(terminal, 2);
            SearchOptions options;
            options.eval_pawn_weight = options.eval_activity_weight = options.eval_king_safety_weight = 0;
            const auto result = iterative_search(terminal, 2, options);
            require(result.score == standard.score && result.best_move == standard.best_move, "weights overrode terminal result");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
