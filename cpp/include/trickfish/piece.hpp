#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace trickfish {

enum class Color : std::uint8_t {
    white,
    black
};

enum class PieceType : std::uint8_t {
    pawn,
    knight,
    bishop,
    rook,
    queen,
    king
};

inline constexpr Color opposite(Color color) {
    return color == Color::white ? Color::black : Color::white;
}

inline constexpr std::size_t piece_index(Color color, PieceType type) {
    return static_cast<std::size_t>(color) * 6 + static_cast<std::size_t>(type);
}

inline constexpr char piece_symbol(Color color, PieceType type) {
    constexpr char symbols[2][6] = {
        {'P', 'N', 'B', 'R', 'Q', 'K'},
        {'p', 'n', 'b', 'r', 'q', 'k'}
    };
    return symbols[static_cast<std::size_t>(color)][static_cast<std::size_t>(type)];
}

inline constexpr Color color_from_symbol(char symbol) {
    if (symbol >= 'A' && symbol <= 'Z') return Color::white;
    if (symbol >= 'a' && symbol <= 'z') return Color::black;
    throw std::invalid_argument("invalid piece symbol");
}

inline constexpr PieceType piece_type_from_symbol(char symbol) {
    if (symbol >= 'a' && symbol <= 'z') symbol = static_cast<char>(symbol - 'a' + 'A');
    if (symbol == 'P') return PieceType::pawn;
    if (symbol == 'N') return PieceType::knight;
    if (symbol == 'B') return PieceType::bishop;
    if (symbol == 'R') return PieceType::rook;
    if (symbol == 'Q') return PieceType::queen;
    if (symbol == 'K') return PieceType::king;
    throw std::invalid_argument("invalid piece symbol");
}

}
