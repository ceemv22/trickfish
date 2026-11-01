#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <vector>

#include "trickfish/move.hpp"

namespace trickfish {

class MoveOrderingTable {
public:
    explicit MoveOrderingTable(std::size_t capacity = 65536) : slots_(capacity) {
        if (capacity == 0) throw std::invalid_argument("move ordering table capacity must be positive");
    }

    [[nodiscard]] std::size_t capacity() const { return slots_.size(); }

    [[nodiscard]] std::optional<Move> probe(std::uint64_t key) const {
        const auto& slot = slots_[key % slots_.size()];
        return slot && slot->key == key ? std::optional<Move>{slot->move} : std::nullopt;
    }

    void store(std::uint64_t key, const Move& move) {
        slots_[key % slots_.size()] = Entry{key, move};
    }

    void clear() {
        for (auto& slot : slots_) slot.reset();
    }

private:
    struct Entry {
        std::uint64_t key;
        Move move;
    };
    std::vector<std::optional<Entry>> slots_;
};

}
