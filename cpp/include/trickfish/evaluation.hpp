#pragma once

#include <array>
#include <bit>
#include <cstddef>

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

[[nodiscard]] inline int evaluate_static(const Position& position) {
    return evaluate_material(position) + evaluate_bishop_pair(position) + evaluate_rook_files(position);
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
