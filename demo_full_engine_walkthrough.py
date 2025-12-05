"""
demo_full_engine_walkthrough.py

Smallest reproducible example of scoring in the live engine.
Walks through: hydrate cards, show legality, place YOU card with projections,
place ENEMY card with mirrored projections, show effective power overlays, and
compute lane + match scoring. Intended as a quick-start blueprint and
debugging harness.
"""

from __future__ import annotations

from pathlib import Path

from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    apply_effects_for_enemy,
    apply_effects_for_you,
    apply_pawns_for_enemy,
    apply_pawns_for_you,
    compute_projection_targets,
    compute_projection_targets_for_enemy,
)
from qb_engine.scoring import compute_match_score


# Invert the lane name mapping so we can go index -> name
LANE_INDEX_TO_NAME = {v: k for k, v in LANE_NAME_TO_INDEX.items()}


def header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def find_first_legal_placement(board: BoardState, card) -> tuple[int, int] | None:
    """
    Scan the board for the first legal placement for YOU using the current legality rules.
    Returns (lane_index, col_index) or None if nothing is legal.
    """
    for lane_index in range(3):
        for col_index in range(5):
            if is_legal_placement(board, lane_index, col_index, card):
                return lane_index, col_index
    return None


def describe_board(board: BoardState, effect_engine: EffectEngine | None = None) -> None:
    """
    Print the board; if effect_engine is supplied, include auras and effective power.
    """
    if effect_engine is None:
        board.print_board()
    else:
        board.print_board_with_effects_and_power(effect_engine)


def main() -> None:
    # ------------------------------------------------------------------ #
    # 0. Wiring: locate data files, hydrate cards, construct effect engine
    # ------------------------------------------------------------------ #
    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"

    cards_path = data_dir / "qb_DB_Complete_v2.json"
    effects_path = data_dir / "qb_effects_v1.json"

    hydrator = CardHydrator(str(cards_path))
    effect_engine = EffectEngine(effects_path, hydrator)

    # Choose a simple "P-only" card for YOU and a second card for ENEMY.
    # Swap IDs as desired for exploration.
    you_card = hydrator.get_card("001")  # Security Officer (simple pattern)
    enemy_card = hydrator.get_card("003")  # Grenadier (used in effect tests)

    # ------------------------------------------------------------------ #
    # 1. Initial board
    # ------------------------------------------------------------------ #
    board = BoardState.create_initial_board()

    header("Step 1 — Initial board (ownership / ranks only)")
    describe_board(board)

    # ------------------------------------------------------------------ #
    # 2. Show legal placements for your card
    # ------------------------------------------------------------------ #
    header(f"Step 2 — Legal placements for YOU card {you_card.id} ({you_card.name})")

    legal = []
    for lane_index in range(3):
        for col_index in range(5):
            if is_legal_placement(board, lane_index, col_index, you_card):
                lane_name = LANE_INDEX_TO_NAME[lane_index]
                col_number = col_index + 1
                legal.append((lane_index, col_index))
                print(f"  • {lane_name} {col_number}")

    if not legal:
        print("No legal placements found for this card on the initial board.")
        return

    # For demo purposes, pick the first legal tile
    lane_index_y, col_index_y = legal[0]
    lane_name_y = LANE_INDEX_TO_NAME[lane_index_y]
    col_number_y = col_index_y + 1

    print(
        f"\nChoosing first legal placement for YOU: "
        f"{lane_name_y} {col_number_y} for {you_card.id} ({you_card.name})"
    )

    # ------------------------------------------------------------------ #
    # 3. Play your card: place + projection + effects
    # ------------------------------------------------------------------ #
    header("Step 3 — Applying your play (place card + projection + effects)")

    # Place the card (also applies any on_play effects via EffectEngine)
    board.place_card(lane_name_y, col_number_y, you_card, effect_engine)

    print("Board after placing your card (no projection yet):")
    describe_board(board)

    # Compute and apply pawn/effect projections for YOU
    proj_you = compute_projection_targets(lane_index_y, col_index_y, you_card)
    apply_pawns_for_you(board, proj_you, you_card)
    apply_effects_for_you(board, proj_you, you_card)

    print("\nBoard after your pawn/effect projections and influence recompute:")
    describe_board(board)

    # ------------------------------------------------------------------ #
    # 4. Enemy plays a card with mirrored projection
    # ------------------------------------------------------------------ #
    header(
        f"Step 4 — Enemy play: place ENEMY card {enemy_card.id} ({enemy_card.name})"
    )

    # For the demo, place enemy card on their right-side column in MID lane.
    # (This ignores enemy-side legality checks; it's just to exercise projection.)
    lane_index_e = 1  # MID
    col_index_e = 4  # column 5 (enemy's home side)
    lane_name_e = LANE_INDEX_TO_NAME[lane_index_e]
    col_number_e = col_index_e + 1

    print(
        f"Placing ENEMY card at {lane_name_e} {col_number_e} "
        f"({enemy_card.id} {enemy_card.name})"
    )

    board.place_card(lane_name_e, col_number_e, enemy_card, effect_engine)

    print("Board after enemy card placement (no projection yet):")
    describe_board(board)

    # Compute mirrored projection for enemy and apply pawn/effect changes
    proj_enemy = compute_projection_targets_for_enemy(
        lane_index_e, col_index_e, enemy_card
    )
    apply_pawns_for_enemy(board, proj_enemy, enemy_card)
    apply_effects_for_enemy(board, proj_enemy, enemy_card)

    print("\nBoard after enemy pawn/effect projections and influence recompute:")
    describe_board(board)

    # ------------------------------------------------------------------ #
    # 5. Show auras and EFFECTIVE power using EffectEngine
    # ------------------------------------------------------------------ #
    header("Step 5 — Board with auras and EFFECTIVE power per occupied tile")

    print(
        "Conventions:\n"
        "  • Empty tiles: [Y1] / [N0] / [E1] (with ★ if they have any auras)\n"
        "  • Occupied tiles: [CARD_ID:effective_power] (★ if the tile has auras)\n"
    )
    describe_board(board, effect_engine=effect_engine)

    # ------------------------------------------------------------------ #
    # 6. Scoring: lane scores + match score
    # ------------------------------------------------------------------ #
    header("Step 6 — Scoring summary (lane scores + match total)")

    match_score = compute_match_score(board, effect_engine)

    for lane_score in match_score.lanes:
        lane_name = LANE_INDEX_TO_NAME[lane_score.lane_index]
        print(
            f"{lane_name}: "
            f"you={lane_score.power_you}, "
            f"enemy={lane_score.power_enemy}, "
            f"winner={lane_score.winner}, "
            f"lane_points={lane_score.lane_points}"
        )

    print(
        "\nMATCH TOTAL:"
        f"\n  YOU   = {match_score.total_you}"
        f"\n  ENEMY = {match_score.total_enemy}"
        f"\n  WINNER= {match_score.winner}"
        f"\n  MARGIN= {match_score.margin}"
    )


if __name__ == "__main__":
    main()
