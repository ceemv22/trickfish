#pragma once

#include <cstdint>

#include "trickfish/position.hpp"

namespace trickfish {

[[nodiscard]] std::uint64_t perft(Position& position, int depth);

}
