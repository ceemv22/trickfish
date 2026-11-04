#include "trickfish/evaluation_weights.hpp"

namespace trickfish {

int EvaluationWeights::apply(const Position& position, int baseline) const {
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

}
