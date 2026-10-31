#include <algorithm>
#include <chrono>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "trickfish/movegen.hpp"
#include "trickfish/multipv.hpp"

using namespace trickfish;

constexpr auto initial = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void same_line(const SearchResult& left, const SearchResult& right) {
    require(left.score == right.score && left.best_move == right.best_move &&
        left.principal_variation == right.principal_variation && left.completed_depth == right.completed_depth,
        "MultiPV changed saved line");
}

MultiPVResult checked(Position& root, int depth, int count, const SearchOptions& options = {},
    const SearchLimits& limits = {}, const RepetitionHistory* history = nullptr) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    const auto phase = root.phase_units();
    const auto history_size = history == nullptr ? 0 : history->size();
    const auto history_count = history == nullptr ? 0 : history->current_count();
    const auto result = iterative_multi_pv(root, depth, count, options, limits, history);
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && root.phase_units() == phase,
        "MultiPV changed caller position");
    if (history != nullptr) require(history->size() == history_size && history->current_key() == key &&
        history->current_count() == history_count, "MultiPV changed caller history");
    if (limits.nodes) require(result.nodes <= *limits.nodes, "MultiPV exceeded shared node limit");
    std::vector<Move> selected;
    std::uint64_t line_work = 0;
    for (const auto& line : result.lines) {
        require(line.completed_depth == result.completed_depth, "MultiPV mixed completed depths");
        line_work += line.nodes;
        if (line.best_move) {
            require(std::find(selected.begin(), selected.end(), *line.best_move) == selected.end(), "MultiPV repeated root move");
            selected.push_back(*line.best_move);
            if (!options.root_moves.empty()) require(std::find(options.root_moves.begin(), options.root_moves.end(), *line.best_move) !=
                options.root_moves.end(), "MultiPV escaped root restriction");
        }
        if (line.completed_depth > 0 && line.best_move) require(!line.principal_variation.empty() &&
            line.principal_variation.front() == line.best_move, "MultiPV best move/PV disagree");
        auto position = root;
        for (const auto& move : line.principal_variation) {
            const auto legal = generate_legal_moves(position);
            require(std::find(legal.begin(), legal.end(), move) != legal.end(), "MultiPV returned illegal PV");
            const auto undo = position.make_move(move);
            static_cast<void>(undo);
        }
    }
    require(line_work <= result.nodes, "MultiPV lost aggregate work");
    for (std::size_t index = 1; index < result.lines.size(); ++index) {
        require(result.lines[index - 1].score >= result.lines[index].score, "MultiPV scores are not ranked");
    }
    return result;
}

void forced_root_oracle(Position& root, int depth, int count, SearchOptions options = {}) {
    options.use_table = false;
    auto allowed = options.root_moves;
    if (allowed.empty()) {
        const auto legal = generate_legal_moves(root);
        allowed.assign(legal.begin(), legal.end());
    }
    std::vector<int> scores;
    for (const auto& move : allowed) {
        auto forced = options;
        forced.root_moves = {move};
        scores.push_back(iterative_search(root, depth, forced).score);
    }
    std::sort(scores.begin(), scores.end(), std::greater<int>{});
    const auto result = checked(root, depth, count, options);
    require(!result.stopped && result.completed_depth == depth &&
        result.lines.size() == std::min(static_cast<std::size_t>(count), allowed.size()), "MultiPV did not complete requested batch");
    for (std::size_t index = 0; index < result.lines.size(); ++index) {
        const auto& line = result.lines[index];
        require(line.score == scores[index], "MultiPV ranking differs from exhaustive forced-root scores");
        auto forced = options;
        forced.root_moves = {*line.best_move};
        require(iterative_search(root, depth, forced).score == line.score, "MultiPV line score differs from forced root");
        require(line.transposition_hits == 0, "MultiPV reused restricted-root TT state");
    }
}

int main() {
    try {
        auto root = Position::from_fen(initial);
        const auto ordinary = iterative_search(root, 2);
        const auto single = checked(root, 2, 1);
        require(single.lines.size() == 1 && single.nodes == ordinary.nodes &&
            single.lines.front().transposition_hits == ordinary.transposition_hits, "single-PV delegation changed work");
        same_line(single.lines.front(), ordinary);
        forced_root_oracle(root, 2, 3);
        for (const auto fen : {"4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
                "4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1",
                "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
                "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
                "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
                "4k3/8/8/8/8/8/q7/R3K3 w - - 0 1", "7k/8/5KQ1/8/8/8/8/8 w - - 0 1"}) {
            auto position = Position::from_fen(fen);
            forced_root_oracle(position, 1, 4);
        }
        SearchOptions restricted;
        restricted.root_moves = {Move(52, 36), Move(51, 35)};
        forced_root_oracle(root, 2, maximum_multi_pv, restricted);
        restricted.use_exchange_ordering = true;
        restricted.use_pawn_cache = true;
        restricted.use_endgame_scaling = true;
        forced_root_oracle(root, 2, 2, restricted);
        const auto complete = checked(root, 1, 3);
        SearchLimits limits;
        limits.nodes = complete.nodes + 1;
        const auto interrupted = checked(root, 3, 3, {}, limits);
        require(interrupted.stopped && interrupted.completed_depth == 1 && interrupted.lines.size() == 3 &&
            interrupted.nodes == *limits.nodes, "interrupted batch replaced prior completed iteration");
        for (std::size_t index = 0; index < complete.lines.size(); ++index) same_line(complete.lines[index], interrupted.lines[index]);
        for (const auto budget : {0ULL, 1ULL, 7ULL, 32ULL, 128ULL}) {
            limits.nodes = budget;
            const auto limited = checked(root, 4, 3, restricted, limits);
            require(limited.stopped, "small shared budget did not interrupt MultiPV");
        }
        limits = {};
        limits.deadline = std::chrono::steady_clock::now() - std::chrono::milliseconds(1);
        const auto expired = checked(root, 3, 3, {}, limits);
        require(expired.stopped && expired.completed_depth == 0 && expired.nodes == 0 && expired.lines.size() == 1,
            "expired deadline did not preserve legal fallback");
        limits = {};
        limits.stop_requested = [] { return true; };
        const auto stopped = checked(root, 3, 3, {}, limits);
        require(stopped.stopped && stopped.nodes == 0 && stopped.completed_depth == 0, "external stop was not shared");
        limits.stop_requested = [remaining = 50]() mutable { return --remaining <= 0; };
        const auto stateful_stop = checked(root, 1, 16, {}, limits);
        require(stateful_stop.stopped && stateful_stop.completed_depth == 0 && stateful_stop.nodes < 50,
            "MultiPV reset mutable stop callback between ranks");
        RepetitionHistory history(root);
        checked(root, 2, 3, {}, {}, &history);
        history.push(root);
        history.push(root);
        const auto repeated = checked(root, 2, 4, {}, {}, &history);
        require(repeated.lines.size() == 1 && repeated.lines.front().score == 0, "repetition root produced competing lines");
        for (const auto fen : {"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
                "4k3/8/8/8/8/8/8/4K3 w - - 0 1", "4k3/8/8/8/8/8/R7/4K3 w - - 150 1"}) {
            auto terminal = Position::from_fen(fen);
            const auto normal = iterative_search(terminal, 2);
            const auto result = checked(terminal, 2, 4);
            require(result.lines.size() == 1, "terminal root returned multiple variations");
            same_line(normal, result.lines.front());
        }
        for (int invalid = 0; invalid < 8; ++invalid) {
            bool rejected = false;
            SearchOptions options;
            if (invalid == 4) options.aspiration_window = -1;
            if (invalid == 5) options.root_moves = {Move(52, 36), Move(52, 36)};
            if (invalid == 6) options.root_moves = {Move(52, 12)};
            auto other = Position::from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1");
            RepetitionHistory wrong(other);
            try { static_cast<void>(iterative_multi_pv(root, invalid == 2 ? 0 : invalid == 3 ? 65 : 1,
                invalid == 0 ? 0 : invalid == 1 ? 17 : 3, options, {}, invalid == 7 ? &wrong : nullptr)); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected && root.to_fen() == initial, "invalid MultiPV configuration accepted or mutated root");
        }
        limits = {};
        int visits = 0;
        limits.stop_requested = [&visits] { if (++visits == 5) throw std::runtime_error("injected stop failure"); return false; };
        bool propagated = false;
        RepetitionHistory clean_history(root);
        const auto key = root.key();
        try { static_cast<void>(iterative_multi_pv(root, 3, 3, {}, limits, &clean_history)); }
        catch (const std::runtime_error&) { propagated = true; }
        require(propagated && root.to_fen() == initial && root.key() == key && clean_history.size() == 1,
            "stop callback exception corrupted caller state");
        std::cout << "MultiPV ranking, budgets, reference and restoration checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
