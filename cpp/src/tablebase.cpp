#include "trickfish/tablebase.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <filesystem>
#include <mutex>
#include <stdexcept>
#include <utility>

#include "trickfish/movegen.hpp"

#ifdef TRICKFISH_FATHOM
#include <tbprobe.h>
#endif

namespace trickfish {
namespace {

std::recursive_mutex& tablebase_mutex() {
    static std::recursive_mutex mutex;
    return mutex;
}

}

struct SyzygyTablebase::State {
    std::string path;
    unsigned largest = 0;
    explicit State(std::string directory) : path(std::move(directory)) {
#ifdef TRICKFISH_FATHOM
        if (!tb_init(path.c_str())) throw std::invalid_argument("Syzygy initialization failed");
        largest = TB_LARGEST;
        if (largest == 0) {
            tb_free();
            throw std::invalid_argument("no supported Syzygy WDL files in directory");
        }
#endif
    }
    ~State() {
        const std::lock_guard lock(tablebase_mutex());
#ifdef TRICKFISH_FATHOM
        tb_free();
#endif
    }
};

bool SyzygyTablebase::available() {
#ifdef TRICKFISH_FATHOM
    return true;
#else
    return false;
#endif
}

SyzygyTablebase::SyzygyTablebase(std::shared_ptr<State> state) : state_(std::move(state)) {}

std::shared_ptr<SyzygyTablebase> SyzygyTablebase::open(const std::string& directory) {
    if (!available()) throw std::invalid_argument("this build has no Fathom backend");
    if (!std::filesystem::is_directory(directory)) throw std::invalid_argument("Syzygy path must be an existing directory");
    const auto canonical = std::filesystem::canonical(directory).string();
    const std::lock_guard lock(tablebase_mutex());
    static std::weak_ptr<State> current;
    auto state = current.lock();
    if (state && state->path != canonical) throw std::invalid_argument("disable the current Syzygy directory before changing it");
    if (!state) {
        state = std::make_shared<State>(canonical);
        current = state;
    }
    return std::shared_ptr<SyzygyTablebase>(new SyzygyTablebase(std::move(state)));
}

const std::string& SyzygyTablebase::directory() const { return state_->path; }

std::optional<TablebaseRoot> SyzygyTablebase::probe(const Position& position) const {
#ifdef TRICKFISH_FATHOM
    if (position.castling_rights() != 0 || std::popcount(position.occupancy()) > static_cast<int>(state_->largest) ||
        position.in_check(opposite(position.side_to_move()))) return std::nullopt;
    auto copy = position;
    const auto legal = generate_legal_moves(copy);
    if (legal.empty() || legal.size() >= TB_MAX_MOVES) return std::nullopt;
    const auto white = std::byteswap(position.occupancy(Color::white));
    const auto black = std::byteswap(position.occupancy(Color::black));
    const auto bits = [&position](PieceType type) {
        return std::byteswap(position.pieces(Color::white, type) | position.pieces(Color::black, type));
    };
    const auto ep = position.en_passant_square() < 0 ? 0U : static_cast<unsigned>(position.en_passant_square() ^ 56);
    std::array<unsigned, TB_MAX_MOVES> encoded;
    encoded.fill(TB_RESULT_FAILED);
    const std::lock_guard lock(tablebase_mutex());
    const auto result = tb_probe_root(white, black, bits(PieceType::king), bits(PieceType::queen), bits(PieceType::rook),
        bits(PieceType::bishop), bits(PieceType::knight), bits(PieceType::pawn),
        static_cast<unsigned>(position.halfmove_clock()), 0, ep, position.side_to_move() == Color::white, encoded.data());
    if (result == TB_RESULT_FAILED || result == TB_RESULT_CHECKMATE || result == TB_RESULT_STALEMATE) return std::nullopt;
    const auto decode = [&legal](unsigned value) -> std::optional<TablebaseMove> {
        constexpr std::array promotions = {'\0', 'q', 'r', 'b', 'n'};
        const auto promotion = TB_GET_PROMOTES(value);
        if (promotion >= promotions.size() || TB_GET_WDL(value) > TB_WIN || TB_GET_FROM(value) == TB_GET_TO(value)) return std::nullopt;
        const Move decoded(static_cast<std::uint8_t>(TB_GET_FROM(value) ^ 56), static_cast<std::uint8_t>(TB_GET_TO(value) ^ 56),
            promotions[promotion], TB_GET_EP(value) != 0);
        if (std::find(legal.begin(), legal.end(), decoded) == legal.end()) return std::nullopt;
        return TablebaseMove{decoded, static_cast<int>(TB_GET_WDL(value)), TB_GET_DTZ(value)};
    };
    const auto recommended = decode(result);
    if (!recommended) return std::nullopt;
    TablebaseRoot root{recommended->move, recommended->wdl, recommended->dtz, {}};
    for (const auto value : encoded) {
        if (value == TB_RESULT_FAILED) break;
        const auto entry = decode(value);
        if (!entry || std::any_of(root.moves.begin(), root.moves.end(), [&](const auto& prior) { return prior.move == entry->move; })) return std::nullopt;
        root.moves.push_back(*entry);
    }
    if (root.moves.size() != legal.size()) return std::nullopt;
    return root;
#else
    static_cast<void>(position);
    return std::nullopt;
#endif
}

int tablebase_score(int wdl) {
    if (wdl < 0 || wdl > 4) throw std::invalid_argument("invalid five-valued tablebase outcome");
    return wdl == 4 ? tablebase_win_score : wdl == 0 ? -tablebase_win_score : 0;
}

std::optional<TablebaseMove> select_tablebase_root(Position& position, const TablebaseProvider& provider,
    const std::vector<Move>& allowed, const RepetitionHistory* history, MoveCountDrawPolicy policy) {
    if (policy != MoveCountDrawPolicy::claim_fifty_moves || position.castling_rights() != 0 ||
        position.is_insufficient_material() || is_move_count_draw(position, policy)) return std::nullopt;
    if (history != nullptr && (history->current_key() != position.key() || history->current_count() > 1 ||
        (history->size() > 1 && position.halfmove_clock() != 0))) return std::nullopt;
    const auto legal = generate_legal_moves(position);
    if (legal.empty()) return std::nullopt;
    const auto root = provider.probe(position);
    if (!root || root->moves.size() != legal.size() || root->wdl < 0 || root->wdl > 4 || root->dtz > 4095 ||
        std::find(legal.begin(), legal.end(), root->recommended) == legal.end()) return std::nullopt;
    std::vector<Move> seen;
    std::optional<TablebaseMove> selected;
    for (const auto& entry : root->moves) {
        if (entry.wdl < 0 || entry.wdl > 4 || entry.dtz > 4095 ||
            std::find(legal.begin(), legal.end(), entry.move) == legal.end() ||
            std::find(seen.begin(), seen.end(), entry.move) != seen.end()) return std::nullopt;
        seen.push_back(entry.move);
        if (!allowed.empty() && std::find(allowed.begin(), allowed.end(), entry.move) == allowed.end()) continue;
        if (!selected || tablebase_score(entry.wdl) > tablebase_score(selected->wdl) ||
            (tablebase_score(entry.wdl) == tablebase_score(selected->wdl) && entry.move == root->recommended)) selected = entry;
    }
    return selected;
}

}
