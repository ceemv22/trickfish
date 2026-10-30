#include <iostream>
#include <stdexcept>
#include <string_view>

#include "trickfish/search.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void equivalent(const trickfish::SearchResult& cached, const trickfish::SearchResult& reference) {
    require(cached.score == reference.score && cached.best_move == reference.best_move &&
        cached.principal_variation == reference.principal_variation && cached.completed_depth == reference.completed_depth &&
        cached.nodes == reference.nodes && cached.stopped == reference.stopped &&
        cached.transposition_hits == reference.transposition_hits, "cached ordering changed search result/trace");
    require(cached.killer_cutoffs == reference.killer_cutoffs &&
        cached.history_rewards == reference.history_rewards && cached.history_penalties == reference.history_penalties &&
        cached.continuation_updates == reference.continuation_updates &&
        cached.exchange_evaluations == reference.exchange_evaluations && cached.exchange_nodes == reference.exchange_nodes &&
        cached.exchange_cutoffs == reference.exchange_cutoffs, "cached ordering changed heuristic work");
}

int main() {
    try {
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1"}) {
            auto root = trickfish::Position::from_fen(fen);
            const auto key = root.key();
            trickfish::RepetitionHistory history(root);
            for (const bool exchange : {false, true}) {
                for (const bool table : {false, true}) {
                    for (const bool played : {false, true}) {
                        trickfish::SearchOptions options;
                        options.use_exchange_ordering = exchange;
                        options.use_table = table;
                        auto reference = options;
                        reference.use_cached_ordering = false;
                        const auto* active = played ? &history : nullptr;
                        const int depth = std::string_view(fen).starts_with("rnbq") && !exchange ? 3 : 2;
                        equivalent(trickfish::iterative_search(root, depth, options, {}, active),
                            trickfish::iterative_search(root, depth, reference, {}, active));
                        equivalent(trickfish::iterative_search(root, depth, options, {32, {}, {}}, active),
                            trickfish::iterative_search(root, depth, reference, {32, {}, {}}, active));
                        require(root.to_fen() == fen && root.key() == key && history.size() == 1,
                            "ordering comparison changed root/history");
                    }
                }
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
