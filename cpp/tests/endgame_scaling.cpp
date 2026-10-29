#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/evaluation.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_scale(std::string_view fen, int factor) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    require(trickfish::endgame_scale(position) == factor, "endgame material/color boundary mismatch");
    require(trickfish::evaluate_scaled_static(position) == trickfish::evaluate_static(position) * factor / 256,
        "scaled static score mismatch");
    require(position.to_fen() == fen && position.key() == key, "static scaling changed position");
}

int main() {
    try {
        verify_scale("2b1k3/7p/8/8/8/8/PP6/2B1K3 w - - 0 1", 128);
        verify_scale("2b1k3/7p/8/8/8/8/PP6/2B1K3 b - - 0 1", 128);
        verify_scale("4kb2/7p/8/8/8/8/PP6/2B1K3 w - - 0 1", 256);
        verify_scale("2b1kb2/7p/8/8/8/8/PP6/2B1K3 w - - 0 1", 256);
        verify_scale("2b1k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 256);
        verify_scale("4k3/7p/8/8/8/8/PP6/2B1K3 w - - 0 1", 256);
        verify_scale("2b1k3/7p/8/8/8/8/PP6/1NB1K3 w - - 0 1", 256);
        verify_scale("2b1k2r/7p/8/8/8/8/PP6/2B1K3 w - - 0 1", 256);
        verify_scale("2b1k3/7p/8/8/8/8/PP6/2BQK3 w - - 0 1", 256);
        trickfish::SearchOptions options;
        require(!options.use_endgame_scaling, "endgame scaling must default off");
        options.use_endgame_scaling = true;
        for (const auto side : {"w", "b"}) {
            const auto fen = std::string("2b1k3/7p/8/8/8/8/PP6/2B1K3 ") + side + " - - 0 1";
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            const int raw = trickfish::evaluate_static(root);
            const int sign = root.side_to_move() == trickfish::Color::white ? 1 : -1;
            const auto fallback = trickfish::iterative_search(root, 2, options, {0, {}, {}});
            require(fallback.stopped && fallback.completed_depth == 0 && fallback.best_move &&
                fallback.score == raw / 2 * sign, "scaled interrupted fallback mismatch");
            auto baseline = options;
            baseline.use_endgame_scaling = false;
            require(trickfish::iterative_search(root, 2, baseline, {0, {}, {}}).score == raw * sign,
                "default fallback evaluation changed");
            const auto with_table = trickfish::iterative_search(root, 2, options);
            auto reference = options;
            reference.use_table = false;
            const auto without_table = trickfish::iterative_search(root, 2, reference);
            require(with_table.completed_depth == 2 && with_table.score == without_table.score,
                "scaled search TT/reference score mismatch");
            require(with_table.best_move && !with_table.principal_variation.empty() &&
                *with_table.best_move == with_table.principal_variation.front(), "scaled root/PV mismatch");
            auto replay = root;
            for (const auto& move : with_table.principal_variation) {
                const auto legal = trickfish::generate_legal_moves(replay);
                require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal scaled PV");
                static_cast<void>(replay.make_move(move));
            }
            reference.use_correction = true;
            require(trickfish::iterative_search(root, 2, reference).completed_depth == 2,
                "scaled correction search did not complete");
            require(root.to_fen() == fen && root.key() == key && trickfish::evaluate_static(root) == raw,
                "scaled search changed root/reference evaluation");
        }
        auto capture = trickfish::Position::from_fen("4k3/8/8/8/8/8/P2b4/1B2K3 w - - 0 1");
        const auto fen = capture.to_fen();
        const auto key = capture.key();
        require(trickfish::endgame_scale(capture) == 128, "pre-capture scale mismatch");
        const trickfish::Move move(60, 51);
        const auto undo = capture.make_move(move);
        require(trickfish::endgame_scale(capture) == 256, "bishop capture did not remove scale");
        capture.unmake_move(move, undo);
        require(trickfish::endgame_scale(capture) == 128 && capture.to_fen() == fen && capture.key() == key,
            "capture undo did not restore scaling state");
        auto clock_draw = trickfish::Position::from_fen("2b1k3/7p/8/8/8/8/PP6/2B1K3 w - - 150 1");
        const auto draw_result = trickfish::iterative_search(clock_draw, 2, options, {0, {}, {}});
        require(draw_result.score == 0 && !draw_result.best_move, "scaling changed move-count draw fallback");
        auto mate = trickfish::Position::from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1");
        const auto terminal = trickfish::iterative_search(mate, 2, options, {0, {}, {}});
        require(terminal.score == -trickfish::mate_score && !terminal.best_move, "scaling changed mate fallback");
        auto dead = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1");
        require(trickfish::iterative_search(dead, 2, options).score == 0, "scaling changed insufficient draw");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
