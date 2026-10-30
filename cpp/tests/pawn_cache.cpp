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

void equivalent(const trickfish::SearchResult& cached, const trickfish::SearchResult& reference) {
    require(cached.score == reference.score && cached.best_move == reference.best_move &&
        cached.principal_variation == reference.principal_variation && cached.nodes == reference.nodes &&
        cached.completed_depth == reference.completed_depth && cached.stopped == reference.stopped &&
        cached.transposition_hits == reference.transposition_hits && cached.correction_updates == reference.correction_updates,
        "pawn cache changed search result/trace");
    require(reference.pawn_cache_hits == 0 && reference.pawn_cache_misses == 0, "disabled pawn cache recorded work");
}

void verify_line(trickfish::Position root, const trickfish::SearchResult& result) {
    if (!result.principal_variation.empty()) {
        require(result.best_move && result.principal_variation.front() == *result.best_move, "pawn cache root/PV mismatch");
    }
    for (const auto& move : result.principal_variation) {
        const auto legal = trickfish::generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "pawn cache returned illegal PV");
        static_cast<void>(root.make_move(move));
    }
}

void verify_tree(trickfish::Position& root, trickfish::PawnEvaluationCache& cache, int depth) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    require(cache.evaluate(root) == trickfish::evaluate_static(root), "cached static terms differ on legal tree");
    if (depth > 0) {
        for (const auto& move : trickfish::generate_legal_moves(root)) {
            const auto undo = root.make_move(move);
            verify_tree(root, cache, depth - 1);
            root.unmake_move(move, undo);
        }
    }
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key, "cache tree changed state");
}

int main() {
    try {
        trickfish::PawnEvaluationCache cache(1);
        auto first = trickfish::Position::from_fen("4k3/8/8/P7/8/8/8/1N2K3 w - - 0 1");
        auto same_pawns_phase = trickfish::Position::from_fen("1n2k3/8/8/P7/8/8/8/4K3 b - - 17 9");
        require(first.pawn_key() == same_pawns_phase.pawn_key() &&
            trickfish::game_phase(first) == trickfish::game_phase(same_pawns_phase), "invalid phase-sharing fixture");
        require(cache.evaluate(first) == trickfish::evaluate_static(first) && cache.misses() == 1 && cache.hits() == 0,
            "initial pawn-cache fill mismatch");
        require(cache.evaluate(same_pawns_phase) == trickfish::evaluate_static(same_pawns_phase) && cache.hits() == 1 &&
            trickfish::evaluate_static(first) != trickfish::evaluate_static(same_pawns_phase),
            "cache reused nonpawn terms instead of pawn score");
        auto phase_change = trickfish::Position::from_fen("4k3/8/8/P7/8/8/8/4K3 w - - 0 1");
        require(trickfish::evaluate_pawn_structure(first) != trickfish::evaluate_pawn_structure(phase_change),
            "phase fixture must change pawn score");
        require(cache.evaluate(phase_change) == trickfish::evaluate_static(phase_change) && cache.misses() == 2,
            "same pawn key with different phase reused stale score");
        require(cache.evaluate(phase_change) == trickfish::evaluate_static(phase_change) && cache.hits() == 2,
            "repeat pawn structure did not hit");
        auto collision = trickfish::Position::from_fen("4k3/8/8/8/1P6/8/8/4K3 w - - 0 1");
        require(cache.evaluate(collision) == trickfish::evaluate_static(collision) && cache.misses() == 3,
            "colliding pawn key produced false hit");
        require(cache.evaluate(first) == trickfish::evaluate_static(first) && cache.misses() == 4,
            "evicted pawn entry produced false hit");
        cache.clear();
        require(cache.hits() == 0 && cache.misses() == 0 && cache.capacity() == 1, "pawn-cache clear mismatch");
        auto empty = trickfish::Position::from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1");
        require(cache.evaluate(empty) == trickfish::evaluate_static(empty) && cache.misses() == 1,
            "zero pawn key was treated as initialized entry");
        bool rejected = false;
        try { trickfish::PawnEvaluationCache invalid(0); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "zero pawn-cache capacity accepted");
        bool observed_hits = false;
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "2b1k3/7p/8/8/8/8/PP6/2B1K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            const auto pawn_key = root.pawn_key();
            trickfish::RepetitionHistory history(root);
            trickfish::PawnEvaluationCache tree_cache(16);
            verify_tree(root, tree_cache, std::string_view(fen).starts_with("rnbq") ? 2 : 1);
            for (int variant = 0; variant < 4; ++variant) {
                trickfish::SearchOptions reference;
                reference.use_table = variant != 1;
                reference.use_correction = variant == 2;
                reference.use_endgame_scaling = variant == 2;
                reference.use_exchange_ordering = variant == 3;
                reference.use_mate_distance = variant == 3;
                const auto* played = variant == 1 ? &history : nullptr;
                require(!reference.use_pawn_cache, "pawn cache must default off");
                auto enabled = reference;
                enabled.use_pawn_cache = true;
                const int depth = variant == 0 && std::string_view(fen).starts_with("rnbq") ? 3 : 2;
                const auto baseline = trickfish::iterative_search(root, depth, reference, {}, played);
                const auto result = trickfish::iterative_search(root, depth, enabled, {}, played);
                equivalent(result, baseline);
                verify_line(root, result);
                observed_hits = observed_hits || result.pawn_cache_hits > 0;
                require(result.pawn_cache_misses > 0, "enabled cache was not used by search");
                const auto repeated = trickfish::iterative_search(root, depth, enabled, {}, played);
                require(repeated.pawn_cache_hits == result.pawn_cache_hits && repeated.pawn_cache_misses == result.pawn_cache_misses,
                    "pawn cache leaked across searches");
                for (const auto limit : {0ULL, 32ULL}) {
                    equivalent(trickfish::iterative_search(root, depth, enabled, {limit, {}, {}}, played),
                        trickfish::iterative_search(root, depth, reference, {limit, {}, {}}, played));
                }
                require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && history.size() == 1,
                    "pawn cache changed root/history state");
            }
        }
        require(observed_hits, "search never reused a pawn cache entry");
        for (const auto fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 150 1", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            trickfish::SearchOptions baseline;
            auto enabled = baseline;
            enabled.use_pawn_cache = true;
            equivalent(trickfish::iterative_search(root, 2, enabled), trickfish::iterative_search(root, 2, baseline));
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
