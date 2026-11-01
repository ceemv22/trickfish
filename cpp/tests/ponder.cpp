#include <atomic>
#include <chrono>
#include <future>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

#include "trickfish/ponder.hpp"

using namespace trickfish;
using Clock = std::chrono::steady_clock;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        const auto start = Clock::time_point{};
        const auto later = start + std::chrono::milliseconds(1000);
        require(search_deadline(start, 10) == start + std::chrono::milliseconds(10), "deadline duration changed units");
        require(search_deadline(Clock::time_point::min(), 0) == Clock::time_point::min(), "negative epoch deadline overflowed");
        require(search_deadline(Clock::time_point::min(), 1) == Clock::time_point::min() + std::chrono::milliseconds(1),
            "negative epoch addition overflowed");
        require(search_deadline(Clock::time_point::max(), 0) == Clock::time_point::max(), "zero deadline overflowed");
        for (const bool near_end : {false, true}) {
            bool rejected = false;
            try { static_cast<void>(search_deadline(near_end ? Clock::time_point::max() : start,
                near_end ? 1 : std::numeric_limits<std::uint64_t>::max())); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected, "overflowing deadline accepted");
        }
        PonderControl clocked(25);
        require(clocked.pending() && !clocked.expired(later), "ponder time consumed the normal budget");
        require(clocked.hit(later), "first ponderhit was rejected");
        require(!clocked.pending() && !clocked.expired(later + std::chrono::milliseconds(24)) &&
            clocked.expired(later + std::chrono::milliseconds(25)), "deadline did not begin at hit");
        require(!clocked.hit(later + std::chrono::milliseconds(20)) && clocked.expired(later + std::chrono::milliseconds(25)),
            "duplicate ponderhit reset deadline");
        PonderControl zero(0);
        require(!zero.expired(later) && zero.hit(later) && zero.expired(later), "zero-time ponder budget activated before hit");
        PonderControl real_zero(0);
        require(!real_zero.expired() && real_zero.hit(Clock::now()) && real_zero.expired(), "real-clock zero budget did not activate at hit");
        PonderControl unbounded(std::nullopt);
        require(unbounded.hit(later) && !unbounded.expired(Clock::time_point::max()), "untimed hit invented a deadline");
        require(!unbounded.expired(), "untimed hit activated real-clock expiry");
        PonderControl overflowing(1);
        bool rejected = false;
        try { static_cast<void>(overflowing.hit(Clock::time_point::max())); }
        catch (const std::invalid_argument&) { rejected = true; }
        require(rejected && overflowing.pending() && !overflowing.expired(later), "failed hit changed pending state");
        require(overflowing.hit(start) && overflowing.expired(start + std::chrono::milliseconds(1)), "failed hit could not be retried");
        for (const bool stop_first : {false, true}) {
            PonderControl control(std::nullopt);
            std::promise<void> ready;
            std::promise<bool> outcome;
            auto result = outcome.get_future();
            std::jthread waiter([&](std::stop_token stop) {
                ready.set_value();
                outcome.set_value(control.wait_for_hit(stop));
            });
            ready.get_future().wait();
            require(result.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready,
                "ponder wait returned before hit or stop");
            if (stop_first) waiter.request_stop();
            else require(control.hit(start), "waiting hit was rejected");
            require(result.wait_for(std::chrono::seconds(5)) == std::future_status::ready, "ponder waiter did not wake");
            require(result.get() == !stop_first, "ponder wait reported wrong release reason");
            waiter.join();
        }
        PonderControl already_hit(std::nullopt);
        require(already_hit.hit(start), "pre-wait hit failed");
        require(already_hit.wait_for_hit({}), "hit before wait was lost");
        PonderControl concurrent(5);
        std::atomic<int> accepted{0};
        std::atomic<int> reads{0};
        std::vector<std::jthread> hitters;
        for (int index = 0; index < 8; ++index) {
            hitters.emplace_back([&] {
                if (concurrent.hit(later)) ++accepted;
                for (int repeat = 0; repeat < 1000; ++repeat) {
                    if (concurrent.expired(later + std::chrono::milliseconds(5))) ++reads;
                }
            });
        }
        for (auto& thread : hitters) thread.join();
        require(accepted == 1 && reads == 8000 && !concurrent.pending(), "concurrent hit/deadline publication was inconsistent");
        std::cout << "Ponder fake-clock, single-hit, concurrency, wait and stop checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
