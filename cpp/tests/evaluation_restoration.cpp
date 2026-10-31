#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/evaluation.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::array<int, 2> reference_terms(const trickfish::Position& position) {
    int material = 0;
    int activity = 0;
    bool white_pawn = false;
    bool black_pawn = false;
    for (std::uint8_t square = 0; square < 64; ++square) {
        const auto symbol = position.piece_at(square);
        if (symbol == '.') continue;
        const bool white = symbol >= 'A' && symbol <= 'Z';
        const int sign = white ? 1 : -1;
        const auto type = white ? symbol : static_cast<char>(symbol - 'a' + 'A');
        const int rank = square / 8;
        const int file = square % 8;
        const int distance = std::abs(2 * file - 7) + std::abs(2 * rank - 7);
        switch (type) {
            case 'P':
                material += sign * 100;
                activity += sign * (5 * (white ? 6 - rank : rank - 1) + (file == 3 || file == 4 ? 6 : 0));
                white_pawn = white_pawn || white;
                black_pawn = black_pawn || !white;
                break;
            case 'N': material += sign * 320; activity += sign * std::max(0, 28 - 2 * distance); break;
            case 'B': material += sign * 330; activity += sign * std::max(0, 16 - distance); break;
            case 'R': material += sign * 500; break;
            case 'Q': material += sign * 900; break;
            case 'K': break;
            default: throw std::runtime_error("invalid mailbox piece in evaluation reference");
        }
    }
    int full_activity = activity;
    for (std::uint8_t square = 0; square < 64; ++square) {
        const auto symbol = position.piece_at(square);
        if (symbol == 'R' && square / 8 == 1 && black_pawn) full_activity += 20;
        if (symbol == 'r' && square / 8 == 6 && white_pawn) full_activity -= 20;
    }
    return {material, full_activity};
}

void verify_tree(trickfish::Position& root, int depth) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    const auto material = trickfish::evaluate_material(root);
    const auto activity = trickfish::evaluate_piece_activity(root);
    const auto phase = root.phase_units();
    const auto reference = reference_terms(root);
    require(material == reference[0] && activity == reference[1],
        "material/activity differs from mailbox reference");
    if (depth > 0) {
        for (const auto& move : trickfish::generate_legal_moves(root)) {
            const auto undo = root.make_move(move);
            verify_tree(root, depth - 1);
            root.unmake_move(move, undo);
        }
    }
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key &&
        trickfish::evaluate_material(root) == material && trickfish::evaluate_piece_activity(root) == activity && root.phase_units() == phase,
        "evaluation-state unmake changed root");
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",
            "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "4k3/8/8/8/8/8/p7/1R2K3 b - - 0 1",
            "7k/R6p/5N2/8/8/8/8/7K w - - 0 1",
            "7k/8/8/8/8/5n2/r6P/7K b - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            verify_tree(root, std::string_view(fen).starts_with("rnbq") ? 3 : 2);
        }
        for (const bool white : {true, false}) {
            auto root = trickfish::Position::from_fen(white
                ? "7k/R6p/5N2/8/8/8/8/7K w - - 0 1"
                : "7k/8/8/8/8/5n2/r6P/7K b - - 0 1");
            const int sign = white ? 1 : -1;
            require(trickfish::evaluate_piece_activity(root) == sign * 36, "invalid last-pawn activity fixture");
            const trickfish::Move move(white ? 21 : 45, white ? 15 : 55);
            const auto legal = trickfish::generate_legal_moves(root);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "last-pawn capture is not legal");
            const auto undo = root.make_move(move);
            require(trickfish::evaluate_material(root) == sign * 820 && trickfish::evaluate_piece_activity(root) == sign * 4, "last enemy pawn left stale rook-seventh bonus");
            root.unmake_move(move, undo);
            require(trickfish::evaluate_piece_activity(root) == sign * 36, "last-pawn undo did not restore rook bonus");
            const auto material = trickfish::evaluate_material(root);
            const auto activity = trickfish::evaluate_piece_activity(root);
            const auto key = root.key();
            const auto null_undo = root.make_null_move();
            require(trickfish::evaluate_material(root) == material && trickfish::evaluate_piece_activity(root) == activity,
                "null move changed white-positive evaluation state");
            root.unmake_null_move(null_undo);
            require(root.key() == key && trickfish::evaluate_material(root) == material && trickfish::evaluate_piece_activity(root) == activity,
                "null undo changed evaluation state");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
