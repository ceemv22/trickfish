#include <charconv>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/attacks.hpp"
#include "trickfish/evaluation.hpp"
#include "trickfish/game_status.hpp"
#include "trickfish/move_list.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/perft.hpp"
#include "trickfish/position.hpp"
#include "trickfish/search.hpp"

int main(int argc, char** argv) {
    constexpr auto start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    try {
        if (argc > 1 && std::string_view(argv[1]) == "--search") {
            if (argc < 3 || argc > 4) {
                throw std::invalid_argument("usage: --search depth [fen]");
            }
            int depth = 0;
            const std::string_view text(argv[2]);
            const auto parsed = std::from_chars(text.data(), text.data() + text.size(), depth);
            if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size()) {
                throw std::invalid_argument("search depth must be an integer");
            }
            auto position = trickfish::Position::from_fen(argc == 4 ? argv[3] : start_fen);
            const auto result = trickfish::search(position, depth);
            std::cout << "bestmove " << (result.best_move ? result.best_move->to_uci() : "0000") << '\n';
            std::cout << "score " << result.score << '\n';
            std::cout << "nodes " << result.nodes << '\n';
            return 0;
        }
        if (argc > 1 && (std::string_view(argv[1]) == "--eval" ||
            std::string_view(argv[1]) == "--eval-stm")) {
            if (argc > 3) {
                throw std::invalid_argument("usage: --eval|--eval-stm [fen]");
            }
            auto position = trickfish::Position::from_fen(argc == 3 ? argv[2] : start_fen);
            const auto score = std::string_view(argv[1]) == "--eval-stm"
                ? trickfish::evaluate_for_side_to_move(position)
                : trickfish::evaluate(position);
            std::cout << score << '\n';
            return 0;
        }
        if (argc > 1 && std::string_view(argv[1]) == "--insufficient-material") {
            if (argc > 3) {
                throw std::invalid_argument("usage: --insufficient-material [fen]");
            }
            const auto position = trickfish::Position::from_fen(argc == 3 ? argv[2] : start_fen);
            std::cout << (position.is_insufficient_material() ? "true" : "false") << '\n';
            return 0;
        }
        if (argc > 1 && std::string_view(argv[1]) == "--status") {
            if (argc > 3) {
                throw std::invalid_argument("usage: --status [fen]");
            }
            auto position = trickfish::Position::from_fen(argc == 3 ? argv[2] : start_fen);
            switch (trickfish::game_status(position)) {
                case trickfish::GameStatus::ongoing: std::cout << "ongoing\n"; break;
                case trickfish::GameStatus::check: std::cout << "check\n"; break;
                case trickfish::GameStatus::checkmate: std::cout << "checkmate\n"; break;
                case trickfish::GameStatus::stalemate: std::cout << "stalemate\n"; break;
            }
            return 0;
        }
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
