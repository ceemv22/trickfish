#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/zobrist.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::uint64_t reference_key(const trickfish::Position& position) {
    std::uint64_t key = 0;
    for (std::uint8_t square = 0; square < 64; ++square) {
        const auto symbol = position.piece_at(square);
        if (symbol == 'P' || symbol == 'p') {
            const auto color = symbol == 'P' ? trickfish::Color::white : trickfish::Color::black;
            key ^= trickfish::zobrist::keys.pieces[trickfish::piece_index(color, trickfish::PieceType::pawn)][square];
        }
    }
    return key;
}

void verify_tree(trickfish::Position& root, int depth) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    require(pawn_key == reference_key(root), "incremental pawn key differs from mailbox reference");
    if (depth == 0) return;
    const auto moves = trickfish::generate_legal_moves(root);
    require(root.pawn_key() == pawn_key, "legal filtering changed pawn key");
    for (const auto& move : moves) {
        const auto undo = root.make_move(move);
        verify_tree(root, depth - 1);
        root.unmake_move(move, undo);
        require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key,
            "unmake did not restore full/pawn state");
    }
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
        auto root = trickfish::Position::from_fen("r3k2r/8/8/3pP3/8/8/8/R3K2R w KQkq d6 0 1");
        const auto key = root.key();
        const auto pawn_key = root.pawn_key();
        auto alternate = trickfish::Position::from_fen("4k3/8/8/3pP3/8/8/8/4K3 b - - 17 9");
        require(alternate.pawn_key() == pawn_key, "pawn key depends on nonpawn/side/clock/castling/EP state");
        const auto undo = root.make_null_move();
        require(root.pawn_key() == pawn_key && root.pawn_key() == reference_key(root), "null move changed pawn structure key");
        root.unmake_null_move(undo);
        require(root.key() == key && root.pawn_key() == pawn_key, "null undo changed full/pawn keys");
        auto empty = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1");
        require(empty.pawn_key() == 0, "pawnless key must be zero");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
