#pragma once

#include "trickfish/position.hpp"

namespace trickfish {

[[nodiscard]] int static_exchange_reference(const Position& position, const Move& move);

[[nodiscard]] int static_exchange(const Position& position, const Move& move);

}
