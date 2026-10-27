#include <array>
#include <iostream>
#include <stdexcept>

#include "trickfish/history.hpp"
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
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
