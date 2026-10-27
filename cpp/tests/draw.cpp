#include <iostream>
#include <stdexcept>
#include <string>

#include "trickfish/draw.hpp"

void verify(int clock, trickfish::MoveCountDraw expected) {
    const auto fen = "4k3/8/8/8/8/8/8/R3K3 w - - " + std::to_string(clock) + " 1";
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    if (trickfish::move_count_draw_status(position) != expected || position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("move-count boundary or state-restoration mismatch");
    }
}

int main() {
    try {
        verify(99, trickfish::MoveCountDraw::none);
        verify(100, trickfish::MoveCountDraw::fifty_move_claim_available);
        verify(149, trickfish::MoveCountDraw::fifty_move_claim_available);
        verify(150, trickfish::MoveCountDraw::automatic_seventy_five_move);
        verify(151, trickfish::MoveCountDraw::automatic_seventy_five_move);
        for (const auto fen : {
            "7k/6Q1/6K1/8/8/8/8/8 b - - 100 1",
            "7k/6Q1/6K1/8/8/8/8/8 b - - 150 1",
            "8/8/8/8/8/6k1/6q1/7K w - - 150 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 150 1",
            "4k3/8/8/8/8/8/8/4K3 w - - 150 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            if (trickfish::move_count_draw_status(position) != trickfish::MoveCountDraw::none) {
                throw std::runtime_error("finished game misclassified as move-count claim/draw");
            }
        }
        auto quiet = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/R3K3 w - - 149 1");
        const auto before = quiet.to_fen();
        const trickfish::Move king_move(60, 61);
        const auto undo = quiet.make_move(king_move);
        if (quiet.halfmove_clock() != 150 || trickfish::move_count_draw_status(quiet) !=
            trickfish::MoveCountDraw::automatic_seventy_five_move) {
            throw std::runtime_error("quiet move did not reach automatic draw threshold");
        }
        quiet.unmake_move(king_move, undo);
        if (quiet.to_fen() != before) throw std::runtime_error("draw-boundary undo mismatch");
        auto pawn = trickfish::Position::from_fen("4k3/8/8/8/8/8/P7/4K3 w - - 149 1");
        const trickfish::Move pawn_move(48, 40);
        const auto pawn_undo = pawn.make_move(pawn_move);
        if (pawn.halfmove_clock() != 0 || trickfish::move_count_draw_status(pawn) != trickfish::MoveCountDraw::none) {
            throw std::runtime_error("pawn move did not reset draw clock");
        }
        pawn.unmake_move(pawn_move, pawn_undo);
        auto capture = trickfish::Position::from_fen("4k3/8/8/8/8/8/n7/R3K3 w - - 149 1");
        const trickfish::Move rook_capture(56, 48);
        const auto capture_undo = capture.make_move(rook_capture);
        if (capture.halfmove_clock() != 0 || trickfish::move_count_draw_status(capture) != trickfish::MoveCountDraw::none) {
            throw std::runtime_error("capture did not reset draw clock");
        }
        capture.unmake_move(rook_capture, capture_undo);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
