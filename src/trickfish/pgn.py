def san_for_move(position, move, legal=None):
    legal = position.legal_moves() if legal is None else legal
    if move not in legal:
        raise ValueError("SAN move is not legal")
    symbol = position.board[move.from_square]
    kind = symbol.upper()
    origin, target = move.to_uci()[:2], move.to_uci()[2:4]
    capture = move.en_passant or position.board[move.to_square] is not None
    if move.castling:
        text = "O-O" if move.to_square > move.from_square else "O-O-O"
    else:
        text = "" if kind == "P" else kind
        if kind == "P":
            if capture: text += origin[0]
        else:
            rivals = [other for other in legal if other.from_square != move.from_square and
                other.to_square == move.to_square and position.board[other.from_square] == symbol]
            if rivals:
                if all(other.from_square % 8 != move.from_square % 8 for other in rivals):
                    text += origin[0]
                elif all(other.from_square // 8 != move.from_square // 8 for other in rivals):
                    text += origin[1]
                else:
                    text += origin
        text += ("x" if capture else "") + target
        if move.promotion is not None: text += "=" + move.promotion.upper()
    child = position.make_move(move)
    status = child.game_status()
    if status == "checkmate": text += "#"
    elif child.is_in_check(): text += "+"
    return text


def tag_value(value):
    text = "".join(character if ord(character) >= 32 and ord(character) != 127 else " " for character in str(value))
    return text.replace("\\", "\\\\").replace('"', '\\"')


