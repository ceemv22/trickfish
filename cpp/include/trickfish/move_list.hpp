#pragma once

#include <array>
#include <cstddef>
#include <stdexcept>

#include "trickfish/move.hpp"

namespace trickfish {

class MoveList {
public:
    static constexpr std::size_t capacity = 256;

    constexpr void push(Move move) {
        if (size_ == capacity) {
            throw std::overflow_error("move list capacity exceeded");
        }
        moves_[size_++] = move;
    }

    [[nodiscard]] constexpr std::size_t size() const { return size_; }
    [[nodiscard]] constexpr bool empty() const { return size_ == 0; }
    [[nodiscard]] constexpr Move* begin() { return moves_.data(); }
    [[nodiscard]] constexpr Move* end() { return moves_.data() + size_; }
    [[nodiscard]] constexpr const Move* begin() const { return moves_.data(); }
    [[nodiscard]] constexpr const Move* end() const { return moves_.data() + size_; }

    [[nodiscard]] constexpr Move& operator[](std::size_t index) {
        if (index >= size_) {
            throw std::out_of_range("move index out of range");
        }
        return moves_[index];
    }

    [[nodiscard]] constexpr const Move& operator[](std::size_t index) const {
        if (index >= size_) {
            throw std::out_of_range("move index out of range");
        }
        return moves_[index];
    }

private:
    std::array<Move, capacity> moves_{};
    std::size_t size_ = 0;
};

}
