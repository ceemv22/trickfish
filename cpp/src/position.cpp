#include "trickfish/position.hpp"

#include <algorithm>
#include <charconv>
#include <sstream>
#include <stdexcept>
#include <string>

#include "trickfish/square.hpp"

namespace trickfish {
namespace {

constexpr std::uint8_t white_kingside = 1;
constexpr std::uint8_t white_queenside = 2;
constexpr std::uint8_t black_kingside = 4;
constexpr std::uint8_t black_queenside = 8;
constexpr std::string_view pieces = "prnbqkPRNBQK";

int parse_integer(std::string_view text, std::string_view field) {
    int value = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
    if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) {
        throw std::invalid_argument(std::string(field) + " must be an integer");
    }
    return value;
}

}

Position Position::from_fen(std::string_view fen) {
    std::istringstream stream{std::string(fen)};
    std::string placement;
    std::string active;
    std::string castling;
    std::string en_passant;
    std::string halfmove;
    std::string fullmove;
    std::string extra;
    if (!(stream >> placement >> active >> castling >> en_passant >> halfmove >> fullmove) || stream >> extra) {
        throw std::invalid_argument("FEN must contain exactly six fields");
    }

    Position position;
    position.board_.fill('.');
    int square = 0;
    int ranks = 1;
    int rank_squares = 0;
    for (char symbol : placement) {
        if (symbol == '/') {
            if (rank_squares != 8) {
                throw std::invalid_argument("each rank must describe exactly eight squares");
            }
            ++ranks;
            rank_squares = 0;
        } else if (symbol >= '1' && symbol <= '8') {
            const int empty = symbol - '0';
            square += empty;
            rank_squares += empty;
        } else if (pieces.find(symbol) != std::string_view::npos) {
            if (square >= 64) {
                throw std::invalid_argument("piece placement exceeds the board");
            }
            position.board_[square++] = symbol;
            ++rank_squares;
        } else {
            throw std::invalid_argument("invalid piece symbol");
        }
        if (square > 64 || rank_squares > 8) {
            throw std::invalid_argument("piece placement exceeds the board");
        }
    }
    if (ranks != 8 || rank_squares != 8 || square != 64) {
        throw std::invalid_argument("piece placement must describe eight ranks");
    }
    if (std::count(position.board_.begin(), position.board_.end(), 'K') != 1 ||
        std::count(position.board_.begin(), position.board_.end(), 'k') != 1) {
        throw std::invalid_argument("position must contain exactly one king of each color");
    }

    if (active != "w" && active != "b") {
        throw std::invalid_argument("active color must be w or b");
    }
    position.side_to_move_ = active[0];

    if (castling != "-") {
        for (char right : castling) {
            std::uint8_t bit = 0;
            if (right == 'K') bit = white_kingside;
            else if (right == 'Q') bit = white_queenside;
            else if (right == 'k') bit = black_kingside;
            else if (right == 'q') bit = black_queenside;
            else throw std::invalid_argument("invalid castling field");
            if ((position.castling_rights_ & bit) != 0) {
                throw std::invalid_argument("castling field must not repeat a right");
            }
            position.castling_rights_ |= bit;
        }
    }

    if (en_passant != "-") {
        if (en_passant.size() != 2 || (en_passant[1] != '3' && en_passant[1] != '6')) {
            throw std::invalid_argument("invalid en passant square");
        }
        position.en_passant_square_ = static_cast<std::int8_t>(square_from_name(en_passant));
    }

    position.halfmove_clock_ = parse_integer(halfmove, "halfmove clock");
    position.fullmove_number_ = parse_integer(fullmove, "fullmove number");
    if (position.halfmove_clock_ < 0 || position.fullmove_number_ < 1) {
        throw std::invalid_argument("invalid move counters");
    }
    return position;
}

std::string Position::to_fen() const {
    std::string placement;
    for (int rank = 0; rank < 8; ++rank) {
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            const char piece = board_[rank * 8 + file];
            if (piece == '.') {
                ++empty;
            } else {
                if (empty != 0) {
                    placement += static_cast<char>('0' + empty);
                    empty = 0;
                }
                placement += piece;
            }
        }
        if (empty != 0) {
            placement += static_cast<char>('0' + empty);
        }
        if (rank != 7) {
            placement += '/';
        }
    }

    std::string castling;
    if ((castling_rights_ & white_kingside) != 0) castling += 'K';
    if ((castling_rights_ & white_queenside) != 0) castling += 'Q';
    if ((castling_rights_ & black_kingside) != 0) castling += 'k';
    if ((castling_rights_ & black_queenside) != 0) castling += 'q';
    if (castling.empty()) castling = "-";

    const auto en_passant = en_passant_square_ < 0
        ? std::string("-")
        : square_name(static_cast<std::uint8_t>(en_passant_square_));
    return placement + " " + side_to_move_ + " " + castling + " " + en_passant + " " +
        std::to_string(halfmove_clock_) + " " + std::to_string(fullmove_number_);
}

const std::array<char, 64>& Position::board() const { return board_; }
char Position::side_to_move() const { return side_to_move_; }
std::uint8_t Position::castling_rights() const { return castling_rights_; }
std::int8_t Position::en_passant_square() const { return en_passant_square_; }
int Position::halfmove_clock() const { return halfmove_clock_; }
int Position::fullmove_number() const { return fullmove_number_; }

}
