MASK_64 = (1 << 64) - 1
PIECE_ORDER = "PNBRQKpnbrqk"


def _key_stream(count: int) -> tuple[int, ...]:
    state = 0x9E3779B97F4A7C15
    keys: list[int] = []
    for _ in range(count):
        state = (state + 0x9E3779B97F4A7C15) & MASK_64
        value = state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK_64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK_64
        keys.append((value ^ (value >> 31)) & MASK_64)
    return tuple(keys)


KEYS = _key_stream(781)
PIECE_SQUARE_KEYS = tuple(
    KEYS[index * 64:(index + 1) * 64] for index in range(len(PIECE_ORDER))
)
SIDE_TO_MOVE_KEY = KEYS[768]
CASTLING_KEYS = dict(zip("KQkq", KEYS[769:773], strict=True))
EN_PASSANT_FILE_KEYS = dict(zip("abcdefgh", KEYS[773:781], strict=True))
PIECE_INDEX = {piece: index for index, piece in enumerate(PIECE_ORDER)}


def calculate_key(
    board: tuple[str | None, ...],
    side_to_move: str,
    castling: str,
    en_passant_file: str | None,
) -> int:
    key = 0
    for square, piece in enumerate(board):
        if piece is not None:
            key ^= PIECE_SQUARE_KEYS[PIECE_INDEX[piece]][square]
    if side_to_move == "b":
        key ^= SIDE_TO_MOVE_KEY
    for right in castling:
        if right != "-":
            key ^= CASTLING_KEYS[right]
    if en_passant_file is not None:
        key ^= EN_PASSANT_FILE_KEYS[en_passant_file]
    return key
