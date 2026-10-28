#include <charconv>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/attacks.hpp"
#include "trickfish/evaluation.hpp"
#include "trickfish/exchange.hpp"
#include "trickfish/game_status.hpp"
#include "trickfish/move_list.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/perft.hpp"
#include "trickfish/position.hpp"
#include "trickfish/search.hpp"
#include "trickfish/uci.hpp"

int main(int argc, char** argv) {
    constexpr auto start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    try {
        if (argc == 1 || (argc == 2 && std::string_view(argv[1]) == "--uci")) {
            return trickfish::run_uci(std::cin, std::cout);
        }
        if (argc > 1 && std::string_view(argv[1]) == "--see") {
            if (argc < 3 || argc > 4) throw std::invalid_argument("usage: --see move [fen]");
            auto position = trickfish::Position::from_fen(argc == 4 ? argv[3] : start_fen);
            for (const auto& move : trickfish::generate_legal_moves(position)) {
                if (move.to_uci() == argv[2]) {
                    std::cout << trickfish::static_exchange(position, move) << '\n';
                    return 0;
                }
            }
            throw std::invalid_argument("exchange move must be legal");
        }
        if (argc > 1 && std::string_view(argv[1]) == "--eval-detail") {
            if (argc > 3) throw std::invalid_argument("usage: --eval-detail [fen]");
            auto position = trickfish::Position::from_fen(argc == 3 ? argv[2] : start_fen);
            const auto detail = trickfish::evaluate_breakdown(position);
            std::cout << "phase " << detail.phase << '\n';
            std::cout << "material " << detail.material << '\n';
            std::cout << "piece_activity " << detail.piece_activity << '\n';
            std::cout << "pawn_structure " << detail.pawn_structure << '\n';
            std::cout << "bishop_pair " << detail.bishop_pair << '\n';
            std::cout << "rook_files " << detail.rook_files << '\n';
            std::cout << "king_safety " << detail.king_safety << '\n';
            std::cout << "king_activity " << detail.king_activity << '\n';
            std::cout << "static_total " << detail.total() << '\n';
            std::cout << "evaluation " << trickfish::evaluate(position) << '\n';
            return 0;
        }
        const bool limited_search = argc > 1 && std::string_view(argv[1]) == "--search-nodes";
        const bool timed_search = argc > 1 && std::string_view(argv[1]) == "--search-time";
        const bool reference_search = argc > 1 && std::string_view(argv[1]) == "--search-ab";
        const bool budgeted_search = limited_search || timed_search;
        if (argc > 1 && (std::string_view(argv[1]) == "--search" || reference_search || budgeted_search)) {
            if (argc < (budgeted_search ? 4 : 3) || argc > (budgeted_search ? 5 : 4)) {
                throw std::invalid_argument("usage: --search|--search-ab depth [fen], --search-nodes depth nodes [fen], or --search-time depth milliseconds [fen]");
            }
            int depth = 0;
            const std::string_view text(argv[2]);
            const auto parsed = std::from_chars(text.data(), text.data() + text.size(), depth);
            if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size()) {
                throw std::invalid_argument("search depth must be an integer");
            }
            std::optional<std::uint64_t> node_limit;
            if (limited_search) {
                std::uint64_t limit = 0;
                const std::string_view limit_text(argv[3]);
                const auto parsed_limit = std::from_chars(limit_text.data(), limit_text.data() + limit_text.size(), limit);
                if (parsed_limit.ec != std::errc{} || parsed_limit.ptr != limit_text.data() + limit_text.size()) {
                    throw std::invalid_argument("node limit must be a non-negative integer");
                }
                node_limit = limit;
            }
            std::optional<std::chrono::steady_clock::time_point> deadline;
            if (timed_search) {
                std::uint64_t milliseconds = 0;
                const std::string_view time_text(argv[3]);
                const auto parsed_time = std::from_chars(time_text.data(), time_text.data() + time_text.size(), milliseconds);
                const auto now = std::chrono::steady_clock::now();
                const auto maximum = std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::time_point::max() - now).count();
                if (parsed_time.ec != std::errc{} || parsed_time.ptr != time_text.data() + time_text.size() ||
                    milliseconds > static_cast<std::uint64_t>(maximum)) {
                    throw std::invalid_argument("time limit must be a non-negative representable millisecond count");
                }
                deadline = now + std::chrono::milliseconds(static_cast<std::chrono::milliseconds::rep>(milliseconds));
            }
            const int fen_index = budgeted_search ? 4 : 3;
            auto position = trickfish::Position::from_fen(argc > fen_index ? argv[fen_index] : start_fen);
            trickfish::SearchOptions options;
            options.use_history = !reference_search;
            options.use_pvs = !reference_search;
            options.use_killers = !reference_search;
            options.aspiration_window = reference_search ? 0 : 25;
            trickfish::SearchLimits limits;
            limits.nodes = node_limit;
            limits.deadline = deadline;
            const auto result = trickfish::iterative_search(position, depth, options, limits);
            std::cout << "bestmove " << (result.best_move ? result.best_move->to_uci() : "0000") << '\n';
            std::cout << "score " << result.score << '\n';
            std::cout << "pv";
            for (const auto& move : result.principal_variation) {
                std::cout << " " << move.to_uci();
            }
            std::cout << '\n';
            std::cout << "depth " << result.completed_depth << '\n';
            std::cout << "stopped " << (result.stopped ? "true" : "false") << '\n';
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
