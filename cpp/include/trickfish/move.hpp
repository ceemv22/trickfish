#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>

#include "trickfish/square.hpp"

namespace trickfish {

struct Move {
    std::uint8_t from = 0;
    std::uint8_t to = 0;
    char promotion = '\0';
    bool en_passant = false;
    bool castling = false;

    Move() = default;

    Move(
        std::uint8_t from_square,
        std::uint8_t to_square,
        char promotion_piece = '\0',
        bool is_en_passant = false,
        bool is_castling = false
    )
        : from(from_square),
          to(to_square),
          promotion(promotion_piece),
          en_passant(is_en_passant),
          castling(is_castling) {
        if (from >= 64 || to >= 64 || from == to) {
            throw std::invalid_argument("invalid move squares");
        }
        if (promotion != '\0' && promotion != 'q' && promotion != 'r' && promotion != 'b' && promotion != 'n') {
            throw std::invalid_argument("promotion must be q, r, b, or n");
        }
    }

    [[nodiscard]] std::string to_uci() const {
        auto text = square_name(from) + square_name(to);
        if (promotion != '\0') {
            text.push_back(promotion);
        }
        return text;
    }

    bool operator==(const Move&) const = default;
};

}
