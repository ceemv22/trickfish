#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/evaluation.hpp"
#include "trickfish/pawn_cache.hpp"
#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_search(std::string_view fen, int factor, std::string_view reason) {
    auto root = trickfish::Position::from_fen(fen);
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    const int raw = trickfish::evaluate_static(root);
    const int sign = root.side_to_move() == trickfish::Color::white ? 1 : -1;
    const auto scaling = trickfish::endgame_scaling(root);
    require(scaling.factor == factor && scaling.reason == reason, "pawnless classification mismatch");
    require(trickfish::endgame_scale(root) == factor && trickfish::evaluate_scaled_static(root) == raw * factor / 256,
        "pawnless scaling arithmetic mismatch");
    require(!root.is_insufficient_material(), "pawnless heuristic changed dead-position detection");
    trickfish::SearchOptions options;
    require(!options.use_endgame_scaling, "scaling must default off");
    const auto ordinary = trickfish::iterative_search(root, 2, options, {0, {}, {}});
    require(ordinary.stopped && ordinary.score == raw * sign, "default fallback changed");
    options.use_endgame_scaling = true;
    const auto fallback = trickfish::iterative_search(root, 2, options, {0, {}, {}});
    require(fallback.stopped && fallback.completed_depth == 0 && fallback.best_move &&
        fallback.score == (raw * factor / 256) * sign, "pawnless scaled fallback mismatch");
    const auto result = trickfish::iterative_search(root, 2, options);
    auto reference = options;
    reference.use_table = false;
    require(result.completed_depth == 2 && result.score == trickfish::iterative_search(root, 2, reference).score,
        "pawnless table/reference mismatch");
    auto cached = options;
    cached.use_pawn_cache = true;
    const auto cached_result = trickfish::iterative_search(root, 2, cached);
    require(cached_result.score == result.score && cached_result.nodes == result.nodes &&
        cached_result.best_move == result.best_move && cached_result.principal_variation == result.principal_variation,
        "pawnless cache changed search trace");
    auto replay = root;
    require(result.best_move && !result.principal_variation.empty() &&
        result.best_move == result.principal_variation.front(), "pawnless root/PV mismatch");
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(replay);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal pawnless PV");
        static_cast<void>(replay.make_move(move));
    }
    reference.use_correction = true;
    require(trickfish::iterative_search(root, 2, reference).completed_depth == 2, "pawnless correction did not complete");
    const auto null_undo = root.make_null_move();
    require(trickfish::endgame_scaling(root).factor == factor && trickfish::endgame_scaling(root).reason == reason,
        "null move changed pawnless material classification");
    root.unmake_null_move(null_undo);
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key &&
        trickfish::evaluate_static(root) == raw, "pawnless search changed root/public evaluation");
}

void verify_transition(std::string_view fen, std::string_view uci, int before, int after) {
    auto root = trickfish::Position::from_fen(fen);
    const auto key = root.key();
    const auto raw = trickfish::evaluate_static(root);
    require(trickfish::endgame_scale(root) == before, "transition initial scale mismatch");
    bool found = false;
    for (const auto& move : trickfish::generate_legal_moves(root)) {
        if (move.to_uci() != uci) continue;
        found = true;
        const auto undo = root.make_move(move);
        require(trickfish::endgame_scale(root) == after, "material transition did not update scale");
        root.unmake_move(move, undo);
    }
    require(found && root.to_fen() == fen && root.key() == key &&
        trickfish::endgame_scale(root) == before && trickfish::evaluate_static(root) == raw,
        "material transition undo failed");
}

int main() {
    try {
        require(trickfish::endgame_scaling(trickfish::Position::from_fen(
            "2b1k3/7p/8/8/8/8/PP6/2B1K3 w - - 0 1")).reason == "opposite_bishop_pawns",
            "existing bishop scaling reason changed");
        require(trickfish::endgame_scaling(trickfish::Position::from_fen(
            "k7/8/8/8/8/8/P7/2B1K3 w - - 0 1")).reason == "wrong_bishop_rook_pawn_corner",
            "existing corner scaling reason changed");
        verify_search("7k/8/8/8/8/8/8/1N2K1N1 w - - 0 1", 32, "two_knights_bare_king");
        verify_search("7k/8/8/8/8/8/8/1N2K1N1 b - - 0 1", 32, "two_knights_bare_king");
        verify_search("2b4k/8/8/8/8/8/8/R3K3 w - - 0 1", 64, "rook_minor");
        verify_search("1n5k/8/8/8/8/8/8/R3K3 b - - 0 1", 64, "rook_minor");
        verify_search("r6k/8/8/8/8/8/8/R1B1K3 w - - 0 1", 64, "rook_minor_rook");
        verify_search("r6k/8/8/8/8/8/8/RN2K3 b - - 0 1", 64, "rook_minor_rook");
        verify_transition("1n5k/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8", 64, 64);
        verify_transition("7k/8/8/8/8/8/n7/R3K3 w - - 0 1", "a1a2", 64, 256);
        verify_transition("7k/8/8/8/8/8/p7/RN2K3 w - - 0 1", "a1a2", 256, 256);
        verify_transition("r6k/8/8/8/8/8/8/RN2K3 w - - 0 1", "a1a8", 64, 256);
        verify_transition("7k/8/8/8/8/8/1p6/1N2K1N1 w - - 0 1", "b1d2", 256, 256);
        verify_transition("7k/8/8/8/8/8/3p4/1N2K1N1 w - - 0 1", "b1d2", 256, 32);
        verify_transition("7k/P7/8/8/8/8/8/4K1N1 w - - 0 1", "a7a8n", 256, 32);
        trickfish::SearchOptions options;
        options.use_endgame_scaling = true;
        auto mate = trickfish::Position::from_fen("7k/5K2/5NN1/8/8/8/8/8 b - - 0 1");
        require(trickfish::endgame_scale(mate) == 32 && trickfish::game_status(mate) == trickfish::GameStatus::checkmate,
            "two-knight mate fixture invalid");
        const auto result = trickfish::iterative_search(mate, 2, options);
        require(result.score == -trickfish::mate_score && !result.best_move, "pawnless scaling suppressed mate");
        auto clock = trickfish::Position::from_fen("7k/8/8/8/8/8/8/1N2K1N1 w - - 150 1");
        const auto draw = trickfish::iterative_search(clock, 2, options);
        require(draw.score == 0 && !draw.best_move, "pawnless scaling suppressed automatic draw");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
