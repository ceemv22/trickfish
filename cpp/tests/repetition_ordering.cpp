#include <algorithm>
#include <array>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <vector>

#include "trickfish/history.hpp"
#include "trickfish/move_table.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/multipv.hpp"
#include "trickfish/search.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void check_history(const Position& root, const RepetitionHistory& history, const std::vector<std::uint64_t>& keys) {
    const auto count = static_cast<std::size_t>(std::count(keys.begin(), keys.end(), root.key()));
    require(history.current_key() == root.key() && history.size() == keys.size() && history.current_count() == count &&
        history.can_claim_threefold_repetition() == (count >= 3), "indexed repetition differs from linear history");
}

void walk_history(Position& root, RepetitionHistory& history, std::vector<std::uint64_t>& keys, int depth) {
    check_history(root, history, keys);
    if (depth == 0) return;
    const auto fen = root.to_fen();
    for (const auto& move : generate_legal_moves(root)) {
        const auto undo = root.make_move(move);
        history.push(root);
        keys.push_back(root.key());
        walk_history(root, history, keys, depth - 1);
        history.pop();
        keys.pop_back();
        root.unmake_move(move, undo);
        check_history(root, history, keys);
        require(root.to_fen() == fen, "history traversal changed root");
    }
}

void check_line(Position root, const SearchResult& result) {
    if (result.best_move) {
        const auto legal = generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), *result.best_move) != legal.end(), "illegal ordering best move");
    }
    if (!result.principal_variation.empty()) require(result.best_move == result.principal_variation.front(), "ordering PV root mismatch");
    for (const auto& move : result.principal_variation) {
        const auto legal = generate_legal_moves(root);
        require(std::find(legal.begin(), legal.end(), move) != legal.end(), "illegal ordering PV");
        const auto undo = root.make_move(move);
        static_cast<void>(undo);
    }
}

SearchResult compare(Position& root, const RepetitionHistory& history, int depth, SearchOptions options = {}) {
    const auto fen = root.to_fen();
    const auto count = history.current_count();
    const auto size = history.size();
    options.use_repetition_ordering = false;
    const auto reference = iterative_search(root, depth, options, {}, &history);
    options.use_repetition_ordering = true;
    const auto candidate = iterative_search(root, depth, options, {}, &history);
    require(candidate.score == reference.score && candidate.completed_depth == reference.completed_depth &&
        !candidate.stopped && !reference.stopped, "repetition move ordering changed exhaustive score");
    require(reference.transposition_hits == 0, "reference history search used TT scores");
    check_line(root, candidate);
    require(root.to_fen() == fen && history.size() == size && history.current_count() == count,
        "ordering changed caller state");
    return candidate;
}

void check_storage() {
    MoveOrderingTable table(2);
    const Move first(52, 36), second(51, 35), promotion(8, 0, 'n');
    require(table.capacity() == 2 && !table.probe(0), "empty move table mismatch");
    table.store(0, first);
    require(table.probe(0) == first && !table.probe(2), "zero key or collision probe mismatch");
    table.store(1, second);
    table.store(2, promotion);
    require(!table.probe(0) && table.probe(2) == promotion && table.probe(1) == second, "move collision replacement mismatch");
    table.store(2, first);
    require(table.probe(2) == first, "same-key hint did not update");
    table.clear();
    require(!table.probe(1) && !table.probe(2) && table.capacity() == 2, "move table clear mismatch");
    bool rejected = false;
    try { MoveOrderingTable invalid(0); } catch (const std::invalid_argument&) { rejected = true; }
    require(rejected, "zero move-table capacity accepted");
}

void check_repeated_path() {
    auto root = Position::from_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    RepetitionHistory history(root);
    std::vector<std::uint64_t> keys{root.key()};
    const std::array<Move, 4> cycle{Move(62, 45), Move(6, 21), Move(45, 62), Move(21, 6)};
    std::vector<UndoState> undos;
    for (std::size_t index = 0; index < 256; ++index) {
        undos.push_back(root.make_move(cycle[index % 4]));
        history.push(root);
        keys.push_back(root.key());
        check_history(root, history, keys);
        if (index == 6) {
            const auto result = compare(root, history, 2);
            require(result.score == 0 && result.best_move == cycle[3], "move hint masked a child repetition");
        }
        if (index == 7) {
            const auto result = compare(root, history, 2);
            require(result.score == 0 && result.transposition_hits == 0, "root repetition bypassed terminal precedence");
        }
    }
    auto copy = history;
    copy.pop();
    require(history.size() == 257 && copy.size() == 256 && history.current_count() == 65, "history copy shared counts");
    for (std::size_t index = undos.size(); index > 0; --index) {
        history.pop();
        keys.pop_back();
        root.unmake_move(cycle[(index - 1) % 4], undos[index - 1]);
        check_history(root, history, keys);
    }
    walk_history(root, history, keys, 2);
    bool rejected = false;
    try { history.pop(); } catch (const std::underflow_error&) { rejected = true; }
    require(rejected && history.size() == 1 && history.current_count() == 1, "underflow corrupted index");
}

void check_cancellation() {
    auto root = Position::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    RepetitionHistory history(root);
    const auto fen = root.to_fen();
    SearchOptions options;
    options.use_repetition_ordering = true;
    const auto first = iterative_search(root, 1, options, {}, &history);
    SearchLimits limits;
    limits.nodes = first.nodes + 3;
    const auto stopped = iterative_search(root, 4, options, limits, &history);
    require(stopped.stopped && stopped.completed_depth == 1 && stopped.score == first.score &&
        stopped.nodes == *limits.nodes, "ordering interruption lost completed depth or exceeded budget");
    check_line(root, stopped);
    limits.nodes = 0;
    require(iterative_search(root, 3, options, limits, &history).nodes == 0, "zero-node ordering fallback searched");
    limits = {};
    limits.deadline = std::chrono::steady_clock::time_point::min();
    require(iterative_search(root, 3, options, limits, &history).completed_depth == 0, "expired ordering deadline searched");
    limits = {};
    int polls = 0;
    limits.stop_requested = [&polls] {
        if (++polls == 30) throw std::runtime_error("injected stop failure");
        return false;
    };
    bool threw = false;
    try { static_cast<void>(iterative_search(root, 3, options, limits, &history)); }
    catch (const std::runtime_error&) { threw = true; }
    require(threw && polls == 30 && root.to_fen() == fen && history.size() == 1 && history.current_count() == 1,
        "exception did not restore indexed history/root");
    const auto after = iterative_search(root, 3, options, {}, &history);
    const auto again = iterative_search(root, 3, options, {}, &history);
    require(after.nodes == again.nodes && after.principal_variation == again.principal_variation &&
        after.transposition_hits == again.transposition_hits, "move hints leaked between searches");
    auto plain_options = options;
    plain_options.use_repetition_ordering = false;
    const auto plain = iterative_search(root, 3, plain_options);
    const auto no_history = iterative_search(root, 3, options);
    require(plain.score == no_history.score && plain.nodes == no_history.nodes &&
        plain.principal_variation == no_history.principal_variation &&
        plain.transposition_hits == no_history.transposition_hits, "history option changed standalone search trace");
    options.use_table = false;
    require(iterative_search(root, 3, options, {}, &history).transposition_hits == 0, "table master switch ignored");
}

int main() {
    try {
        check_storage();
        check_repeated_path();
        check_cancellation();
        std::uint64_t hits = 0;
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/ppp2ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
            "4k3/8/8/8/8/8/q7/R3K3 w - - 99 1",
            "7k/6Q1/6K1/8/8/8/8/8 b - - 150 1"}) {
            auto root = Position::from_fen(fen);
            RepetitionHistory history(root);
            std::vector<std::uint64_t> keys{root.key()};
            walk_history(root, history, keys, 2);
            for (const bool pvs : {false, true}) {
                SearchOptions options;
                options.use_pvs = pvs;
                options.aspiration_window = pvs ? 25 : 0;
                options.use_killers = pvs;
                options.use_history = pvs;
                options.use_continuation = pvs;
                options.draw_policy = MoveCountDrawPolicy::claim_fifty_moves;
                options.use_pawn_cache = pvs;
                hits += compare(root, history, 3, options).transposition_hits;
            }
            const auto legal = generate_legal_moves(root);
            if (!legal.empty()) {
                SearchOptions restricted;
                restricted.root_moves = {legal[0]};
                require(compare(root, history, 2, restricted).best_move == legal[0] || root.halfmove_clock() >= 150,
                    "hint escaped restricted root");
                restricted.root_moves.clear();
                restricted.use_repetition_ordering = true;
                const auto lines = iterative_multi_pv(root, 2, 3, restricted, {}, &history);
                for (const auto& line : lines.lines) check_line(root, line);
            }
        }
        require(hits > 0, "repetition move-ordering reuse was not exercised");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
