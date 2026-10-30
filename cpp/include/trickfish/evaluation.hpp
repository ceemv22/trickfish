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

[[nodiscard]] inline int evaluate_material(const Position& position) {
    return position.material_score();
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
    return std::min(evaluation_max_phase, position.phase_units());
}

namespace detail {

inline constexpr auto passed_pawn_masks = [] {
    std::array<std::array<Bitboard, 64>, 2> masks{};
    for (const auto color : {Color::white, Color::black}) {
        const int step = color == Color::white ? -1 : 1;
        for (int square = 0; square < 64; ++square) {
            for (int rank = square / 8 + step; rank >= 0 && rank < 8; rank += step) {
                for (int file = square % 8 - 1; file <= square % 8 + 1; ++file) {
                    if (file >= 0 && file < 8) {
                        masks[static_cast<std::size_t>(color)][static_cast<std::size_t>(square)] |=
                            Bitboard{1} << (rank * 8 + file);
                    }
                }
            }
        }
    }
    return masks;
}();

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
        const bool passed = (enemy_pawns & passed_pawn_masks[static_cast<std::size_t>(color)][square]) == 0;
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

namespace detail {

inline int center_distance(std::uint8_t square) {
    const int rank = square / 8;
    const int file = square % 8;
    return std::abs(2 * file - 7) + std::abs(2 * rank - 7);
}

inline int king_safety_total(const Position& position, int phase) {
    int score = 0;
    for (const auto color : {Color::white, Color::black}) {
        auto kings = position.pieces(color, PieceType::king);
        const auto pawns = position.pieces(color, PieceType::pawn);
        const int pawn_rank = color == Color::white ? 6 : 1;
        while (kings != 0) {
            const auto square = pop_lsb(kings);
            const int file = square % 8;
            const bool castled_square = color == Color::white
                ? square == 58 || square == 62 : square == 2 || square == 6;
            int bonus = castled_square ? 20 : 0;
            for (int shield_file = file - 1; shield_file <= file + 1; ++shield_file) {
                if (shield_file >= 0 && shield_file < 8 &&
                    (pawns & square_bit(static_cast<std::uint8_t>(pawn_rank * 8 + shield_file))) != 0) {
                    bonus += 8;
                }
            }
            const int scaled = bonus * phase / evaluation_max_phase;
            score += color == Color::white ? scaled : -scaled;
        }
    }
    return score;
}

inline int king_activity_total(const Position& position, int phase) {
    if ((position.pieces(Color::white, PieceType::queen) | position.pieces(Color::black, PieceType::queen) |
        position.pieces(Color::white, PieceType::rook) | position.pieces(Color::black, PieceType::rook)) != 0) {
        return 0;
    }
    int score = 0;
    for (const auto color : {Color::white, Color::black}) {
        auto kings = position.pieces(color, PieceType::king);
        while (kings != 0) {
            const auto square = pop_lsb(kings);
            const int bonus = std::max(0, 14 - center_distance(square)) * (evaluation_max_phase - phase) /
                evaluation_max_phase;
            score += color == Color::white ? bonus : -bonus;
        }
    }
    return score;
}

}

[[nodiscard]] inline int evaluate_piece_activity(const Position& position) {
    int score = position.base_activity_score();
    for (const auto color : {Color::white, Color::black}) {
        if (position.pieces(opposite(color), PieceType::pawn) != 0) {
            const auto seventh_rank = Bitboard{0xff} << (color == Color::white ? 8 : 48);
            const int bonus = 20 * std::popcount(position.pieces(color, PieceType::rook) & seventh_rank);
            score += color == Color::white ? bonus : -bonus;
        }
    }
    return score;
}

[[nodiscard]] inline int evaluate_king_safety(const Position& position) {
    return detail::king_safety_total(position, game_phase(position));
}

[[nodiscard]] inline int evaluate_king_activity(const Position& position) {
    return detail::king_activity_total(position, game_phase(position));
}

struct EvaluationBreakdown {
    int phase = 0;
    int material = 0;
    int piece_activity = 0;
    int pawn_structure = 0;
    int bishop_pair = 0;
    int rook_files = 0;
    int king_safety = 0;
    int king_activity = 0;

    [[nodiscard]] int total() const {
        return material + piece_activity + pawn_structure + bishop_pair + rook_files + king_safety + king_activity;
    }
};

namespace detail {

inline EvaluationBreakdown breakdown_with_pawns(const Position& position, int phase, int pawn_score) {
    return {phase, evaluate_material(position), evaluate_piece_activity(position), pawn_score,
        evaluate_bishop_pair(position), evaluate_rook_files(position), king_safety_total(position, phase),
        king_activity_total(position, phase)};
}

}

[[nodiscard]] inline EvaluationBreakdown evaluate_breakdown(const Position& position) {
    const auto phase = game_phase(position);
    return detail::breakdown_with_pawns(position, phase, detail::pawn_structure_total(position, phase));
}

[[nodiscard]] inline int evaluate_static(const Position& position) {
    return evaluate_breakdown(position).total();
}

inline constexpr int endgame_scale_normal = 256;

[[nodiscard]] inline int endgame_scale(const Position& position) {
    for (const auto color : {Color::white, Color::black}) {
        if (position.pieces(color, PieceType::knight) != 0 ||
            position.pieces(color, PieceType::rook) != 0 || position.pieces(color, PieceType::queen) != 0) {
            return endgame_scale_normal;
        }
    }
    for (const auto attacker : {Color::white, Color::black}) {
        const auto defender = opposite(attacker);
        auto bishops = position.pieces(attacker, PieceType::bishop);
        const auto pawns = position.pieces(attacker, PieceType::pawn);
        if (std::popcount(bishops) != 1 || pawns == 0 ||
            position.occupancy(defender) != position.pieces(defender, PieceType::king)) continue;
        constexpr Bitboard a_file = 0x0101010101010101ULL;
        constexpr Bitboard h_file = a_file << 7;
        int file = -1;
        if ((pawns & ~a_file) == 0) file = 0;
        else if ((pawns & ~h_file) == 0) file = 7;
        if (file < 0) continue;
        const auto corner = static_cast<std::uint8_t>((attacker == Color::white ? 0 : 56) + file);
        if (position.pieces(defender, PieceType::king) != square_bit(corner)) continue;
        const auto bishop = pop_lsb(bishops);
        if ((bishop / 8 + bishop % 8) % 2 != (corner / 8 + corner % 8) % 2) return 0;
    }
    auto white = position.pieces(Color::white, PieceType::bishop);
    auto black = position.pieces(Color::black, PieceType::bishop);
    if (std::popcount(white) != 1 || std::popcount(black) != 1 ||
        (position.pieces(Color::white, PieceType::pawn) | position.pieces(Color::black, PieceType::pawn)) == 0) {
        return endgame_scale_normal;
    }
    const auto white_square = pop_lsb(white);
    const auto black_square = pop_lsb(black);
    const auto white_color = (white_square / 8 + white_square % 8) % 2;
    const auto black_color = (black_square / 8 + black_square % 8) % 2;
    return white_color != black_color ? 128 : endgame_scale_normal;
}

[[nodiscard]] inline int evaluate_scaled_static(const Position& position) {
    return evaluate_static(position) * endgame_scale(position) / endgame_scale_normal;
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
