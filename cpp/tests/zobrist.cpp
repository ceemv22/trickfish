#include <array>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/position.hpp"

void verify(trickfish::Position& position, int depth) {
    std::array<trickfish::Bitboard, 12> expected_pieces{};
    for (std::uint8_t square = 0; square < 64; ++square) {
        const auto symbol = position.piece_at(square);
        if (symbol != '.') {
            const auto index = trickfish::piece_index(
                trickfish::color_from_symbol(symbol), trickfish::piece_type_from_symbol(symbol)
            );
            expected_pieces[index] |= trickfish::square_bit(square);
        }
    }
    for (const auto color : {trickfish::Color::white, trickfish::Color::black}) {
        const bool expected_check =
            (position.pieces(color, trickfish::PieceType::king) & position.attacks_by(trickfish::opposite(color))) != 0;
        if (position.in_check(color) != expected_check) {
            throw std::runtime_error("targeted check detection mismatch: " + position.to_fen());
        }
        for (std::size_t type = 0; type < 6; ++type) {
            const auto piece_type = static_cast<trickfish::PieceType>(type);
            if (position.pieces(color, piece_type) != expected_pieces[trickfish::piece_index(color, piece_type)]) {
                throw std::runtime_error("board and piece bitboards disagree: " + position.to_fen());
            }
        }
        trickfish::Bitboard expected = 0;
        for (std::uint8_t square = 0; square < 64; ++square) {
            const auto symbol = position.piece_at(square);
            if (symbol != '.' && trickfish::color_from_symbol(symbol) == color) {
                expected |= trickfish::square_bit(square);
            }
        }
        if (position.occupancy(color) != expected) {
            throw std::runtime_error("incremental occupancy mismatch: " + position.to_fen());
        }
    }
    const auto fen = position.to_fen();
    const auto key = position.key();
    if (key != trickfish::Position::from_fen(fen).key()) {
        throw std::runtime_error("incremental key mismatch: " + fen);
    }
    if (depth == 0) {
        return;
    }
    const auto moves = trickfish::generate_legal_moves(position);
    if (position.key() != key || position.to_fen() != fen) {
        throw std::runtime_error("legal generation changed position: " + fen);
    }
    for (const auto& move : moves) {
        const auto undo = position.make_move(move);
        verify(position, depth - 1);
        position.unmake_move(move, undo);
        verify(position, 0);
        if (position.key() != key || position.to_fen() != fen) {
            throw std::runtime_error("unmake failed to restore position: " + fen);
        }
    }
}

int main() {
    constexpr std::array<std::string_view, 6> positions = {
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1"
    };
    try {
        for (const auto fen : positions) {
            auto position = trickfish::Position::from_fen(fen);
            verify(position, 3);
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
