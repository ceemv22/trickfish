#pragma once

#include <cstdint>
#include <vector>

#include "trickfish/position.hpp"

namespace trickfish {

class CorrectionHistory {
public:
    [[nodiscard]] int adjustment(const Position& position) const;
    [[nodiscard]] bool update(const Position& position, int target, int raw, int depth);
    void clear();
private:
    struct Entry {
        std::uint64_t key = 0;
        int value = 0;
        bool occupied = false;
    };
    std::vector<Entry> entries_;
};

}
