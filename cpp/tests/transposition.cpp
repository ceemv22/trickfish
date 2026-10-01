#include <iostream>
#include <stdexcept>

#include "trickfish/transposition.hpp"

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
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
