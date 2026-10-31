#include <algorithm>
#include <charconv>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <system_error>
#include <vector>

#include "trickfish/attacks.hpp"

using trickfish::Bitboard;

struct Case {
    std::uint8_t square;
    Bitboard occupancy;
};

Bitboard reference_attacks(std::uint8_t square, Bitboard occupancy) {
    return trickfish::bishop_attacks_reference(square, occupancy) | trickfish::rook_attacks_reference(square, occupancy);
}

Bitboard ray_attacks(std::uint8_t square, Bitboard occupancy) {
    return trickfish::bishop_attacks_ray(square, occupancy) | trickfish::rook_attacks_ray(square, occupancy);
}

struct Sample {
    std::uint64_t checksum;
    double nanoseconds;
};

Sample measure(const std::vector<Case>& cases, int iterations, Bitboard (*function)(std::uint8_t, Bitboard)) {
    Bitboard (*volatile selected)(std::uint8_t, Bitboard) = function;
    std::uint64_t checksum = 0;
    const auto started = std::chrono::steady_clock::now();
    for (int repeat = 0; repeat < iterations; ++repeat) {
        for (const auto& item : cases) {
            const auto call = selected;
            checksum += call(item.square, item.occupancy);
        }
    }
    const auto elapsed = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now() - started).count();
    if (elapsed <= 0) throw std::runtime_error("nonpositive sliding timing");
    return {checksum, elapsed};
}

int main(int argc, char** argv) {
    try {
        int iterations = 512;
        if (argc > 2) throw std::invalid_argument("usage: sliding_kernel_bench [iterations]");
        if (argc == 2) {
            const std::string_view text(argv[1]);
            const auto parsed = std::from_chars(text.data(), text.data() + text.size(), iterations);
            if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size()) throw std::invalid_argument("invalid iterations");
        }
        if (iterations < 1 || iterations > 4096) throw std::invalid_argument("iterations must be 1..4096");
        std::vector<Case> cases;
        std::uint64_t random = 0x123456789abcdef0ULL;
        const auto next = [&random]() {
            random ^= random << 13;
            random ^= random >> 7;
            random ^= random << 17;
            return random;
        };
        for (std::uint8_t square = 0; square < 64; ++square) {
            for (int sample = 0; sample < 32; ++sample) {
                Bitboard occupancy = next();
                if (sample % 4 == 1 || sample % 4 == 2) {
                    const auto first = next();
                    const auto second = next();
                    if (sample % 4 == 1) occupancy &= first & second;
                    else occupancy |= first | second;
                }
                else if (sample % 4 == 3) occupancy = 0;
                cases.push_back({square, occupancy});
                if (reference_attacks(square, occupancy) != ray_attacks(square, occupancy)) {
                    throw std::runtime_error("sliding kernel parity failed before timing");
                }
            }
        }
        if (measure(cases, 1, reference_attacks).checksum != measure(cases, 1, ray_attacks).checksum) {
            throw std::runtime_error("sliding warmup checksum mismatch");
        }
        std::vector<Sample> reference, ray;
        std::vector<double> ratios;
        for (int repeat = 0; repeat < 6; ++repeat) {
            Sample old{}, candidate{};
            if (repeat % 2 == 0) {
                old = measure(cases, iterations, reference_attacks);
                candidate = measure(cases, iterations, ray_attacks);
            } else {
                candidate = measure(cases, iterations, ray_attacks);
                old = measure(cases, iterations, reference_attacks);
            }
            if (old.checksum != candidate.checksum || (!reference.empty() && old.checksum != reference.front().checksum)) {
                throw std::runtime_error("sliding timing checksum mismatch");
            }
            reference.push_back(old);
            ray.push_back(candidate);
            ratios.push_back(candidate.nanoseconds / old.nanoseconds);
        }
        std::sort(ratios.begin(), ratios.end());
        std::cout << std::setprecision(17) << "{\n  \"schema_version\": 1,\n  \"cases\": " << cases.size()
            << ",\n  \"generator\": \"xorshift64-13-7-17/mixed-sparse-dense-empty-v1\",\n  \"seed\": \"123456789abcdef0\""
            << ",\n  \"iterations\": " << iterations
            << ",\n  \"selected_engine_kernel\": \"" << (trickfish::use_ray_sliders ? "ray" : "reference") << "\","
            << "\n  \"scope\": \"bishop and rook union; empty, sparse, dense and mixed occupancies; indirect call included; search excluded\","
            << "\n  \"samples\": [\n";
        for (std::size_t index = 0; index < reference.size(); ++index) {
            if (index != 0) std::cout << ",\n";
            std::cout << "    {\"reference_first\": " << (index % 2 == 0 ? "true" : "false")
                << ", \"reference_ns\": " << reference[index].nanoseconds << ", \"ray_ns\": " << ray[index].nanoseconds
                << ", \"checksum\": " << reference[index].checksum << "}";
        }
        std::cout << "\n  ],\n  \"median_ray_reference_ratio\": " << (ratios[2] + ratios[3]) / 2 << "\n}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
