#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

#include "trickfish/attacks.hpp"
#include "trickfish/movegen.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

bool reference_check(const Position& position, Color color) {
    const auto king = position.pieces(color, PieceType::king);
    if (king == 0) {
        return false;
    }
    const auto square = static_cast<std::uint8_t>(std::countr_zero(king));
    const auto enemy = opposite(color);
    if ((pawn_attacks(color, square) & position.pieces(enemy, PieceType::pawn)) != 0 ||
        (knight_attacks(square) & position.pieces(enemy, PieceType::knight)) != 0 ||
        (king_attacks(square) & position.pieces(enemy, PieceType::king)) != 0) {
        return true;
    }
    const auto occupied = position.occupancy();
    const auto queens = position.pieces(enemy, PieceType::queen);
    return (bishop_attacks(square, occupied) & (position.pieces(enemy, PieceType::bishop) | queens)) != 0 ||
        (rook_attacks(square, occupied) & (position.pieces(enemy, PieceType::rook) | queens)) != 0;
}

bool geometric_attack(std::uint8_t king, std::uint8_t attacker, PieceType type, Color enemy) {
    const int rank = static_cast<int>(king / 8) - attacker / 8;
    const int file = static_cast<int>(king % 8) - attacker % 8;
    const int dr = std::abs(rank), df = std::abs(file);
    if (type == PieceType::pawn) return rank == (enemy == Color::white ? -1 : 1) && df == 1;
    if (type == PieceType::knight) return (dr == 1 && df == 2) || (dr == 2 && df == 1);
    if (type == PieceType::king) return dr <= 1 && df <= 1 && dr + df != 0;
    const bool diagonal = dr == df && dr != 0;
    const bool orthogonal = (dr == 0 || df == 0) && dr + df != 0;
    return type == PieceType::bishop ? diagonal : type == PieceType::rook ? orthogonal : diagonal || orthogonal;
}

Bitboard between(std::uint8_t king, std::uint8_t attacker) {
    if (!geometric_attack(king, attacker, PieceType::queen, Color::black)) return 0;
    const int dr = (attacker / 8 > king / 8) - (attacker / 8 < king / 8);
    const int df = (attacker % 8 > king % 8) - (attacker % 8 < king % 8);
    int rank = king / 8 + dr, file = king % 8 + df;
    Bitboard mask = 0;
    while (rank != attacker / 8 || file != attacker % 8) {
        mask |= square_bit(static_cast<std::uint8_t>(rank * 8 + file));
        rank += dr;
        file += df;
    }
    return mask;
}

Position position_from_board(const std::array<char, 64>& board) {
    std::string fen;
    for (int rank = 0; rank < 8; ++rank) {
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            const auto symbol = board[static_cast<std::size_t>(rank * 8 + file)];
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
    return Position::from_fen(fen + " w - - 0 1");
}

void verify(const Position& position) {
    for (const auto color : {Color::white, Color::black}) {
        const bool full_map = (position.pieces(color, PieceType::king) & position.attacks_by(opposite(color))) != 0;
        require(position.in_check(color) == reference_check(position, color), "filtered/unfiltered check mismatch");
        require(position.in_check(color) == full_map, "filtered/full-map check mismatch");
    }
}

std::uint64_t verify_tree(Position& root, int depth) {
    const auto fen = root.to_fen();
    const auto key = root.key();
    const auto pawn_key = root.pawn_key();
    verify(root);
    std::uint64_t cases = 1;
    if (depth > 0) {
        for (const auto& move : generate_legal_moves(root)) {
            const auto undo = root.make_move(move);
            cases += verify_tree(root, depth - 1);
            root.unmake_move(move, undo);
        }
    }
    require(root.to_fen() == fen && root.key() == key && root.pawn_key() == pawn_key, "check traversal changed root");
    return cases;
}

int main() {
    try {
        std::uint64_t cases = 0;
        for (std::uint8_t king = 0; king < 64; ++king) {
            Bitboard bishop_mask = 0, rook_mask = 0;
            for (std::uint8_t attacker = 0; attacker < 64; ++attacker) {
                if (geometric_attack(king, attacker, PieceType::bishop, Color::black)) bishop_mask |= square_bit(attacker);
                if (geometric_attack(king, attacker, PieceType::rook, Color::black)) rook_mask |= square_bit(attacker);
            }
            require(detail::bishop_alignment[king] == bishop_mask && detail::rook_alignment[king] == rook_mask,
                "alignment mask differs from coordinate geometry");
            for (const auto color : {Color::white, Color::black}) {
                for (std::uint8_t attacker = 0; attacker < 64; ++attacker) {
                    if (attacker == king) continue;
                    for (const auto type : {PieceType::pawn, PieceType::knight, PieceType::bishop, PieceType::rook, PieceType::queen, PieceType::king}) {
                        if (type == PieceType::pawn && (attacker / 8 == 0 || attacker / 8 == 7)) continue;
                        auto segment = between(king, attacker);
                        const bool slider = type == PieceType::bishop || type == PieceType::rook || type == PieceType::queen;
                        const int variants = slider && segment != 0 ? 3 : 1;
                        for (int variant = 0; variant < variants; ++variant) {
                            std::array<char, 64> board{};
                            board.fill('.');
                            board[king] = piece_symbol(color, PieceType::king);
                            board[attacker] = piece_symbol(opposite(color), type);
                            if (variant != 0) {
                                const auto blocker = static_cast<std::uint8_t>(std::countr_zero(segment));
                                board[blocker] = piece_symbol(variant == 1 ? color : opposite(color), PieceType::knight);
                            }
                            if (type != PieceType::king) {
                                bool placed = false;
                                for (std::uint8_t square = 0; square < 64; ++square) {
                                    if (board[square] != '.' || (segment & square_bit(square)) != 0 ||
                                        geometric_attack(king, square, PieceType::king, opposite(color))) continue;
                                    board[square] = piece_symbol(opposite(color), PieceType::king);
                                    placed = true;
                                    break;
                                }
                                require(placed, "could not place reference enemy king");
                            }
                            const auto position = position_from_board(board);
                            verify(position);
                            const bool geometric = geometric_attack(king, attacker, type, opposite(color));
                            require(position.in_check(color) == (geometric && variant == 0), "independent geometry mismatch");
                            ++cases;
                        }
                    }
                }
            }
        }
        for (const auto fen : {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
                "k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1",
                "4k3/8/8/r4pPK/8/8/8/8 w - f6 0 1",
                "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1"}) {
            auto root = Position::from_fen(fen);
            cases += verify_tree(root, 2);
            if (!root.in_check(root.side_to_move())) {
                const auto original = root.to_fen();
                const auto key = root.key();
                const auto undo = root.make_null_move();
                verify(root);
                root.unmake_null_move(undo);
                require(root.to_fen() == original && root.key() == key, "check null restoration failed");
            }
        }
        std::cout << "geometry_and_tree_cases " << cases << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

