#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/movegen.hpp"
#include "trickfish/position.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify(std::string_view fen, std::string_view expected) {
    auto position = trickfish::Position::from_fen(fen);
    const auto original = position;
    const auto first = position.make_null_move();
    require(position.to_fen() == expected && position.key() == trickfish::Position::from_fen(expected).key(),
        "null state/FEN/incremental-key mismatch");
    for (const auto color : {trickfish::Color::white, trickfish::Color::black}) {
        require(position.occupancy(color) == original.occupancy(color) &&
            position.attacks_by(color) == original.attacks_by(color), "null move changed occupancy or attacks");
        for (const auto type : {trickfish::PieceType::pawn, trickfish::PieceType::knight, trickfish::PieceType::bishop,
            trickfish::PieceType::rook, trickfish::PieceType::queen, trickfish::PieceType::king}) {
            require(position.pieces(color, type) == original.pieces(color, type), "null move changed piece boards");
        }
    }
    require(position.castling_rights() == original.castling_rights(), "null move changed castling rights");
    const auto first_key = position.key();
    const auto second = position.make_null_move();
    require(position.key() == trickfish::Position::from_fen(position.to_fen()).key(), "nested null key mismatch");
    position.unmake_null_move(second);
    require(position.to_fen() == expected && position.key() == first_key, "nested null undo mismatch");
    const auto legal = trickfish::generate_legal_moves(position);
    require(!legal.empty(), "null fixture has no reply");
    const auto reply = legal[0];
    const auto undo = position.make_move(reply);
    require(position.key() == trickfish::Position::from_fen(position.to_fen()).key(), "reply after null key mismatch");
    position.unmake_move(reply, undo);
    require(position.to_fen() == expected && position.key() == first_key, "reply undo lost null state");
    position.unmake_null_move(first);
    require(position.to_fen() == fen && position.key() == original.key(), "null undo failed root restoration");
}

int main() {
    try {
        verify("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 1 1");
        verify("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 3 7",
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 4 8");
        verify("4k3/8/8/3pP3/8/8/8/4K3 w - d6 5 7", "4k3/8/8/3pP3/8/8/8/4K3 b - - 6 7");
        verify("4k3/8/8/8/3Pp3/8/8/4K3 b - d3 5 7", "4k3/8/8/8/3Pp3/8/8/4K3 w - - 6 8");
        verify("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "k3r3/8/8/3pP3/8/8/8/4K3 b - - 1 1");
        verify("4k3/8/8/3p4/8/8/8/4K3 w - d6 0 1", "4k3/8/8/3p4/8/8/8/4K3 b - - 1 1");
        for (const auto fen : {"4k3/8/8/8/8/8/4r3/4K3 w - - 0 1", "4k3/4R3/8/8/8/8/8/4K3 b - - 0 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto key = position.key();
            bool rejected = false;
            try { static_cast<void>(position.make_null_move()); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && position.to_fen() == fen && position.key() == key, "checked null move mutated position");
        }
        const auto maximum = std::to_string(std::numeric_limits<int>::max());
        for (const auto fen : {"4k3/8/8/8/8/8/8/4K3 w - - " + maximum + " 1",
            "4k3/8/8/8/8/8/8/4K3 b - - 0 " + maximum}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto key = position.key();
            bool rejected = false;
            try { static_cast<void>(position.make_null_move()); }
            catch (const std::overflow_error&) { rejected = true; }
            require(rejected && position.to_fen() == fen && position.key() == key, "overflowing null move mutated position");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
