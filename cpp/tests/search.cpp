#include <iostream>
#include <algorithm>
#include <stdexcept>
#include <string_view>

#include "trickfish/search.hpp"
#include "trickfish/game_status.hpp"

void verify_pv(const trickfish::Position& root, const trickfish::SearchResult& result) {
    auto replay = root;
    if (result.principal_variation.size() > static_cast<std::size_t>(result.completed_depth) ||
        (result.best_move && (result.principal_variation.empty() || result.principal_variation.front() != *result.best_move)) ||
        (!result.best_move && !result.principal_variation.empty())) {
        throw std::runtime_error("PV root or length mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(replay);
        if (std::find(legal.begin(), legal.end(), move) == legal.end()) {
            throw std::runtime_error("PV contains an illegal move");
        }
        const auto undo = replay.make_move(move);
        static_cast<void>(undo);
    }
}

void verify(std::string_view fen, int depth, int score, std::string_view move) {
    auto position = trickfish::Position::from_fen(fen);
    const auto key = position.key();
    const auto reference = trickfish::search(position, depth, false);
    trickfish::TranspositionTable table(4096);
    const auto result = trickfish::search(position, depth, table);
    const auto cached = trickfish::search(position, depth, table);
    const auto iterative = trickfish::iterative_search(position, depth);
    for (const auto* candidate : {&reference, &result, &cached, &iterative}) {
        verify_pv(position, *candidate);
    }
    if (iterative.score != reference.score || iterative.completed_depth != depth || iterative.nodes == 0) {
        throw std::runtime_error("iterative search differs from fixed-depth reference");
    }
    if (reference.score != result.score || cached.score != result.score) {
        throw std::runtime_error("TT changed search score");
    }
    if (result.best_move && !position.is_insufficient_material() &&
        (cached.best_move != result.best_move || cached.transposition_hits == 0 || cached.nodes >= result.nodes)) {
        throw std::runtime_error("cached search failed to reuse root entry");
    }
    if (result.score != score || result.nodes == 0) {
        throw std::runtime_error("search score mismatch");
    }
    if (!move.empty() && (!result.best_move || result.best_move->to_uci() != move)) {
        throw std::runtime_error("search move mismatch");
    }
    if (score == 99999) {
        if (!result.best_move) {
            throw std::runtime_error("mate search returned no move");
        }
        const auto undo = position.make_move(*result.best_move);
        if (trickfish::game_status(position) != trickfish::GameStatus::checkmate) {
            throw std::runtime_error("mate search selected a non-mating move");
        }
        position.unmake_move(*result.best_move, undo);
    }
    if (position.to_fen() != fen || position.key() != key) {
        throw std::runtime_error("search changed root position");
    }
}

int main() {
    try {
        verify("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1", 1, 500, "a1a2");
        verify("r3k3/Q7/8/8/8/8/8/4K3 b - - 0 1", 1, 500, "a8a7");
        verify("r3k3/8/8/8/8/8/q7/R3K3 w - - 0 1", 1, -500, "a1a2");
        verify("4k3/8/8/8/8/8/p7/4K3 w - - 0 1", 1, -900, "");
        auto shallow_position = trickfish::Position::from_fen("4k3/8/8/8/8/8/q7/R3K3 w - - 0 1");
        trickfish::TranspositionTable shallow_table;
        shallow_table.store({shallow_position.key(), 0, 12345, trickfish::Bound::exact, trickfish::Move(56, 48)});
        if (trickfish::search(shallow_position, 1, shallow_table).score != 500) {
            throw std::runtime_error("insufficient-depth TT entry used as score");
        }
        auto opening = trickfish::Position::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto opening_fen = opening.to_fen();
        const auto opening_key = opening.key();
        const auto plain = trickfish::search(opening, 3, false);
        trickfish::TranspositionTable collision_table(1);
        const auto collisions = trickfish::search(opening, 3, collision_table);
        const auto normal = trickfish::search(opening, 3);
        const auto iterative = trickfish::iterative_search(opening, 3);
        const auto iterative_plain = trickfish::iterative_search(opening, 3, false);
        for (const auto* candidate : {&plain, &collisions, &normal, &iterative, &iterative_plain}) {
            verify_pv(opening, *candidate);
        }
        if (plain.principal_variation.size() != 3) {
            throw std::runtime_error("TT-disabled opening PV is incomplete");
        }
        if (iterative.score != plain.score || iterative_plain.score != plain.score ||
            iterative.completed_depth != 3 || iterative_plain.completed_depth != 3 || !iterative.best_move) {
            throw std::runtime_error("iterative opening search mismatch");
        }
        if (plain.score != collisions.score || plain.score != normal.score ||
            opening.to_fen() != opening_fen || opening.key() != opening_key) {
            throw std::runtime_error("TT collision search parity mismatch");
        }
        const auto mate_fen = "7k/8/5KQ1/8/8/8/8/8 w - - 0 1";
        verify(mate_fen, 1, 99999, "");
        verify(mate_fen, 3, 99999, "");
        for (const auto fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
            "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"}) {
            auto position = trickfish::Position::from_fen(fen);
            const auto result = trickfish::search(position, 2);
            const auto terminal_iterative = trickfish::iterative_search(position, 3);
            verify_pv(position, result);
            verify_pv(position, terminal_iterative);
            if (terminal_iterative.best_move || terminal_iterative.completed_depth != 1 ||
                terminal_iterative.score != result.score) {
                throw std::runtime_error("iterative terminal root mismatch");
            }
            if (result.best_move || result.score != (position.in_check(position.side_to_move()) ? -100000 : 0)) {
                throw std::runtime_error("terminal root mismatch");
            }
        }
        verify("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1", 2, 0, "");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
