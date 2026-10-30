#include <algorithm>
#include <bit>
#include <charconv>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <system_error>
#include <vector>

#include "trickfish/evaluation.hpp"

int reference_terms(const trickfish::Position& position) {
    int score = 0;
    for (std::size_t type = 0; type < trickfish::piece_values.size(); ++type) {
        const auto piece = static_cast<trickfish::PieceType>(type);
        score += trickfish::piece_values[type] *
            (std::popcount(position.pieces(trickfish::Color::white, piece)) -
             std::popcount(position.pieces(trickfish::Color::black, piece)));
    }
    for (const auto color : {trickfish::Color::white, trickfish::Color::black}) {
        int bonus = 0;
        auto pawns = position.pieces(color, trickfish::PieceType::pawn);
        while (pawns != 0) {
            const auto square = trickfish::pop_lsb(pawns);
            const int rank = square / 8;
            const int file = square % 8;
            bonus += 5 * (color == trickfish::Color::white ? 6 - rank : rank - 1) + (file == 3 || file == 4 ? 6 : 0);
        }
        for (const auto type : {trickfish::PieceType::knight, trickfish::PieceType::bishop}) {
            auto pieces = position.pieces(color, type);
            while (pieces != 0) {
                const int distance = trickfish::detail::center_distance(trickfish::pop_lsb(pieces));
                bonus += type == trickfish::PieceType::knight ? std::max(0, 28 - 2 * distance) : std::max(0, 16 - distance);
            }
        }
        if (position.pieces(trickfish::opposite(color), trickfish::PieceType::pawn) != 0) {
            const auto rank = trickfish::Bitboard{0xff} << (color == trickfish::Color::white ? 8 : 48);
            bonus += 20 * std::popcount(position.pieces(color, trickfish::PieceType::rook) & rank);
        }
        score += color == trickfish::Color::white ? bonus : -bonus;
    }
    return score;
}

int incremental_terms(const trickfish::Position& position) {
    return trickfish::evaluate_material(position) + trickfish::evaluate_piece_activity(position);
}

struct Sample {
    std::int64_t checksum;
    double nanoseconds;
};

Sample measure(const std::vector<trickfish::Position>& positions, int iterations,
    int (*function)(const trickfish::Position&)) {
    int (*volatile evaluator)(const trickfish::Position&) = function;
    std::int64_t checksum = 0;
    const auto start = std::chrono::steady_clock::now();
    for (int repeat = 0; repeat < iterations; ++repeat) {
        for (const auto& position : positions) {
            const auto selected = evaluator;
            checksum += selected(position);
        }
    }
    const auto elapsed = std::chrono::duration<double, std::nano>(std::chrono::steady_clock::now() - start).count();
    if (elapsed <= 0) throw std::runtime_error("nonpositive evaluation timing sample");
    return {checksum, elapsed};
}

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return (values[values.size() / 2 - 1] + values[values.size() / 2]) / 2;
}

int main(int argc, char* argv[]) {
    try {
        int iterations = 20000;
        if (argc > 2) throw std::invalid_argument("usage: evaluation_terms_bench [iterations]");
        if (argc == 2) {
            const std::string_view text(argv[1]);
            const auto parsed = std::from_chars(text.data(), text.data() + text.size(), iterations);
            if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size()) {
                throw std::invalid_argument("invalid iteration count");
            }
        }
        if (iterations < 1000 || iterations > 10000000) throw std::invalid_argument("iterations must be 1000..10000000");
        std::vector<trickfish::Position> positions;
        for (const auto fen : {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
            "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
            "7k/R6p/5N2/8/8/8/8/7K w - - 0 1",
            "7k/8/8/8/8/5n2/r6P/7K b - - 0 1"}) {
            positions.push_back(trickfish::Position::from_fen(fen));
            if (reference_terms(positions.back()) != incremental_terms(positions.back())) {
                throw std::runtime_error("evaluation term parity mismatch before timing");
            }
        }
        std::vector<Sample> reference, incremental;
        std::vector<double> ratios;
        for (int sample = 0; sample < 6; ++sample) {
            Sample old{}, cached{};
            if (sample % 2 == 0) {
                old = measure(positions, iterations, reference_terms);
                cached = measure(positions, iterations, incremental_terms);
            } else {
                cached = measure(positions, iterations, incremental_terms);
                old = measure(positions, iterations, reference_terms);
            }
            if (old.checksum != cached.checksum || (!reference.empty() && old.checksum != reference.front().checksum)) {
                throw std::runtime_error("nondeterministic evaluation checksum");
            }
            reference.push_back(old);
            incremental.push_back(cached);
            ratios.push_back(cached.nanoseconds / old.nanoseconds);
        }
        std::cout << "{\n  \"fixture_fens\": [";
        for (std::size_t index = 0; index < positions.size(); ++index) {
            if (index != 0) std::cout << ", ";
            std::cout << '\"' << positions[index].to_fen() << '\"';
        }
        std::cout << "],\n";
        std::cout << std::setprecision(17) << "  \"schema_version\": 1,\n  \"iterations\": " << iterations
            << ",\n  \"positions\": " << positions.size()
            << ",\n  \"scope\": \"material and piece activity reads; indirect-call overhead included; move updates excluded\","
            << "\n  \"samples\": [\n";
        for (std::size_t sample = 0; sample < reference.size(); ++sample) {
            if (sample != 0) std::cout << ",\n";
            std::cout << "    {\"reference_first\": " << (sample % 2 == 0 ? "true" : "false")
                << ", \"reference_ns\": " << reference[sample].nanoseconds
                << ", \"incremental_ns\": " << incremental[sample].nanoseconds
                << ", \"checksum\": " << reference[sample].checksum << "}";
        }
        std::cout << "\n  ],\n  \"median_paired_read_time_ratio\": " << median(ratios) << "\n}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
