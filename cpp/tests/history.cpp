#include <array>
#include <iostream>
#include <stdexcept>

#include "trickfish/history.hpp"
#include "trickfish/search.hpp"
#include "trickfish/movegen.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        const auto fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
        auto position = trickfish::Position::from_fen(fen);
        trickfish::RepetitionHistory history(position);
        require(history.size() == 1 && history.current_count() == 1 &&
            !history.can_claim_threefold_repetition(), "initial history mismatch");
        const std::array<trickfish::Move, 4> cycle = {
            trickfish::Move(62, 45), trickfish::Move(6, 21),
            trickfish::Move(45, 62), trickfish::Move(21, 6)
        };
        std::array<trickfish::UndoState, 8> undos;
        for (std::size_t index = 0; index < undos.size(); ++index) {
            const auto& move = cycle[index % cycle.size()];
            const auto legal = trickfish::generate_legal_moves(position);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "cycle move is illegal");
            undos[index] = position.make_move(move);
            history.push(position);
            require(history.current_key() == position.key(), "recorded key mismatch");
            if (index == 3) {
                require(history.current_count() == 2 && !history.can_claim_threefold_repetition(),
                    "twofold incorrectly claimable");
            }
        }
        require(history.current_count() == 3 && history.can_claim_threefold_repetition(),
            "threefold not detected");
        for (std::size_t index = undos.size(); index > 0; --index) {
            history.pop();
            position.unmake_move(cycle[(index - 1) % cycle.size()], undos[index - 1]);
            require(history.current_key() == position.key() && !history.can_claim_threefold_repetition(),
                "history undo mismatch");
        }
        require(position.to_fen() == fen && history.size() == 1 && history.current_count() == 1,
            "history failed to restore root");
        bool rejected = false;
        try { history.pop(); } catch (const std::underflow_error&) { rejected = true; }
        require(rejected && history.size() == 1, "initial history position removed");
        const auto root_key = position.key();
        const auto undo = position.make_move(trickfish::Move(52, 36));
        history.push(position);
        require(history.current_count() == 1 && history.current_key() != root_key,
            "new branch inherited repetition count");
        history.pop();
        position.unmake_move(trickfish::Move(52, 36), undo);
        require(history.current_key() == root_key && history.current_count() == 1,
            "branch undo failed to restore history");
        auto advantaged = trickfish::Position::from_fen(
            "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        trickfish::RepetitionHistory repeated(advantaged);
        for (std::size_t index = 0; index < 8; ++index) {
            const auto unused = advantaged.make_move(cycle[index % cycle.size()]);
            static_cast<void>(unused);
            repeated.push(advantaged);
        }
        const auto before = advantaged.to_fen();
        const auto before_key = advantaged.key();
        const auto material_search = trickfish::iterative_search(advantaged, 1, false);
        const auto repetition_search = trickfish::iterative_search(advantaged, 2, true,
            std::nullopt, std::nullopt, {}, &repeated);
        require(material_search.score > 0 && repetition_search.score == 0 && repetition_search.best_move &&
            repetition_search.transposition_hits == 0, "history-aware search failed to distinguish repetition");
        require(advantaged.to_fen() == before && advantaged.key() == before_key && repeated.size() == 9 &&
            repeated.current_count() == 3, "search modified caller history or root position");
        auto before_third = trickfish::Position::from_fen(
            "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        trickfish::RepetitionHistory twice(before_third);
        for (std::size_t index = 0; index < 7; ++index) {
            const auto unused = before_third.make_move(cycle[index % cycle.size()]);
            static_cast<void>(unused);
            twice.push(before_third);
        }
        const auto child_fen = before_third.to_fen();
        const auto child_key = before_third.key();
        const auto saved = trickfish::iterative_search(before_third, 1, true,
            std::nullopt, std::nullopt, {}, &twice);
        require(saved.score == 0 && saved.best_move == cycle[3], "search missed repetition at quiescence entry");
        require(before_third.to_fen() == child_fen && before_third.key() == child_key && twice.size() == 8 &&
            twice.current_count() == 2, "child repetition search changed root/history");
        trickfish::RepetitionHistory fresh(position);
        const auto plain = trickfish::iterative_search(position, 1, false);
        const auto history_mode = trickfish::iterative_search(position, 1, true,
            std::nullopt, std::nullopt, {}, &fresh);
        require(history_mode.score == plain.score && history_mode.transposition_hits == 0,
            "fresh history changed score or used unsafe TT scores");
        const auto stopped = trickfish::iterative_search(position, 4, true,
            plain.nodes + 2, std::nullopt, {}, &fresh);
        require(stopped.stopped && stopped.completed_depth == 1 && stopped.score == plain.score &&
            position.to_fen() == fen && fresh.size() == 1 && fresh.current_count() == 1,
            "history-aware interrupted search lost root state");
        bool mismatched = false;
        try {
            const auto ignored = trickfish::iterative_search(advantaged, 1, true,
                std::nullopt, std::nullopt, {}, &fresh);
            static_cast<void>(ignored);
        } catch (const std::invalid_argument&) {
            mismatched = true;
        }
        require(mismatched && advantaged.to_fen() == before, "mismatched root history accepted");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
