#include <charconv>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#include "trickfish/attacks.hpp"
#include "trickfish/move_list.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/perft.hpp"
#include "trickfish/position.hpp"

int main(int argc, char** argv) {
    constexpr auto start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    try {
        if (argc >= 3 && std::string_view(argv[1]) == "--perft") {
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
            std::cout << trickfish::perft(position, depth) << '\n';
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
