#include <algorithm>
#include <iostream>
#include <stdexcept>

#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

class FixtureTablebase final : public TablebaseProvider {
public:
    int wdl = 4;
    bool missing = false;
    bool corrupt = false;
    mutable int calls = 0;
    std::optional<TablebaseRoot> probe(const Position& position) const override {
        ++calls;
        if (missing) return std::nullopt;
        auto root = position;
        const auto legal = generate_legal_moves(root);
        TablebaseRoot result{legal[0], wdl, 3, {}};
        for (const auto& move : legal) result.moves.push_back({move, wdl, 3});
        if (corrupt) result.moves[0].wdl = 8;
        return result;
    }
};

int main() {
    try {
        auto root = Position::from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1");
        const auto fen = root.to_fen();
        const auto key = root.key();
        auto provider = std::make_shared<FixtureTablebase>();
        SearchOptions options;
        options.tablebase = provider;
        const auto ordinary = iterative_search(root, 2, options);
        require(!ordinary.tablebase_used && provider->calls == 0, "automatic-only draw policy used fifty-move oracle");
        options.draw_policy = MoveCountDrawPolicy::claim_fifty_moves;
        const auto legal = generate_legal_moves(root);
        for (int wdl = 0; wdl <= 4; ++wdl) {
            provider->wdl = wdl;
            const auto result = iterative_search(root, 2, options);
            require(result.tablebase_used && result.score == tablebase_score(wdl) && result.best_move == legal[0] &&
                result.completed_depth == 2 && result.nodes > 0, "tablebase root score/filter mismatch");
            require(!result.principal_variation.empty() && result.principal_variation.front() == result.best_move,
                "tablebase filtering lost PV");
            require(root.to_fen() == fen && root.key() == key, "tablebase search changed root");
        }
        options.root_moves = {legal[1]};
        require(iterative_search(root, 2, options).best_move == legal[1], "tablebase escaped restricted root");
        options.root_moves.clear();
        provider->missing = true;
        require(!iterative_search(root, 2, options).tablebase_used, "missing table fabricated an oracle result");
        provider->missing = false;
        provider->corrupt = true;
        require(!iterative_search(root, 2, options).tablebase_used, "corrupt provider outcome accepted");
        provider->corrupt = false;
        RepetitionHistory history(root);
        history.push(root);
        const int before = provider->calls;
        require(!iterative_search(root, 2, options, {}, &history).tablebase_used && provider->calls == before,
            "repeated root used history-free tablebase score");
        history.pop();
        const auto undo = root.make_move(legal[0]);
        history.push(root);
        if (root.halfmove_clock() != 0) {
            require(!iterative_search(root, 2, options, {}, &history).tablebase_used,
                "nonzero reversible history used history-free tablebase score");
        }
        history.pop();
        root.unmake_move(legal[0], undo);
        SearchLimits limits;
        limits.nodes = 0;
        const int prior = provider->calls;
        const auto stopped = iterative_search(root, 2, options, limits);
        require(stopped.stopped && stopped.nodes == 0 && !stopped.tablebase_used && provider->calls == prior,
            "zero budget probed tablebase before cancellation");
        for (const auto terminal : {"7k/6Q1/6K1/8/8/8/8/8 b - - 150 1", "4k3/8/8/8/8/8/8/4K3 w - - 0 1"}) {
            auto position = Position::from_fen(terminal);
            require(!iterative_search(position, 2, options).tablebase_used, "tablebase overrode terminal precedence");
        }
        require(tablebase_score(0) == -50000 && tablebase_score(1) == 0 && tablebase_score(2) == 0 &&
            tablebase_score(3) == 0 && tablebase_score(4) == 50000, "WDL rule50 score mapping mismatch");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
