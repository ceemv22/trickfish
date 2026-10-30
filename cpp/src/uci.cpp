#include "trickfish/uci.hpp"

#include <algorithm>
#include <charconv>
#include <cctype>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <cstdint>
#include <istream>
#include <mutex>
#include <optional>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <stop_token>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "trickfish/evaluation.hpp"
#include "trickfish/movegen.hpp"
#include "trickfish/search.hpp"
#include "trickfish/time.hpp"

namespace trickfish {
namespace {

constexpr std::string_view starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

std::vector<std::string> tokens_for(std::string_view command) {
    std::istringstream input{std::string(command)};
    std::vector<std::string> tokens;
    for (std::string word; input >> word;) tokens.push_back(std::move(word));
    return tokens;
}

void validate_root(const Position& position) {
    if (position.in_check(opposite(position.side_to_move()))) {
        throw std::invalid_argument("non-moving king is in check");
    }
    for (std::uint8_t file = 0; file < 8; ++file) {
        for (const auto square : {file, static_cast<std::uint8_t>(56 + file)}) {
            const auto piece = position.piece_at(square);
            if (piece == 'P' || piece == 'p') {
                throw std::invalid_argument("pawn on a promotion rank");
            }
        }
    }
    if (position.en_passant_square() >= 0) {
        const int rank = position.en_passant_square() / 8;
        if (rank != (position.side_to_move() == Color::white ? 2 : 5)) {
            throw std::invalid_argument("en passant rank does not match side to move");
        }
    }
}

std::uint64_t number_for(const std::string& text) {
    std::uint64_t value = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
    if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) {
        throw std::invalid_argument("invalid non-negative integer: " + text);
    }
    return value;
}

struct CheckOption {
    std::string_view name;
    bool SearchOptions::*member;
};

struct SpinOption {
    std::string_view name;
    int SearchOptions::*member;
    int minimum;
    int maximum;
};

constexpr CheckOption check_options[] = {
    {"Experimental Exchange Ordering", &SearchOptions::use_exchange_ordering},
    {"Experimental Null Move", &SearchOptions::use_null_move},
    {"Experimental LMR", &SearchOptions::use_lmr},
    {"Experimental Futility", &SearchOptions::use_futility},
    {"Experimental Razoring", &SearchOptions::use_razoring},
    {"Experimental Check Extensions", &SearchOptions::use_check_extensions},
    {"Experimental Correction History", &SearchOptions::use_correction},
    {"Experimental Endgame Scaling", &SearchOptions::use_endgame_scaling},
    {"Experimental Mate Distance Pruning", &SearchOptions::use_mate_distance}
};

constexpr SpinOption spin_options[] = {
    {"Futility Margin", &SearchOptions::futility_margin, 0, 10000},
    {"Razor Margin", &SearchOptions::razor_margin, 0, 10000},
    {"Check Extension Limit", &SearchOptions::check_extension_limit, 0, 4}
};

std::string lowercase(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char character) {
        return static_cast<char>(std::tolower(character));
    });
    return text;
}

struct GoLimits {
    int depth = 64;
    std::optional<std::uint64_t> nodes;
    std::optional<std::chrono::steady_clock::time_point> deadline;
    bool infinite = false;
    std::vector<Move> root_moves;
};

std::chrono::steady_clock::time_point deadline_after(std::uint64_t milliseconds) {
    const auto now = std::chrono::steady_clock::now();
    const auto maximum = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::time_point::max() - now).count();
    if (milliseconds > static_cast<std::uint64_t>(maximum)) {
        throw std::invalid_argument("time budget is too large");
    }
    return now + std::chrono::milliseconds(static_cast<std::chrono::milliseconds::rep>(milliseconds));
}

GoLimits parse_go(const std::vector<std::string>& tokens, Position& position, std::uint64_t overhead) {
    GoLimits limits;
    limits.infinite = tokens.size() == 1;
    const auto side = position.side_to_move();
    bool searchmoves_seen = false;
    ClockControl clock;
    bool has_clock_parameters = false;
    std::optional<std::uint64_t> movetime;
    for (std::size_t index = 1; index < tokens.size(); ++index) {
        const auto& name = tokens[index];
        if (name == "searchmoves") {
            if (searchmoves_seen) throw std::invalid_argument("duplicate searchmoves parameter");
            searchmoves_seen = true;
            const auto legal = generate_legal_moves(position);
            const std::vector<std::string> parameters = {"infinite", "depth", "nodes", "movetime", "wtime",
                "btime", "winc", "binc", "movestogo", "searchmoves", "ponder", "mate"};
            while (index + 1 < tokens.size() &&
                std::find(parameters.begin(), parameters.end(), tokens[index + 1]) == parameters.end()) {
                const auto& text = tokens[++index];
                const auto found = std::find_if(legal.begin(), legal.end(), [&](const Move& move) {
                    return move.to_uci() == text;
                });
                if (found == legal.end() || std::find(limits.root_moves.begin(), limits.root_moves.end(), *found) != limits.root_moves.end()) {
                    throw std::invalid_argument("searchmoves requires unique legal root moves");
                }
                limits.root_moves.push_back(*found);
            }
            if (limits.root_moves.empty()) throw std::invalid_argument("searchmoves requires at least one move");
            continue;
        }
        if (name == "infinite") {
            limits.infinite = true;
            continue;
        }
        if (name != "depth" && name != "nodes" && name != "movetime" && name != "wtime" &&
            name != "btime" && name != "winc" && name != "binc" && name != "movestogo") {
            throw std::invalid_argument("unsupported go parameter: " + name);
        }
        if (++index == tokens.size()) throw std::invalid_argument("missing go parameter value");
        const auto value = number_for(tokens[index]);
        if (name == "depth") {
            if (value < 1 || value > 64) throw std::invalid_argument("depth must be between 1 and 64");
            limits.depth = static_cast<int>(value);
        } else if (name == "nodes") {
            limits.nodes = value;
        } else if (name == "movetime") {
            movetime = value;
        } else {
            has_clock_parameters = true;
            if (name == "wtime") clock.white_time = value;
            else if (name == "btime") clock.black_time = value;
            else if (name == "winc") clock.white_increment = value;
            else if (name == "binc") clock.black_increment = value;
            else {
                if (value == 0) throw std::invalid_argument("movestogo must be positive");
                clock.moves_to_go = value;
            }
        }
    }
    if (!limits.infinite) {
        if (movetime) {
            limits.deadline = deadline_after(*movetime);
        } else if (has_clock_parameters) {
            const auto budget = allocate_clock_time(side, clock, overhead);
            if (!budget) throw std::invalid_argument("missing time for the side to move");
            limits.deadline = deadline_after(*budget);
        }
    }
    return limits;
}

class UciSession {
public:
    UciSession(std::istream& input, std::ostream& output)
        : input_(input), output_(output), position_(Position::from_fen(starting_fen)), history_(position_) {}

    ~UciSession() { stop_search(); }

    int run() {
        for (std::string command; std::getline(input_, command);) {
            const auto tokens = tokens_for(command);
            if (tokens.empty()) continue;
            try {
                const auto& name = tokens[0];
                if (name == "uci") {
                    emit("id name Trickfish C++\nid author ceemv22\noption name Move Overhead type spin default " +
                        std::to_string(default_move_overhead_ms) + " min 0 max 10000");
                    const SearchOptions defaults;
                    for (const auto& option : check_options) {
                        emit("option name " + std::string(option.name) + " type check default " +
                            (defaults.*option.member ? "true" : "false"));
                    }
                    for (const auto& option : spin_options) {
                        emit("option name " + std::string(option.name) + " type spin default " +
                            std::to_string(defaults.*option.member) + " min " + std::to_string(option.minimum) +
                            " max " + std::to_string(option.maximum));
                    }
                    emit("uciok");
                } else if (name == "isready") {
                    emit("readyok");
                } else if (name == "quit") {
                    break;
                } else if (name == "stop") {
                    stop_search();
                } else if (name == "ucinewgame") {
                    stop_search();
                    auto next = parse_uci_position("position startpos");
                    position_ = std::move(next.position);
                    history_ = std::move(next.history);
                } else if (name == "position") {
                    stop_search();
                    auto next = parse_uci_position(command);
                    position_ = std::move(next.position);
                    history_ = std::move(next.history);
                } else if (name == "go") {
                    stop_search();
                    start_search(parse_go(tokens, position_, move_overhead_));
                } else if (name == "setoption") {
                    set_option(tokens);
                } else if (name == "ponderhit") {
                    emit("info string unsupported command: " + name);
                }
            } catch (const std::exception& error) {
                emit("info string error: " + std::string(error.what()));
            }
        }
        stop_search();
        return 0;
    }

private:
    void set_option(const std::vector<std::string>& tokens) {
        if (tokens.size() < 5 || tokens[1] != "name") throw std::invalid_argument("invalid setoption command");
        const auto value = std::find(tokens.begin() + 2, tokens.end(), "value");
        if (value == tokens.end() || value + 1 == tokens.end() || value + 2 != tokens.end()) {
            throw std::invalid_argument("setoption requires one value");
        }
        std::string name;
        for (auto word = tokens.begin() + 2; word != value; ++word) {
            if (!name.empty()) name += ' ';
            name += *word;
        }
        name = lowercase(std::move(name));
        if (name == "move overhead") {
            const auto overhead = number_for(*(value + 1));
            if (overhead > 10000) throw std::invalid_argument("Move Overhead must be between 0 and 10000");
            move_overhead_ = overhead;
            return;
        }
        for (const auto& option : check_options) {
            if (name != lowercase(std::string(option.name))) continue;
            const auto selected = lowercase(*(value + 1));
            if (selected != "true" && selected != "false") throw std::invalid_argument("check option requires true or false");
            search_options_.*option.member = selected == "true";
            return;
        }
        for (const auto& option : spin_options) {
            if (name != lowercase(std::string(option.name))) continue;
            const auto selected = number_for(*(value + 1));
            if (selected < static_cast<std::uint64_t>(option.minimum) || selected > static_cast<std::uint64_t>(option.maximum)) {
                throw std::invalid_argument("spin option value is out of range");
            }
            search_options_.*option.member = static_cast<int>(selected);
            return;
        }
        throw std::invalid_argument("unsupported option: " + name);
    }

    void emit(const std::string& text) {
        std::lock_guard lock(output_mutex_);
        output_ << text << '\n' << std::flush;
    }

    void stop_search() {
        if (worker_.joinable()) {
            worker_.request_stop();
            worker_.join();
        }
    }

    void emit_result(const SearchResult& result) {
        std::ostringstream message;
        message << "info depth " << result.completed_depth << " nodes " << result.nodes;
        if (result.completed_depth > 0) {
            if (std::abs(result.score) >= mate_threshold) {
                const int moves = (mate_score - std::abs(result.score) + 1) / 2;
                message << " score mate " << (result.score < 0 ? -moves : moves);
            } else {
                message << " score cp " << result.score;
            }
        }
        if (!result.principal_variation.empty()) {
            message << " pv";
            for (const auto& move : result.principal_variation) message << ' ' << move.to_uci();
        }
        message << "\nbestmove " << (result.best_move ? result.best_move->to_uci() : "0000");
        emit(message.str());
    }

    void start_search(GoLimits limits) {
        worker_ = std::jthread([this, root = position_, history = history_, limits, options = search_options_](std::stop_token stop) mutable {
            try {
                const SearchLimits search_limits{limits.nodes, limits.deadline,
                    [stop] { return stop.stop_requested(); }};
                options.root_moves = limits.root_moves;
                const auto result = iterative_search(root, limits.depth, options, search_limits, &history);
                if (limits.infinite && !stop.stop_requested()) {
                    std::mutex wait_mutex;
                    std::unique_lock lock(wait_mutex);
                    std::condition_variable_any condition;
                    condition.wait(lock, stop, [] { return false; });
                }
                emit_result(result);
            } catch (const std::exception& error) {
                emit("info string search error: " + std::string(error.what()) + "\nbestmove 0000");
            }
        });
    }

    std::istream& input_;
    std::ostream& output_;
    Position position_;
    RepetitionHistory history_;
    SearchOptions search_options_;
    std::uint64_t move_overhead_ = default_move_overhead_ms;
    std::mutex output_mutex_;
    std::jthread worker_;
};

}

UciPosition parse_uci_position(std::string_view command) {
    const auto tokens = tokens_for(command);
    if (tokens.size() < 2 || tokens[0] != "position") {
        throw std::invalid_argument("position requires startpos or fen");
    }
    std::string fen;
    std::size_t move_index = 0;
    if (tokens[1] == "startpos") {
        fen = starting_fen;
        move_index = 2;
    } else if (tokens[1] == "fen" && tokens.size() >= 8) {
        for (std::size_t index = 2; index < 8; ++index) {
            if (!fen.empty()) fen += ' ';
            fen += tokens[index];
        }
        move_index = 8;
    } else {
        throw std::invalid_argument("position requires startpos or six FEN fields");
    }
    auto position = Position::from_fen(fen);
    validate_root(position);
    RepetitionHistory history(position);
    if (move_index < tokens.size()) {
        if (tokens[move_index++] != "moves") throw std::invalid_argument("expected moves after position");
        for (; move_index < tokens.size(); ++move_index) {
            const auto legal = generate_legal_moves(position);
            const auto found = std::find_if(legal.begin(), legal.end(), [&](const Move& move) {
                return move.to_uci() == tokens[move_index];
            });
            if (found == legal.end()) throw std::invalid_argument("illegal move: " + tokens[move_index]);
            const auto undo = position.make_move(*found);
            static_cast<void>(undo);
            history.push(position);
        }
    }
    return {std::move(position), std::move(history)};
}

int run_uci(std::istream& input, std::ostream& output) {
    UciSession session(input, output);
    return session.run();
}

}
