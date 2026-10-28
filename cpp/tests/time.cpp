#include <iostream>
#include <limits>
#include <stdexcept>

#include "trickfish/time.hpp"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        trickfish::ClockControl clock;
        require(!trickfish::allocate_clock_time(trickfish::Color::white, clock), "missing clock became a budget");
        clock.white_time = 30000;
        clock.black_time = 5000;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 1000, "default white allocation mismatch");
        require(trickfish::allocate_clock_time(trickfish::Color::black, clock) == 166, "wrong side clock selected");
        clock.white_increment = 2000;
        clock.black_increment = 100;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 2000, "white increment mismatch");
        require(trickfish::allocate_clock_time(trickfish::Color::black, clock) == 216, "black increment mismatch");
        clock.moves_to_go = 10;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 4000, "movestogo allocation mismatch");
        clock.moves_to_go = 1;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 28500, "reserve exceeded");
        clock.white_time = 10;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 0, "exhausted reserve spent increment");
        clock.white_time = 0;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 0, "zero clock received time");
        clock.white_time = 11;
        clock.white_increment = 0;
        clock.moves_to_go = 30;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock) == 1, "minimum usable allocation mismatch");
        clock.white_time = 10000;
        require(trickfish::allocate_clock_time(trickfish::Color::white, clock, 10000) == 0, "custom overhead ignored");
        clock.moves_to_go = 0;
        bool rejected = false;
        try {
            const auto ignored = trickfish::allocate_clock_time(trickfish::Color::white, clock);
            static_cast<void>(ignored);
        } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "zero movestogo accepted");
        const auto maximum = std::numeric_limits<std::uint64_t>::max();
        for (const auto remaining : {std::uint64_t{0}, std::uint64_t{1}, std::uint64_t{11}, maximum}) {
            for (const auto increment : {std::uint64_t{0}, maximum}) {
                for (const auto moves : {std::uint64_t{1}, std::uint64_t{30}, maximum}) {
                    clock.white_time = remaining;
                    clock.white_increment = increment;
                    clock.moves_to_go = moves;
                    const auto budget = trickfish::allocate_clock_time(trickfish::Color::white, clock, 0);
                    require(budget && *budget <= remaining && (remaining == 0 || *budget > 0),
                        "clock arithmetic overflow or invalid budget");
                }
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
