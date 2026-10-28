#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/exchange.hpp"
#include "trickfish/movegen.hpp"

void verify(std::string_view fen, std::string_view text, int expected) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    for (const auto& move : trickfish::generate_legal_moves(position)) {
        if (move.to_uci() == text) {
            if (trickfish::static_exchange(position, move) != expected || position.to_fen() != fen || position.key() != key) {
                throw std::runtime_error("exchange score or root preservation mismatch");
            }
            return;
        }
    }
    throw std::runtime_error("exchange fixture move is illegal");
}

int main() {
    try {
        verify("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1", "a1a2", 900);
        verify("r3k3/Q7/8/8/8/8/8/4K3 b - - 0 1", "a8a7", 900);
        verify("k7/8/4p3/3p4/3R4/8/8/7K w - - 0 1", "d4d5", -400);
        verify("k7/8/4p3/3p4/3R4/8/8/3Q3K w - - 0 1", "d4d5", -300);
        verify("4k3/8/4p3/3p4/3R4/8/8/4R2K w - - 0 1", "d4d5", 100);
        verify("8/8/4k3/3p4/3R4/8/8/7K w - - 0 1", "d4d5", -400);
        verify("8/8/4k3/3p4/2KR4/8/8/8 w - - 0 1", "d4d5", 100);
        verify("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6", 100);
        verify("3rk3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6", 0);
        verify("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q", 800);
        verify("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8q", 1300);
        verify("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7b8n", 720);
        verify("1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q", -100);
        auto root = trickfish::Position::from_fen("4k3/8/8/8/8/8/P7/4K3 w - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        for (const auto move : {trickfish::Move(48, 40), trickfish::Move(48, 32, 'q')}) {
            bool rejected = false;
            try { static_cast<void>(trickfish::static_exchange(root, move)); }
            catch (const std::invalid_argument&) { rejected = true; }
            if (!rejected || root.to_fen() != fen || root.key() != key) {
                throw std::runtime_error("exchange accepted invalid/quiet move or changed root");
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
