#include <algorithm>
#include <iostream>
#include <limits>
#include <stdexcept>

#include "trickfish/correction.hpp"
#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_line(trickfish::Position position, const trickfish::SearchResult& result) {
    require(result.principal_variation.size() <= static_cast<std::size_t>(result.completed_depth), "correction PV too long");
    require(result.best_move && !result.principal_variation.empty() &&
        result.principal_variation.front() == *result.best_move, "correction root/PV mismatch");
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(position);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "correction returned illegal PV");
        const auto undo = position.make_move(move);
        static_cast<void>(undo);
    }
}

int main() {
    try {
        auto root = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        trickfish::CorrectionHistory correction;
        require(correction.adjustment(root) == 0, "new correction context was not empty");
        require(correction.update(root, 128, 0, 16) && correction.adjustment(root) == 64, "correction sample weighting mismatch");
        auto same_pawns = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/2N5/PPPPPPPP/R1BQKBNR w KQkq - 0 1");
        auto other_side = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1");
        auto changed_pawns = trickfish::Position::from_fen(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1");
        require(correction.adjustment(same_pawns) == 64 && correction.adjustment(other_side) == 0 &&
            correction.adjustment(changed_pawns) == 0, "correction pawn/side context mismatch");
        require(!correction.update(root, 100000, 0, 16) &&
            !correction.update(root, std::numeric_limits<int>::min(), 0, 16) && correction.adjustment(root) == 64,
            "mate-band correction sample was accepted");
        for (int index = 0; index < 128; ++index) static_cast<void>(correction.update(root, 10000, 0, 64));
        require(correction.adjustment(root) > 0 && correction.adjustment(root) <= 256, "positive correction overflow");
        for (int index = 0; index < 128; ++index) static_cast<void>(correction.update(root, -10000, 0, 64));
        require(correction.adjustment(root) < 0 && correction.adjustment(root) >= -256, "negative correction overflow");
        correction.clear();
        require(correction.adjustment(root) == 0 && root.to_fen() == fen && root.key() == key, "correction clear/state mismatch");
        for (int invalid : {0, 65}) {
            bool rejected = false;
            try { static_cast<void>(correction.update(root, 128, 0, invalid)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && correction.adjustment(root) == 0, "invalid correction depth changed state");
        }
        trickfish::SearchOptions options;
        const auto baseline = trickfish::iterative_search(root, 2, options);
        require(baseline.correction_updates == 0 && baseline.correction_applications == 0, "default search used correction");
        options.use_correction = true;
        const auto uncached = trickfish::iterative_search(root, 2, options);
        require(uncached.transposition_hits == 0 && uncached.correction_updates > 0,
            "correction search reused TT without history isolation");
        trickfish::RepetitionHistory history(root);
        int depth = 4;
        auto active = trickfish::iterative_search(root, depth, options, {}, &history);
        if (active.correction_applications == 0) active = trickfish::iterative_search(root, ++depth, options, {}, &history);
        require(active.correction_updates > 0 && active.correction_applications > 0 && active.transposition_hits == 0,
            "correction learning/application/TT isolation mismatch");
        verify_line(root, active);
        const auto repeated = trickfish::iterative_search(root, depth, options, {}, &history);
        require(active.score == repeated.score && active.nodes == repeated.nodes && active.best_move == repeated.best_move &&
            active.correction_updates == repeated.correction_updates && active.correction_applications == repeated.correction_applications,
            "correction state leaked between searches");
        trickfish::SearchLimits limits;
        limits.nodes = active.nodes - 1;
        const auto stopped = trickfish::iterative_search(root, depth, options, limits, &history);
        require(stopped.stopped && stopped.completed_depth == depth - 1 && history.size() == 1 &&
            root.to_fen() == fen && root.key() == key && trickfish::evaluate_static(root) == 0,
            "correction search mutated root/history/public evaluator");
        auto mate = trickfish::Position::from_fen("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1");
        const auto terminal = trickfish::iterative_search(mate, 2, options);
        require(terminal.score == -100000 && !terminal.best_move && terminal.correction_updates == 0,
            "correction changed terminal mate");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
