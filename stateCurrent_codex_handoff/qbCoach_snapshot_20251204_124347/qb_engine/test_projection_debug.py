from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import compute_projection_targets, LANE_INDEX_TO_NAME


def main():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()

    card = hydrator.get_card("001")  # Security Officer

    # Use a legal tile: MID-1 (your side, rank 1)
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
        print("Aborting projection test because placement is illegal.")
        return

    proj_result = compute_projection_targets(lane_index, col_index, card)

    print(f"\nProjection targets for card {card.id} {card.name} at {lane_name}-{col_number}:")
    for t_lane_index, t_col_index, kind in proj_result.targets:
        t_lane_name = LANE_INDEX_TO_NAME[t_lane_index]
        t_col_number = t_col_index + 1
        print(f"  {kind} → {t_lane_name}-{t_col_number} (lane_index={t_lane_index}, col_index={t_col_index})")


if __name__ == "__main__":
    main()
