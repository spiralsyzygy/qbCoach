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

        rowOffset = pRowIndex - 2
        colOffset = pColIndex - 2
        lane'     = lane - rowOffset
        col'      = col  + colOffset

    Only cells with "P", "E", or "X" in card.grid are returned.
    Off-board targets are discarded.
    """

    targets: List[ProjectionTarget] = []

    # card.grid is a 5x5 list of strings like ".", "P", "E", "X", "W"
    for p_row_index, row in enumerate(card.grid):
        for p_col_index, cell in enumerate(row):
            if cell not in ("P", "E", "X"):
                continue

            row_offset = p_row_index - 2
            col_offset = p_col_index - 2

            lane_prime = root_lane_index - row_offset
            col_prime = root_col_index + col_offset

            # Keep only tiles that land on the 3x5 board
            if 0 <= lane_prime < 3 and 0 <= col_prime < 5:
                targets.append((lane_prime, col_prime, cell))

    return ProjectionResult(
        root_lane_index=root_lane_index,
        root_col_index=root_col_index,
        targets=targets,
    )


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

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("P", "X"):
            continue  # ignore pure effect-only tiles here

        tile = board.tiles[lane_index][col_index]

        # No hidden pawn stack under occupied tiles
        if tile.card_id is not None:
            continue

        board.add_pawn_delta_for_you(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            amount=1,
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

    description = getattr(card, "effect", "") or ""

    for lane_index, col_index, kind in proj.targets:
        if kind not in ("E", "X"):
            continue

        board.add_effect_aura(
            lane_index=lane_index,
            col_index=col_index,
            card_id=card.id,
            description=description,
        )
