#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/evaluation.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int reference_phase(const trickfish::Position& position) {
    int total = 0;
    for (std::uint8_t square = 0; square < 64; ++square) {
        const auto symbol = position.piece_at(square);
        if (symbol == 'n' || symbol == 'N' || symbol == 'b' || symbol == 'B') ++total;
        else if (symbol == 'r' || symbol == 'R') total += 2;
        else if (symbol == 'q' || symbol == 'Q') total += 4;
    }
    return total;
}

void verify_tree(trickfish::Position& position, int depth) {
    const auto fen = position.to_fen();
    const auto key = position.key();
    const auto pawn_key = position.pawn_key();
    const int phase = position.phase_units();
    require(phase == reference_phase(position) && trickfish::game_phase(position) == std::min(24, phase),
        "incremental phase differs from mailbox reference");
    if (depth > 0) {
        for (const auto& move : trickfish::generate_legal_moves(position)) {
            const auto undo = position.make_move(move);
            verify_tree(position, depth - 1);
            position.unmake_move(move, undo);
        }
    }
    require(position.to_fen() == fen && position.key() == key && position.pawn_key() == pawn_key &&
        position.phase_units() == phase, "phase/tree unmake changed root state");
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",
            "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "4k3/8/8/8/8/8/p7/1R2K3 b - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            verify_tree(root, std::string_view(fen).starts_with("rnbq") ? 3 : 2);
        }
        auto excess = trickfish::Position::from_fen("r6k/6pp/8/8/QQQQQQQ1/8/8/7K b - - 0 1");
        const auto key = excess.key();
        require(excess.phase_units() == 30 && trickfish::game_phase(excess) == 24, "promoted phase was clamped in state");
        const trickfish::Move capture(0, 32);
        const auto legal = trickfish::generate_legal_moves(excess);
        require(std::find(legal.begin(), legal.end(), capture) != legal.end(), "invalid promoted-material capture fixture");
        const auto undo = excess.make_move(capture);
        require(excess.phase_units() == 26 && trickfish::game_phase(excess) == 24,
            "capture incorrectly subtracted from clamped phase");
        verify_tree(excess, 1);
        excess.unmake_move(capture, undo);
        require(excess.phase_units() == 30 && excess.key() == key, "promoted-material undo failed");
        const auto null_undo = excess.make_null_move();
        require(excess.phase_units() == 30, "null move changed phase");
        excess.unmake_null_move(null_undo);
        require(excess.phase_units() == 30 && excess.key() == key, "null undo changed phase/state");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
