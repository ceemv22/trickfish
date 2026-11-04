def replay_uci_line(position, moves):
    for uci in moves:
        legal = {move.to_uci(): move for move in position.legal_moves()}
        if uci not in legal:
            raise ValueError("illegal variation move " + str(uci) + " in " + position.to_fen())
        position = position.make_move(legal[uci])
    return position
