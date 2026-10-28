#pragma once

#include <array>
#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdlib>

#include "trickfish/game_status.hpp"
#include "trickfish/position.hpp"

namespace trickfish {

inline constexpr int mate_score = 100000;
inline constexpr std::array piece_values = {100, 320, 330, 500, 900, 0};

[[nodiscard]] inline int evaluate_material(const Position& position) {
    int score = 0;
    for (std::size_t type = 0; type < piece_values.size(); ++type) {
        const auto piece = static_cast<PieceType>(type);
        score += piece_values[type] * (std::popcount(position.pieces(Color::white, piece)) -
            std::popcount(position.pieces(Color::black, piece)));
    }
    return score;
}

[[nodiscard]] inline int evaluate_bishop_pair(const Position& position) {
    const int white = std::popcount(position.pieces(Color::white, PieceType::bishop)) >= 2 ? 30 : 0;
    const int black = std::popcount(position.pieces(Color::black, PieceType::bishop)) >= 2 ? 30 : 0;
    return white - black;
}

[[nodiscard]] inline int evaluate_rook_files(const Position& position) {
    const auto white_pawns = position.pieces(Color::white, PieceType::pawn);
    const auto black_pawns = position.pieces(Color::black, PieceType::pawn);
    if ((white_pawns | black_pawns) == 0) {
        return 0;
    }
    int score = 0;
    constexpr Bitboard a_file = 0x0101010101010101ULL;
    for (const auto color : {Color::white, Color::black}) {
        const auto own_pawns = color == Color::white ? white_pawns : black_pawns;
        const auto enemy_pawns = color == Color::white ? black_pawns : white_pawns;
        auto rooks = position.pieces(color, PieceType::rook);
        while (rooks != 0) {
            const auto file = pop_lsb(rooks) % 8;
            const auto mask = a_file << file;
            const int bonus = ((own_pawns & mask) == 0 ? 10 : 0) + ((enemy_pawns & mask) == 0 ? 10 : 0);
            score += color == Color::white ? bonus : -bonus;
        }
    }
    return score;
}

inline constexpr int evaluation_max_phase = 24;

[[nodiscard]] inline int game_phase(const Position& position) {
    constexpr std::array weights = {0, 1, 1, 2, 4, 0};
    int phase = 0;
    for (std::size_t type = 0; type < weights.size(); ++type) {
        const auto piece = static_cast<PieceType>(type);
        phase += weights[type] * (std::popcount(position.pieces(Color::white, piece)) +
            std::popcount(position.pieces(Color::black, piece)));
    }
    return std::min(evaluation_max_phase, phase);
}

namespace detail {

inline int pawn_structure_for_side(const Position& position, Color color, int phase) {
    const auto pawns = position.pieces(color, PieceType::pawn);
    const auto enemy_pawns = position.pieces(opposite(color), PieceType::pawn);
    std::array<int, 8> files{};
    auto sources = pawns;
    while (sources != 0) ++files[pop_lsb(sources) % 8];
    int score = 0;
    for (const int count : files) {
        if (count > 1) score -= 15 * (count - 1);
    }
    sources = pawns;
    while (sources != 0) {
        const auto square = pop_lsb(sources);
        const int rank = square / 8;
        const int file = square % 8;
        if ((file == 0 || files[static_cast<std::size_t>(file - 1)] == 0) &&
            (file == 7 || files[static_cast<std::size_t>(file + 1)] == 0)) {
            score -= 12;
        }
        bool passed = true;
        auto enemies = enemy_pawns;
        while (enemies != 0) {
            const auto enemy = pop_lsb(enemies);
            const int enemy_rank = enemy / 8;
            const int enemy_file = enemy % 8;
            const bool ahead = color == Color::white ? enemy_rank < rank : enemy_rank > rank;
            if (ahead && std::abs(enemy_file - file) <= 1) {
                passed = false;
                break;
            }
        }
        if (passed) {
            const int advance = color == Color::white ? 6 - rank : rank - 1;
            const int scaled = (evaluation_max_phase - phase) * 2 * advance;
            int endgame_bonus = scaled / evaluation_max_phase;
            if (scaled < 0 && scaled % evaluation_max_phase != 0) --endgame_bonus;
            score += 8 + 8 * advance + endgame_bonus;
        }
    }
    return score;
}

inline int pawn_structure_total(const Position& position, int phase) {
    return pawn_structure_for_side(position, Color::white, phase) -
        pawn_structure_for_side(position, Color::black, phase);
}

}

[[nodiscard]] inline int evaluate_pawn_structure(const Position& position) {
    return detail::pawn_structure_total(position, game_phase(position));
}

struct EvaluationBreakdown {
    int phase = 0;
    int material = 0;
    int pawn_structure = 0;
    int bishop_pair = 0;
    int rook_files = 0;

    [[nodiscard]] int total() const { return material + pawn_structure + bishop_pair + rook_files; }
};

[[nodiscard]] inline EvaluationBreakdown evaluate_breakdown(const Position& position) {
    const auto phase = game_phase(position);
    return {phase, evaluate_material(position), detail::pawn_structure_total(position, phase),
        evaluate_bishop_pair(position), evaluate_rook_files(position)};
}

[[nodiscard]] inline int evaluate_static(const Position& position) {
    return evaluate_breakdown(position).total();
}

[[nodiscard]] inline int evaluate(Position& position) {
    const auto status = game_status(position);
    if (status == GameStatus::checkmate) {
        return position.side_to_move() == Color::white ? -mate_score : mate_score;
    }
    if (status == GameStatus::stalemate || position.is_insufficient_material()) {
        return 0;
    }
    return evaluate_static(position);
}

[[nodiscard]] inline int evaluate_for_side_to_move(Position& position) {
    const auto score = evaluate(position);
    return position.side_to_move() == Color::white ? score : -score;
}

}
