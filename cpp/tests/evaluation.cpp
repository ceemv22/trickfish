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

void verify_rook_files(std::string_view fen, int rook_files, int expected) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    if (trickfish::evaluate_rook_files(position) != rook_files ||
        trickfish::evaluate_static(position) != expected || trickfish::evaluate(position) != expected ||
        position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("rook-file evaluation mismatch");
    }
}

int main() {
    try {
        verify_rook_files("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1", 20, 620);
        verify_rook_files("4k3/p7/8/8/8/8/1P6/R3K3 w - - 0 1", 10, 510);
        verify_rook_files("4k3/p7/8/8/8/8/P7/R3K3 w - - 0 1", 0, 500);
        verify_rook_files("4k3/8/8/8/8/8/P7/R3K3 w - - 0 1", 10, 610);
        verify_rook_files("r3k3/1p6/8/8/8/8/8/4K3 w - - 0 1", -20, -620);
        verify_rook_files("r3k3/1p6/8/8/8/8/1P6/R3K3 w - - 0 1", 0, 0);
        verify_rook_files("4k3/8/8/8/8/R7/1P6/R3K3 w - - 0 1", 40, 1140);
        verify_rook_files("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", 0, 500);

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
        auto rook_position = trickfish::Position::from_fen("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1");
        const auto rook_search = trickfish::search(rook_position, 1);
        if (rook_search.score != 620 || !rook_search.best_move) {
            throw std::runtime_error("search did not use rook-file term");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
