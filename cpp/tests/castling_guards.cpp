#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "trickfish/movegen.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void append_reference_castling(MoveList& moves, const Position& position) {
    const auto color = position.side_to_move();
    const auto enemy_attacks = position.attacks_by(opposite(color));
    const auto occupied = position.occupancy();
    const std::uint8_t king_square = color == Color::white ? 60 : 4;
    const std::uint8_t kingside_rook = color == Color::white ? 63 : 7;
    const std::uint8_t queenside_rook = color == Color::white ? 56 : 0;
    const auto king = position.pieces(color, PieceType::king);
    const auto rooks = position.pieces(color, PieceType::rook);

    if ((king & square_bit(king_square)) == 0 || (enemy_attacks & square_bit(king_square)) != 0) {
        return;
    }

    const auto kingside_path = square_bit(static_cast<std::uint8_t>(king_square + 1)) |
        square_bit(static_cast<std::uint8_t>(king_square + 2));
    if (position.has_castling_right(color, true) &&
        (rooks & square_bit(kingside_rook)) != 0 &&
        (occupied & kingside_path) == 0 &&
        (enemy_attacks & kingside_path) == 0) {
        moves.push(Move(king_square, static_cast<std::uint8_t>(king_square + 2), '\0', false, true));
    }

    const auto queenside_empty = square_bit(static_cast<std::uint8_t>(king_square - 1)) |
        square_bit(static_cast<std::uint8_t>(king_square - 2)) |
        square_bit(static_cast<std::uint8_t>(king_square - 3));
    const auto queenside_king_path = square_bit(static_cast<std::uint8_t>(king_square - 1)) |
        square_bit(static_cast<std::uint8_t>(king_square - 2));
    if (position.has_castling_right(color, false) &&
        (rooks & square_bit(queenside_rook)) != 0 &&
        (occupied & queenside_empty) == 0 &&
        (enemy_attacks & queenside_king_path) == 0) {
        moves.push(Move(king_square, static_cast<std::uint8_t>(king_square - 2), '\0', false, true));
    }
}

Position from_board(const std::array<char, 64>& board, Color side, const std::string& rights) {
    std::string fen;
    for (int rank = 0; rank < 8; ++rank) {
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            const auto symbol = board[static_cast<std::size_t>(8 * rank + file)];
            if (symbol == '.') ++empty;
            else {
                if (empty != 0) fen += static_cast<char>('0' + empty);
                empty = 0;
                fen += symbol;
            }
        }
        if (empty != 0) fen += static_cast<char>('0' + empty);
        if (rank != 7) fen += '/';
    }
    fen += side == Color::white ? " w " : " b ";
    fen += rights.empty() ? "-" : rights;
    return Position::from_fen(fen + " - 0 1");
}

std::array<char, 64> board_of(const Position& position) {
    std::array<char, 64> board{};
    for (std::uint8_t square = 0; square < 64; ++square) board[square] = position.piece_at(square);
    return board;
}

Position reflected(const Position& position) {
    std::array<char, 64> board{};
    for (std::uint8_t square = 0; square < 64; ++square) {
        auto symbol = position.piece_at(square);
        if (symbol != '.') symbol = static_cast<char>(symbol >= 'A' && symbol <= 'Z' ? symbol + 32 : symbol - 32);
        board[square ^ 56] = symbol;
    }
    return from_board(board, opposite(position.side_to_move()), "KQkq");
}

std::uint64_t verify_tree(Position& root, int depth) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    const auto phase = root.phase_units();
    MoveList reference;
    append_reference_castling(reference, root);
    std::vector<Move> expected(reference.begin(), reference.end()), actual;
    for (const auto& move : generate_pseudo_legal_moves(root)) {
        if (move.castling) actual.push_back(move);
    }
    require(actual == expected, "lazy castling changed old-algorithm moves or order");
    std::uint64_t visited = 1;
    if (depth > 0) {
        for (const auto& move : generate_legal_moves(root)) {
            const auto undo = root.make_move(move);
            visited += verify_tree(root, depth - 1);
            root.unmake_move(move, undo);
        }
    }
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key && root.phase_units() == phase,
        "castling parity traversal changed root state");
    return visited;
}

int main() {
    try {
        const auto base = Position::from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1");
        const auto initial_board = board_of(base);
        std::uint64_t visited = 0;
        for (unsigned bits = 0; bits < 16; ++bits) {
            std::string rights;
            for (unsigned index = 0; index < 4; ++index) {
                if ((bits & (1U << index)) != 0) rights += std::string("KQkq")[index];
            }
            for (const auto side : {Color::white, Color::black}) {
                auto root = from_board(initial_board, side, rights);
                visited += verify_tree(root, 1);
            }
        }
        const auto check_variant = [&](const std::array<char, 64>& board) {
            auto root = from_board(board, Color::white, "KQkq");
            visited += verify_tree(root, 1);
            auto mirror = reflected(root);
            visited += verify_tree(mirror, 1);
        };
        for (const auto square : {57, 58, 59, 61, 62}) {
            auto board = initial_board;
            board[static_cast<std::size_t>(square)] = 'N';
            check_variant(board);
        }
        for (unsigned missing = 1; missing < 4; ++missing) {
            auto board = initial_board;
            if ((missing & 1U) != 0) board[56] = '.';
            if ((missing & 2U) != 0) board[63] = '.';
            check_variant(board);
        }
        auto away = initial_board;
        away[60] = '.';
        away[52] = 'K';
        check_variant(away);
        for (int file = 0; file < 8; ++file) {
            auto board = initial_board;
            board[static_cast<std::size_t>(32 + file)] = 'r';
            check_variant(board);
        }
        auto start = Position::from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
        visited += verify_tree(start, 2);
        std::cout << "castling_reference_tree_positions " << visited << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

