#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/search.hpp"
#include "trickfish/game_status.hpp"

void verify(std::string_view fen, int depth, int score, std::string_view move) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    const auto result = trickfish::search(position, depth);
    if (result.score != score || result.nodes == 0) {
        throw std::runtime_error("search score mismatch");
    }
    if (!move.empty() && (!result.best_move || result.best_move->to_uci() != move)) {
        throw std::runtime_error("search move mismatch");
    }
    if (score == 99999) {
        if (!result.best_move) {
            throw std::runtime_error("mate search returned no move");
        }
        const auto undo = position.make_move(*result.best_move);
        if (trickfish::game_status(position) != trickfish::GameStatus::checkmate) {
            throw std::runtime_error("mate search selected a non-mating move");
        }
        position.unmake_move(*result.best_move, undo);
    }
    if (position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("search changed root position");
    }
}

int main() {
    try {
        verify("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1", 1, 500, "a1a2");
        verify("r3k3/Q7/8/8/8/8/8/4K3 b - - 0 1", 1, 500, "a8a7");
        const auto mate_fen = "7k/8/5KQ1/8/8/8/8/8 w - - 0 1";
        verify(mate_fen, 1, 99999, "");
        verify(mate_fen, 3, 99999, "");
        for (const auto fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto result = trickfish::search(position, 2);
            if (result.best_move || result.score != (position.in_check(position.side_to_move()) ? -100000 : 0)) {
                throw std::runtime_error("terminal root mismatch");
            }
        }
        verify("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 2, 0, "");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
