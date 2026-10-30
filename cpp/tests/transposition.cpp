#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/transposition.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void verify_reused_search(std::string_view fen) {
    auto root = trickfish::Position::from_fen(fen);
    const auto key = root.key();
    const auto reference = trickfish::search(root, 3, false);
    trickfish::TranspositionTable table(64);
    for (int repeat = 0; repeat < 2; ++repeat) {
        const auto result = trickfish::search(root, 3, table);
        require(result.score == reference.score && result.completed_depth == 3, "reused TT changed search score/depth");
        auto replay = root;
        if (result.best_move) {
            require(!result.principal_variation.empty() && result.principal_variation.front() == *result.best_move,
                "reused TT root/PV mismatch");
        }
        for (const auto& move : result.principal_variation) {
            const auto legal = trickfish::generate_legal_moves(replay);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "reused TT returned illegal PV");
            static_cast<void>(replay.make_move(move));
        }
        require(root.to_fen() == fen && root.key() == key, "reused TT search changed root");
    }
}

int main() {
    try {
        for (const int score : {0, 500, -500, 99999, -99999, 99904, -99904}) {
            for (const int ply : {0, 1, 32, 96}) {
                require(trickfish::score_from_table(trickfish::score_to_table(score, ply), ply) == score,
                    "mate score round-trip mismatch");
            }
        }
        require(trickfish::score_from_table(trickfish::score_to_table(99993, 5), 2) == 99996,
            "winning mate distance changed across transposition");
        require(trickfish::score_from_table(trickfish::score_to_table(-99993, 5), 2) == -99996,
            "losing mate distance changed across transposition");
        require(trickfish::score_to_table(500, 32) == 500 &&
            trickfish::score_from_table(-500, 32) == -500, "ordinary score adjusted");
        trickfish::TranspositionTable table(2);
        require(table.capacity() == 2 && table.probe(0) == nullptr, "empty table mismatch");
        const trickfish::Move move(52, 36);
        table.store({0, 4, 125, trickfish::Bound::lower, move});
        const auto* entry = table.probe(0);
        require(entry && entry->depth == 4 && entry->score == 125 &&
            entry->bound == trickfish::Bound::lower && entry->best_move == move, "zero-key payload mismatch");
        require(table.probe(2) == nullptr, "colliding key produced false hit");
        table.store({0, 2, -10, trickfish::Bound::upper, std::nullopt});
        require(table.probe(0)->depth == 4, "shallower result replaced deeper same-key entry");
        table.store({0, 4, 200, trickfish::Bound::exact, std::nullopt});
        require(table.probe(0)->score == 200 && !table.probe(0)->best_move, "equal-depth replacement mismatch");
        table.store({1, 1, 5, trickfish::Bound::upper, std::nullopt});
        table.store({2, 3, 50, trickfish::Bound::exact, move});
        require(table.probe(0) == nullptr && table.probe(2) && table.probe(1), "collision eviction mismatch");
        table.clear();
        require(!table.probe(1) && !table.probe(2) && table.capacity() == 2, "reset mismatch");
        trickfish::TranspositionTable bounds(1);
        bounds.store({7, 6, 17, trickfish::Bound::exact, move});
        for (const auto kind : {trickfish::Bound::lower, trickfish::Bound::upper}) {
            bounds.store({7, 6, 17, kind, std::nullopt});
            require(bounds.probe(7)->bound == trickfish::Bound::exact && bounds.probe(7)->best_move == move,
                "same-depth bound discarded exact information/move");
        }
        bounds.store({7, 7, 20, trickfish::Bound::lower, std::nullopt});
        require(bounds.probe(7)->depth == 7 && bounds.probe(7)->bound == trickfish::Bound::lower,
            "deeper bound did not replace shallower exact entry");
        bounds.store({7, 7, 10, trickfish::Bound::lower, move});
        require(bounds.probe(7)->score == 20 && !bounds.probe(7)->best_move,
            "weaker lower bound replaced stronger payload");
        bounds.store({7, 7, 30, trickfish::Bound::lower, move});
        require(bounds.probe(7)->score == 30 && bounds.probe(7)->best_move == move,
            "stronger lower bound was not accepted");
        bounds.clear();
        bounds.store({7, 7, -10, trickfish::Bound::upper, move});
        bounds.store({7, 7, 0, trickfish::Bound::upper, std::nullopt});
        require(bounds.probe(7)->score == -10 && bounds.probe(7)->best_move == move,
            "weaker upper bound replaced stronger payload");
        bounds.store({7, 7, -20, trickfish::Bound::upper, std::nullopt});
        require(bounds.probe(7)->score == -20 && !bounds.probe(7)->best_move,
            "stronger upper bound was not accepted");
        bounds.store({7, 7, -25, trickfish::Bound::exact, move});
        require(bounds.probe(7)->bound == trickfish::Bound::exact && bounds.probe(7)->score == -25,
            "same-depth exact did not replace bound");
        bounds.store({8, 1, 0, trickfish::Bound::upper, std::nullopt});
        require(!bounds.probe(7) && bounds.probe(8), "same-key preference changed collision eviction");
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"}) {
            verify_reused_search(fen);
        }
        bool rejected = false;
        try {
            trickfish::TranspositionTable invalid(0);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "zero capacity accepted");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
