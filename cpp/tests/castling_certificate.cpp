#include <algorithm>
#include <array>
#include <cctype>
#include <iostream>
#include <stdexcept>
#include <string>

#include "trickfish/movegen.hpp"

using namespace trickfish;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::string fen(const std::array<char, 64>& board, Color color, std::string rights) {
    std::string text;
    for (int rank = 0; rank < 8; ++rank) {
        if (rank != 0) text += '/';
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            const char piece = board[rank * 8 + file];
            if (piece == '.') ++empty;
            else {
                if (empty) text += static_cast<char>('0' + empty);
                empty = 0;
                text += piece;
            }
        }
        if (empty) text += static_cast<char>('0' + empty);
    }
    if (color == Color::black) for (auto& right : rights) right = static_cast<char>(std::tolower(static_cast<unsigned char>(right)));
    return text + (color == Color::white ? " w " : " b ") + rights + " - 0 1";
}

int main() {
    try {
        std::size_t roots = 0, certificates = 0;
        for (const auto color : {Color::white, Color::black}) {
            const int home = color == Color::white ? 60 : 4;
            for (const auto rights : {"K", "Q", "KQ"}) for (int blockers = 0; blockers < 32; ++blockers) {
                for (const char type : {'p', 'n', 'b', 'r', 'q'}) for (int target = 0; target < 64; ++target) {
                    std::array<char, 64> board;
                    board.fill('.');
                    board[home] = color == Color::white ? 'K' : 'k';
                    board[home ^ 56] = color == Color::white ? 'k' : 'K';
                    board[home - 4] = board[home + 3] = color == Color::white ? 'R' : 'r';
                    constexpr std::array offsets = {-3, -2, -1, 1, 2};
                    for (std::size_t index = 0; index < offsets.size(); ++index) {
                        if (blockers & (1 << index)) board[home + offsets[index]] = color == Color::white ? 'N' : 'n';
                    }
                    if (board[target] != '.' || (type == 'p' && (target / 8 == 0 || target / 8 == 7))) continue;
                    board[target] = color == Color::white ? type : static_cast<char>(std::toupper(static_cast<unsigned char>(type)));
                    auto root = Position::from_fen(fen(board, color, rights));
                    const auto original = root.to_fen();
                    const auto key = root.key();
                    const auto candidates = generate_pseudo_legal_moves(root);
                    MoveList reference;
                    for (const auto& move : candidates) {
                        const auto undo = root.make_move(move);
                        const bool safe = !root.in_check(color);
                        root.unmake_move(move, undo);
                        if (move.castling) {
                            ++certificates;
                            require(safe, "pseudo-castle certificate failed final-position king safety");
                        }
                        if (safe) reference.push(move);
                    }
                    const auto actual = generate_legal_moves(root);
                    require(std::equal(actual.begin(), actual.end(), reference.begin(), reference.end()), "castling shortcut changed full-filter legal moves");
                    require(root.to_fen() == original && root.key() == key, "certificate validation changed root");
                    ++roots;
                }
            }
        }
        require(roots > 40000 && certificates > 1000, "castling certificate matrix missed coverage");
        std::cout << roots << " roots, " << certificates << " independently made/unmade castle certificates\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
