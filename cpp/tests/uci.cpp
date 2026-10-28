#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "trickfish/movegen.hpp"
#include "trickfish/uci.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::string session(const std::string& commands) {
    std::istringstream input(commands);
    std::ostringstream output;
    require(trickfish::run_uci(input, output) == 0, "UCI returned failure");
    return output.str();
}

std::vector<std::string> best_moves(const std::string& output) {
    std::istringstream input(output);
    std::vector<std::string> moves;
    for (std::string line; std::getline(input, line);) {
        if (line.starts_with("bestmove ")) moves.push_back(line.substr(9));
    }
    return moves;
}

void require_legal(std::string_view command, const std::string& move) {
    auto root = trickfish::parse_uci_position(command);
    const auto legal = trickfish::generate_legal_moves(root.position);
    require(std::any_of(legal.begin(), legal.end(), [&](const trickfish::Move& candidate) {
        return candidate.to_uci() == move;
    }), "UCI returned an illegal move");
}

int main() {
    try {
        const auto handshake = session("uci\nisready\nquit\n");
        require(handshake.find("id name Trickfish C++\n") != std::string::npos &&
            handshake.find("id author ceemv22\n") != std::string::npos &&
            handshake.find("option name Move Overhead type spin default 10 min 0 max 10000\n") != std::string::npos &&
            handshake.find("uciok\nreadyok\n") != std::string::npos, "handshake mismatch");
        auto e4 = trickfish::parse_uci_position("position startpos moves e2e4");
        require(e4.position.side_to_move() == trickfish::Color::black && e4.history.size() == 2,
            "startpos move/history mismatch");
        const auto repetition = trickfish::parse_uci_position(
            "position startpos moves g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8");
        require(repetition.history.current_count() == 3 && repetition.history.size() == 9,
            "UCI discarded repetition history");
        const auto promoted = trickfish::parse_uci_position("position fen 4k3/P7/8/8/8/8/8/4K3 w - - 0 1 moves a7a8q");
        require(promoted.position.piece_at(0) == 'Q' && promoted.history.size() == 2, "promotion parsing failed");
        const auto ep = trickfish::parse_uci_position("position fen 4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1 moves e5d6");
        require(ep.position.piece_at(19) == 'P' && ep.position.piece_at(27) == '.', "EP move flags lost");
        const auto castled = trickfish::parse_uci_position("position fen r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1 moves e1g1");
        require(castled.position.piece_at(62) == 'K' && castled.position.piece_at(61) == 'R', "castling flags lost");
        for (const auto command : {
            "position startpos moves e2e5", "position fen 4k3/8/3N4/3pP3/8/8/8/4K3 w - d6 0 1",
            "position fen P3k3/8/8/8/8/8/8/4K3 w - - 0 1", "position fen 4k3/8/8/8/8/8/8/4K3 w - d3 0 1",
            "position fen 8/8/8/8/8/8/8/8 w - - 0 1", "position startpos extra"}) {
            bool rejected = false;
            try {
                const auto ignored = trickfish::parse_uci_position(command);
                static_cast<void>(ignored);
            } catch (const std::invalid_argument&) { rejected = true; }
            require(rejected, "invalid UCI position accepted");
        }
        const auto atomic = session("position startpos moves e2e4\n"
            "position startpos moves d2d4 d7d5 g1z9\ngo nodes 0\nstop\nquit\n");
        const auto atomic_moves = best_moves(atomic);
        require(atomic.find("info string error: illegal move: g1z9") != std::string::npos && atomic_moves.size() == 1,
            "malformed position did not report error");
        require_legal("position startpos moves e2e4", atomic_moves[0]);
        const auto running = session("go infinite\nisready\nstop\nstop\nquit\n");
        require(running.find("readyok\n") < running.find("bestmove ") && best_moves(running).size() == 1,
            "readiness/stop lifecycle mismatch");
        require_legal("position startpos", best_moves(running)[0]);
        const auto clocks = session("setoption name move overhead value 10000\n"
            "position startpos moves e2e4\ngo depth 4 wtime 1000000 btime 10000 binc 500 movestogo 20\nquit\n");
        const auto clock_moves = best_moves(clocks);
        require(clock_moves.size() == 1 && clocks.find("error:") == std::string::npos,
            "clock control/overhead command failed");
        require_legal("position startpos moves e2e4", clock_moves[0]);
        const auto invalid_clock = session("go wtime 1000 movestogo 0\nisready\nquit\n");
        require(invalid_clock.find("movestogo must be positive") != std::string::npos &&
            invalid_clock.find("readyok") != std::string::npos && best_moves(invalid_clock).empty(),
            "invalid clock parameters started a search");
        const auto eof = best_moves(session("go depth 64\n"));
        require(eof.size() == 1, "EOF did not stop and join search");
        require_legal("position startpos", eof[0]);
        const auto reset = best_moves(session("position startpos moves e2e4\nucinewgame\ngo nodes 0\nquit\n"));
        require(reset.size() == 1, "new-game lifecycle mismatch");
        require_legal("position startpos", reset[0]);
        const auto superseded = best_moves(session("go infinite\nposition startpos moves e2e4\ngo nodes 0\nquit\n"));
        require(superseded.size() == 2, "superseded search did not return exactly one bestmove");
        require_legal("position startpos", superseded[0]);
        require_legal("position startpos moves e2e4", superseded[1]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
