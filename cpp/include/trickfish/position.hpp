#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>

namespace trickfish {

class Position {
public:
    static Position from_fen(std::string_view fen);

    [[nodiscard]] std::string to_fen() const;
    [[nodiscard]] const std::array<char, 64>& board() const;
    [[nodiscard]] char side_to_move() const;
    [[nodiscard]] std::uint8_t castling_rights() const;
    [[nodiscard]] std::int8_t en_passant_square() const;
    [[nodiscard]] int halfmove_clock() const;
    [[nodiscard]] int fullmove_number() const;

private:
    std::array<char, 64> board_{};
    char side_to_move_ = 'w';
    std::uint8_t castling_rights_ = 0;
    std::int8_t en_passant_square_ = -1;
    int halfmove_clock_ = 0;
    int fullmove_number_ = 1;
};

}
