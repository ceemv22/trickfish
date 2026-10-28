#pragma once

#include <iosfwd>
#include <string_view>

#include "trickfish/history.hpp"
#include "trickfish/position.hpp"

namespace trickfish {

struct UciPosition {
    Position position;
    RepetitionHistory history;
};

[[nodiscard]] UciPosition parse_uci_position(std::string_view command);
int run_uci(std::istream& input, std::ostream& output);

}
