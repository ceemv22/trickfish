#pragma once

#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "trickfish/draw.hpp"
#include "trickfish/history.hpp"

namespace trickfish {

inline constexpr int tablebase_win_score = 50000;

struct TablebaseMove {
    Move move;
    int wdl = 2;
    unsigned dtz = 0;
};

struct TablebaseRoot {
    Move recommended;
    int wdl = 2;
    unsigned dtz = 0;
    std::vector<TablebaseMove> moves;
};

class TablebaseProvider {
public:
    virtual ~TablebaseProvider() = default;
    [[nodiscard]] virtual std::optional<TablebaseRoot> probe(const Position& position) const = 0;
};

class SyzygyTablebase final : public TablebaseProvider {
public:
    [[nodiscard]] static bool available();
    [[nodiscard]] static std::shared_ptr<SyzygyTablebase> open(const std::string& directory);
    [[nodiscard]] std::optional<TablebaseRoot> probe(const Position& position) const override;
    [[nodiscard]] const std::string& directory() const;
private:
    struct State;
    explicit SyzygyTablebase(std::shared_ptr<State> state);
    std::shared_ptr<State> state_;
};

[[nodiscard]] int tablebase_score(int wdl);
[[nodiscard]] std::optional<TablebaseMove> select_tablebase_root(Position& position, const TablebaseProvider& provider,
    const std::vector<Move>& allowed, const RepetitionHistory* history, MoveCountDrawPolicy policy);

}
