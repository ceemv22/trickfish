#pragma once

#include <atomic>
#include <condition_variable>
#include <mutex>
#include <stop_token>

#include "trickfish/time.hpp"

namespace trickfish {

class PonderControl {
public:
    explicit PonderControl(std::optional<std::uint64_t> budget) : budget_(budget) {}

    [[nodiscard]] bool pending() const { return pending_.load(std::memory_order_acquire); }

    [[nodiscard]] bool hit(std::chrono::steady_clock::time_point now) {
        {
            std::lock_guard lock(mutex_);
            if (!pending_.load(std::memory_order_relaxed)) return false;
            const auto deadline = budget_ ? std::optional{search_deadline(now, *budget_)} : std::nullopt;
            deadline_ = deadline;
            pending_.store(false, std::memory_order_release);
        }
        changed_.notify_all();
        return true;
    }

    [[nodiscard]] bool expired(std::chrono::steady_clock::time_point now) const {
        return !pending_.load(std::memory_order_acquire) && deadline_ && now >= *deadline_;
    }

    [[nodiscard]] bool expired() const {
        return !pending_.load(std::memory_order_acquire) && deadline_ && std::chrono::steady_clock::now() >= *deadline_;
    }

    bool wait_for_hit(std::stop_token stop) {
        std::unique_lock lock(mutex_);
        return changed_.wait(lock, stop, [this] { return !pending_.load(std::memory_order_acquire); });
    }

private:
    const std::optional<std::uint64_t> budget_;
    std::optional<std::chrono::steady_clock::time_point> deadline_;
    std::atomic<bool> pending_{true};
    std::mutex mutex_;
    std::condition_variable_any changed_;
};

}
