# qb_engine/projection.py

from dataclasses import dataclass
from typing import List, Tuple

from qb_engine.board_state import BoardState   # NOW AT TOP
from qb_engine.models import Card


# For clarity: (lane_index, col_index, kind) where kind is "P", "E", or "X"
ProjectionTarget = Tuple[int, int, str]

LANE_INDEX_TO_NAME = {
    0: "TOP",
    1: "MID",
    2: "BOT",
}


def _pattern_index_to_offsets(p_row_index: int, p_col_index: int) -> tuple[int, int]:
    """
    Convert pattern grid indices to board offsets.

    Pattern grid convention (to avoid collision with board columns):
      - Columns are letters E,D,C,B,A (left→right) in the JSON grid indices 0..4.
      - Rows are numbers 1..5 (top→bottom) in the JSON grid indices 0..4.
      - W is always at (col=C, row=3) => indices (2, 2).

    Returned offsets are relative to the placement tile on the board:
      row_offset: -2..+2 added to the lane index (top/bot)
      col_offset: -2..+2 added to the board column index (left/right)
    """
    row_offset = p_row_index - 2  # numbers 1..5 top→bottom -> -2..+2
    col_offset = p_col_index - 2  # letters E..A left→right -> -2..+2
    return row_offset, col_offset


@dataclass
class ProjectionResult:
    """
    Holds the board-relative projection targets for a single card placement.

    Each target is:
      (lane_index, col_index, kind)
    where:
      - lane_index: 0=TOP, 1=MID, 2=BOT
      - col_index:  0..4 (1..5 to the player)
      - kind: "P", "E", or "X"
    """
    root_lane_index: int
    root_col_index: int
    targets: List[ProjectionTarget]


def compute_projection_targets(
    root_lane_index: int,
    root_col_index: int,
    card: Card,
) -> ProjectionResult:
    """
    Given a placement tile (root_lane_index, root_col_index) for `card`,
    compute all on-board projection targets derived from the card.grid.

    Uses the mapping from the rules:

        rowOffset = pRowIndex - 2   # pattern rows 1..5 (top→bottom), W at row 3
        colOffset = pColIndex - 2   # pattern cols E..A (left→right), W at col C
        lane'     = lane + rowOffset
        col'      = col  + colOffset

    Only cells with "P", "E", or "X" in card.grid are returned.
    Off-board targets are discarded.
    """

    targets: List[ProjectionTarget] = []

    # Use pattern-derived projection cells as the authoritative source.
    for cell in card.projection_cells:
        if cell.symbol not in ("P", "E", "X"):
            continue

        lane_prime = root_lane_index + cell.row_offset
        col_prime = root_col_index + cell.col_offset

        if 0 <= lane_prime < 3 and 0 <= col_prime < 5:
            targets.append((lane_prime, col_prime, cell.symbol))

    return ProjectionResult(
        root_lane_index=root_lane_index,
        root_col_index=root_col_index,
        targets=targets,
    )


def compute_projection_targets_for_enemy(
    root_lane_index: int,
    root_col_index: int,
    card: Card,
) -> ProjectionResult:
    """
    Enemy-side projection: mirror the horizontal direction compared to the Y side.

    For Y we use col' = root_col_index + col_offset; enemy uses col' = root_col_index - col_offset.
    Lane computation remains the same.
    """
    targets: List[ProjectionTarget] = []

    for cell in card.projection_cells:
        if cell.symbol not in ("P", "E", "X"):
            continue

        lane_prime = root_lane_index + cell.row_offset
        col_prime = root_col_index - cell.col_offset  # mirrored horizontally

        if 0 <= lane_prime < 3 and 0 <= col_prime < 5:
            targets.append((lane_prime, col_prime, cell.symbol))

    return ProjectionResult(
        root_lane_index=root_lane_index,
        root_col_index=root_col_index,
        targets=targets,
    )


SPECIAL_PAWN_AMOUNT = {
    # Supercharged P tiles: use these values instead of +1
    "on_play_raise_positions_rank_2": 2,
    "on_play_raise_positions_rank_3": 3,
}


def _pawn_amount_for_card(card: Card) -> int:
    """Return pawn delta amount for P/X tiles (default 1, overrides for special cards)."""
    return SPECIAL_PAWN_AMOUNT.get(getattr(card, "effect_id", None), 1)


def apply_pawns_for_you(board: BoardState, proj: ProjectionResult, card: Card) -> None:
    """
    Apply pawn projections (P/X tiles) for YOU to the given board.

    Instead of mutating tiles directly, we:
      - Log PawnDelta entries for each affected EMPTY tile.
      - Recompute tile owner/rank from base_influence + all PawnDeltas.

    Rules:
      - Only apply pawn changes to EMPTY tiles (no hidden stacks under cards).
      - X is treated as including a P component here; E component is handled elsewhere.
    """

    amount = _pawn_amount_for_card(card)

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("P", "X"):
            continue  # ignore pure effect-only tiles here

        board.add_pawn_delta_for_you(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            amount=amount,
        )

    board.recompute_influence_from_deltas()


def apply_pawns_for_enemy(board: BoardState, proj: ProjectionResult, card: Card) -> None:
    """
    Apply pawn projections (P/X tiles) for ENEMY placements.

    Mirrors apply_pawns_for_you but records negative deltas.
    """
    amount = _pawn_amount_for_card(card)

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("P", "X"):
            continue

        board.add_pawn_delta_for_enemy(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            amount=amount,
        )

    board.recompute_influence_from_deltas()


def apply_effects_for_you(board: BoardState, proj: ProjectionResult, card: Card) -> None:
    """
    Apply effect projections (E/X tiles) for YOU to the given board.

    Rules:
      - E and X tiles project an effect "aura" onto their target tiles.
      - Auras exist whether or not the tile is occupied.
      - Any card currently on, or later played onto, an affected tile will
        be subject to the source card's effect.

    This function does NOT yet implement the semantics of that effect
    (buff/debuff/destroy/etc.); it only records where the aura lives.
    """

    description = getattr(card, "effect_description", None) or getattr(card, "effect", "") or ""

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("E", "X"):
            continue

        board.add_effect_aura(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            description=description,
        )


def apply_effects_for_enemy(board: BoardState, proj: ProjectionResult, card: Card) -> None:
    """
    Apply effect projections (E/X tiles) for ENEMY placements.

    Mirrors apply_effects_for_you.
    """
    description = getattr(card, "effect_description", None) or getattr(card, "effect", "") or ""

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("E", "X"):
            continue

        board.add_effect_aura(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            description=description,
        )
