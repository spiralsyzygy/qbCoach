# qb_engine/legality.py

from qb_engine.board_state import BoardState
from qb_engine.models import Card


def is_legal_placement(
    board: BoardState,
    lane_index: int,
    col_index: int,
    card: Card,
) -> bool:
    """
    Basic placement legality check (LegalityChecker v2, simplified):

    A card may be played on a tile if and only if:
      1. Tile is empty (no card_id).
      2. Tile is owned by YOU ("Y").
      3. Tile's rank >= card.cost.

    For now, we treat Tile.rank as the visibleRank for the owning side.
    """

    # Bounds check: lane_index ∈ {0,1,2}, col_index ∈ {0..4}
    if lane_index < 0 or lane_index >= len(board.tiles):
        return False
    if col_index < 0 or col_index >= len(board.tiles[0]):
        return False

    tile = board.tiles[lane_index][col_index]

    # 1. Must be empty
    if tile.card_id is not None:
        return False

    # 2. Must be owned by YOU
    if tile.owner != "Y":
        return False

    # 3. Tile rank must be sufficient for card cost
    if tile.rank < card.cost:
        return False

    return True
