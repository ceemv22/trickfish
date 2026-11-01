#pragma once

#include <algorithm>
#include <stdexcept>

#include "trickfish/evaluation.hpp"

namespace trickfish {

struct EvaluationWeights {
    int pawns = 100;
    int activity = 100;
    int king_safety = 100;

    [[nodiscard]] bool standard() const { return pawns == 100 && activity == 100 && king_safety == 100; }

    void validate() const {
        for (const int value : {pawns, activity, king_safety}) {
            if (value < 0 || value > 200) throw std::invalid_argument("evaluation weights must be between 0 and 200");
        }
    }

    [[nodiscard]] int apply(const Position& position, int baseline) const {
        int score = baseline;
        if (pawns != 100) {
            const int term = evaluate_pawn_structure(position);
            score += term * pawns / 100 - term;
        }
        if (activity != 100) {
            const int term = evaluate_piece_activity(position);
            score += term * activity / 100 - term;
        }
        if (king_safety != 100) {
            const int term = evaluate_king_safety(position);
            score += term * king_safety / 100 - term;
        }
        return score;
    }
};

}
