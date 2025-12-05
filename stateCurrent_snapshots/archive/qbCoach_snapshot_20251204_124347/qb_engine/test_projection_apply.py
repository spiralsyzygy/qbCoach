# qb_engine/test_projection_apply.py

from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    compute_projection_targets,
    apply_pawns_for_you,
    LANE_INDEX_TO_NAME,
)


def main():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()

    card = hydrator.get_card("001")  # Security Officer

    # We'll play at MID-1 again
    lane_name = "MID"
    col_number = 1
    lane_index = LANE_NAME_TO_INDEX[lane_name]
    col_index = col_number - 1

    print("Initial board:")
    board.print_board()
    print()

    legal = is_legal_placement(board, lane_index, col_index, card)
    print(f"Is placement at {lane_name}-{col_number} legal? {legal}")
    if not legal:
        print("Aborting test: placement is illegal.")
        return

    # 1) Place the card
    board.place_card(lane_name, col_number, card)

    print(f"\nBoard after placing {card.id} at {lane_name}-{col_number}:")
    board.print_board()
    print()

    # 2) Compute projection targets
    proj = compute_projection_targets(lane_index, col_index, card)

    print("Projection targets (P/E/X):")
    for t_lane_index, t_col_index, kind in proj.targets:
        t_lane_name = LANE_INDEX_TO_NAME[t_lane_index]
        t_col_num = t_col_index + 1
        print(f"  {kind} -> {t_lane_name}-{t_col_num} (lane={t_lane_index}, col={t_col_index})")

    # 3) Apply pawn projections for YOU
    apply_pawns_for_you(board, proj, card)

    print("\nBoard after applying pawn projections:")
    board.print_board()


if __name__ == "__main__":
    main()
