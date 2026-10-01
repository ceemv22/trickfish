#include <charconv>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/attacks.hpp"
#include "trickfish/evaluation.hpp"
#include "trickfish/move_list.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/perft.hpp"
#include "trickfish/position.hpp"

int main(int argc, char** argv) {
    constexpr auto start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    try {
        if (argc > 1 && std::string_view(argv[1]) == "--material") {
            if (argc > 3) {
                throw std::invalid_argument("usage: --material [fen]");
            }
            const auto position = trickfish::Position::from_fen(argc == 3 ? argv[2] : start_fen);
            std::cout << trickfish::evaluate_material(position) << '\n';
            return 0;
        }
        const bool divide = argc > 1 && std::string_view(argv[1]) == "--divide";
        const bool perft = argc > 1 && std::string_view(argv[1]) == "--perft";
        if (divide || perft) {
            if (argc < 3 || argc > 4) {
                throw std::invalid_argument("usage: --perft|--divide depth [fen]");
            }
            int depth = 0;
            const std::string_view depth_text(argv[2]);
            const auto result = std::from_chars(
                depth_text.data(),
                depth_text.data() + depth_text.size(),
                depth
            );
            if (result.ec != std::errc{} || result.ptr != depth_text.data() + depth_text.size()) {
                throw std::invalid_argument("perft depth must be an integer");
            }
            const std::string fen = argc >= 4 ? argv[3] : start_fen;
            auto position = trickfish::Position::from_fen(fen);
            if (divide) {
                if (depth < 1) {
                    throw std::invalid_argument("divide depth must be positive");
                }
                std::uint64_t total = 0;
                const auto moves = trickfish::generate_legal_moves(position);
                for (const auto& move : moves) {
                    const auto undo = position.make_move(move);
                    const auto nodes = trickfish::perft(position, depth - 1);
                    position.unmake_move(move, undo);
                    std::cout << move.to_uci() << " " << nodes << '\n';
                    total += nodes;
                }
                std::cout << "total " << total << '\n';
            } else {
                std::cout << trickfish::perft(position, depth) << '\n';
            }
            return 0;
        }
        const std::string fen = argc > 1 ? argv[1] : start_fen;
        std::cout << trickfish::Position::from_fen(fen).to_fen() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
