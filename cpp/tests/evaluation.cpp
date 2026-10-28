#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/evaluation.hpp"
#include "trickfish/search.hpp"

void verify(std::string_view fen, int material, int positional, int static_score, int final_score) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    if (trickfish::evaluate_material(position) != material ||
        trickfish::evaluate_bishop_pair(position) != positional ||
        trickfish::evaluate_static(position) != static_score ||
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

void verify_pawns(std::string_view fen, int phase, int pawns, int total, int final_score) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    const auto detail = trickfish::evaluate_breakdown(position);
    if (trickfish::game_phase(position) != phase || detail.phase != phase ||
        trickfish::evaluate_pawn_structure(position) != pawns || detail.pawn_structure != pawns ||
        detail.total() != total || trickfish::evaluate_static(position) != total ||
        trickfish::evaluate(position) != final_score || position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("phase/pawn breakdown or terminal precedence mismatch");
    }
}

void verify_activity(std::string_view fen, int piece_activity, int king_safety, int king_activity, int total) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    const auto detail = trickfish::evaluate_breakdown(position);
    if (detail.piece_activity != piece_activity || detail.king_safety != king_safety ||
        detail.king_activity != king_activity || detail.total() != total ||
        trickfish::evaluate_piece_activity(position) != piece_activity ||
        trickfish::evaluate_king_safety(position) != king_safety ||
        trickfish::evaluate_king_activity(position) != king_activity ||
        trickfish::evaluate(position) != total || position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("activity/king evaluation or state restoration mismatch");
    }
}

int main() {
    try {
        verify_activity("n6k/8/8/8/3N4/8/8/4K3 w - - 0 1", 24, 0, 5, 29);
        verify_activity("k6b/8/8/8/3B4/8/P7/4K3 w - - 0 1", 12, 0, 5, 113);
        verify_activity("k7/8/8/8/3K4/8/P7/8 w - - 0 1", 0, 0, 12, 108);
        verify_activity("k7/8/8/8/3K4/8/P7/1Q6 w - - 0 1", 0, 0, 0, 996);
        verify_activity("1q2k3/8/8/8/8/8/5PPP/1Q4K1 w - - 0 1", 0, 14, 0, 338);
        verify_activity("1q2k3/8/8/8/8/8/PPP5/1QK5 w - - 0 1", 0, 12, 0, 336);
        verify_activity("1q2k3/8/8/8/8/8/3PPP2/1Q2K3 w - - 0 1", 12, 8, 0, 344);
        verify_activity("4k3/R6p/8/8/8/8/8/4K3 w - - 0 1", 20, 0, 0, 444);
        verify_activity("4k3/R7/8/8/8/8/8/4K3 w - - 0 1", 0, 0, 0, 500);
        verify_activity("4k3/8/8/8/8/8/5PPP/6KN w - - 0 1", 0, 1, -4, 641);
        verify_pawns("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 24, 0, 0, 0);
        verify_pawns("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", 0, -4, 96, 96);
        verify_pawns("4k3/8/8/P7/8/8/8/4K3 w - - 0 1", 0, 26, 141, 141);
        verify_pawns("4k3/8/8/8/8/8/PP6/4K3 w - - 0 1", 0, 16, 216, 216);
        verify_pawns("4k3/8/8/8/8/P7/P7/4K3 w - - 0 1", 0, -13, 192, 192);
        verify_pawns("4k3/p7/8/8/8/8/P7/4K3 w - - 0 1", 0, 0, 0, 0);
        verify_pawns("4k3/8/1p6/8/P7/8/8/4K3 w - - 0 1", 0, 0, 5, 5);
        verify_pawns("4k3/8/8/P7/8/1p6/8/4K3 w - - 0 1", 0, -10, -15, -15);
        verify_pawns("4k3/8/8/P7/8/8/8/1Q2K3 w - - 0 1", 4, 25, 1040, 1040);
        verify_pawns("3qk3/8/8/P7/8/8/8/3QK3 w - - 0 1", 8, 24, 139, 139);
        verify_pawns("rnbqkbnr/pppppppp/8/8/8/8/QQPPPPPP/RNBQKBNR w KQkq - 0 1", 24, -8, 1592, 1592);
        verify_pawns("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", 0, 10, 15, 15);
        verify_pawns("4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1", 0, -10, -15, -15);
        verify_pawns("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1", 2, -4, 616, 616);
        verify_pawns("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1", 2, 0, 702, 702);
        verify_pawns("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 1, 0, 336, 0);
        verify_pawns("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 4, 0, 900, 100000);
        verify_pawns("8/8/8/8/8/6k1/6q1/7K w - - 0 1", 4, 0, -900, -100000);
        verify_pawns("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 4, 0, 900, 0);

        verify_rook_files("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1", 20, 616);
        verify_rook_files("4k3/p7/8/8/8/8/1P6/R3K3 w - - 0 1", 10, 510);
        verify_rook_files("4k3/p7/8/8/8/8/P7/R3K3 w - - 0 1", 0, 500);
        verify_rook_files("4k3/8/8/8/8/8/P7/R3K3 w - - 0 1", 10, 606);
        verify_rook_files("r3k3/1p6/8/8/8/8/8/4K3 w - - 0 1", -20, -616);
        verify_rook_files("r3k3/1p6/8/8/8/8/1P6/R3K3 w - - 0 1", 0, 0);
        verify_rook_files("4k3/8/8/8/8/R7/1P6/R3K3 w - - 0 1", 40, 1136);
        verify_rook_files("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", 0, 500);

        verify("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1", 660, 30, 702, 702);
        verify("4k3/8/8/8/8/8/8/2B1KB2 b - - 0 1", 660, 30, 702, 702);
        verify("2b1kb2/8/8/8/8/8/8/4K3 w - - 0 1", -660, -30, -702, -702);
        verify("2b1kb2/8/8/8/8/8/8/2B1KB2 w - - 0 1", 0, 0, 0, 0);
        verify("4k3/8/8/8/8/8/1B6/2B1KB2 w - - 0 1", 990, 30, 1038, 1038);
        verify("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 330, 0, 336, 0);
        auto position = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1");
        const auto result = trickfish::search(position, 1);
        if (result.score != 708 || !result.best_move) {
            throw std::runtime_error("search did not use static positional term");
        }
        auto rook_position = trickfish::Position::from_fen("4k3/8/8/8/8/8/1P6/R3K3 w - - 0 1");
        const auto rook_search = trickfish::search(rook_position, 1);
        if (rook_search.score != 645 || !rook_search.best_move) {
            throw std::runtime_error("search did not use rook-file term");
        }
        auto promotion = trickfish::Position::from_fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1");
        const auto promotion_fen = promotion.to_fen();
        const auto promotion_key = promotion.key();
        const trickfish::Move promote(8, 0, 'q');
        const auto undo = promotion.make_move(promote);
        if (trickfish::game_phase(promotion) != 4) throw std::runtime_error("promotion did not update phase");
        promotion.unmake_move(promote, undo);
        if (trickfish::game_phase(promotion) != 0 || promotion.to_fen() != promotion_fen || promotion.key() != promotion_key) {
            throw std::runtime_error("promotion undo failed to restore phase/state");
        }
        auto capture_phase = trickfish::Position::from_fen("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1");
        const auto capture_fen = capture_phase.to_fen();
        const auto capture_key = capture_phase.key();
        if (trickfish::game_phase(capture_phase) != 6) throw std::runtime_error("pre-capture phase mismatch");
        const trickfish::Move capture(56, 48);
        const auto capture_undo = capture_phase.make_move(capture);
        if (trickfish::game_phase(capture_phase) != 2) throw std::runtime_error("capture did not update phase");
        capture_phase.unmake_move(capture, capture_undo);
        if (trickfish::game_phase(capture_phase) != 6 || capture_phase.to_fen() != capture_fen || capture_phase.key() != capture_key) {
            throw std::runtime_error("capture undo failed to restore phase/state");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
