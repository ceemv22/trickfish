#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/evaluation.hpp"
#include "trickfish/search.hpp"

void verify(std::string_view fen, int material, int positional, int final_score) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    if (trickfish::evaluate_material(position) != material ||
        trickfish::evaluate_bishop_pair(position) != positional ||
        trickfish::evaluate_static(position) != material + positional ||
        trickfish::evaluate(position) != final_score || position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("bishop-pair evaluation or position restoration mismatch");
    }
    const int expected_side = position.side_to_move() == trickfish::Color::white ? final_score : -final_score;
    if (trickfish::evaluate_for_side_to_move(position) != expected_side) {
        throw std::runtime_error("bishop-pair score perspective mismatch");
    }
}

int main() {
    try {
        verify("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1", 660, 30, 690);
        verify("4k3/8/8/8/8/8/8/2B1KB2 b - - 0 1", 660, 30, 690);
        verify("2b1kb2/8/8/8/8/8/8/4K3 w - - 0 1", -660, -30, -690);
        verify("2b1kb2/8/8/8/8/8/8/2B1KB2 w - - 0 1", 0, 0, 0);
        verify("4k3/8/8/8/8/8/1B6/2B1KB2 w - - 0 1", 990, 30, 1020);
        verify("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 330, 0, 0);
        auto position = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1");
        const auto result = trickfish::search(position, 1);
        if (result.score != 690 || !result.best_move) {
            throw std::runtime_error("search did not use static positional term");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
