#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>

#include "trickfish/attacks.hpp"

using trickfish::Bitboard;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static_assert(trickfish::rook_attacks_ray(0, 0) == 0x01010101010101feULL);
static_assert(trickfish::bishop_attacks_ray(0, 0) == 0x8040201008040200ULL);
static_assert(trickfish::rook_attacks_ray(0, (Bitboard{1} << 3) | (Bitboard{1} << 16)) == 0x1010eULL);
static_assert(trickfish::rook_attacks_ray(63, 0) == 0x7f80808080808080ULL);

std::uint64_t exhaustive(std::uint8_t square, bool bishop) {
    const auto reference = bishop ? trickfish::bishop_attacks_reference : trickfish::rook_attacks_reference;
    const auto candidate = bishop ? trickfish::bishop_attacks_ray : trickfish::rook_attacks_ray;
    const auto selected = bishop ? trickfish::bishop_attacks : trickfish::rook_attacks;
    const auto mask = reference(square, 0);
    Bitboard occupancy = 0;
    std::uint64_t cases = 0;
    do {
        const auto expected = reference(square, occupancy);
        require(candidate(square, occupancy) == expected, "on-ray occupancy mismatch");
        require(candidate(square, occupancy | ~mask) == expected, "off-ray/source occupancy changed attacks");
        require(selected(square, occupancy) == expected, "selected kernel differs from reference");
        require((expected & trickfish::square_bit(square)) == 0, "sliding attack includes its source");
        ++cases;
        occupancy = (occupancy - mask) & mask;
    } while (occupancy != 0);
    return cases;
}

int main() {
    try {
        std::uint64_t cases = 0;
        std::uint64_t random = 0x123456789abcdef0ULL;
        for (std::uint8_t square = 0; square < 64; ++square) {
            cases += exhaustive(square, true) + exhaustive(square, false);
            for (int sample = 0; sample < 1024; ++sample) {
                random ^= random << 13;
                random ^= random >> 7;
                random ^= random << 17;
                const auto expected = trickfish::bishop_attacks_reference(square, random) |
                    trickfish::rook_attacks_reference(square, random);
                require((trickfish::bishop_attacks_ray(square, random) | trickfish::rook_attacks_ray(square, random)) == expected,
                    "random full-board ray mismatch");
                require(trickfish::queen_attacks(square, random) == expected, "selected queen kernel mismatch");
            }
        }
        for (const auto square : {64, 255}) {
            for (const auto function : std::array{trickfish::bishop_attacks_reference, trickfish::rook_attacks_reference,
                    trickfish::bishop_attacks_ray, trickfish::rook_attacks_ray, trickfish::bishop_attacks,
                    trickfish::rook_attacks, trickfish::queen_attacks}) {
                bool rejected = false;
                try { static_cast<void>(function(static_cast<std::uint8_t>(square), 0)); }
                catch (const std::invalid_argument&) { rejected = true; }
                require(rejected, "invalid sliding square was accepted");
            }
        }
        std::cout << "exhaustive_occupancy_cases " << cases << '\n';
        std::cout << "random_queen_cases " << 64 * 1024 << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
