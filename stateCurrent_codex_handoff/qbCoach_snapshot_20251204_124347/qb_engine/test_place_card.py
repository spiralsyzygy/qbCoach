# qb_engine/test_place_card.py

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement


def main():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()

    card_001 = hydrator.get_card("001")  # Security Officer, cost 1

    print("Initial board:")
    board.print_board()
    print()

    # We'll try to play card_001 at TOP-1
    lane_name = "TOP"
    col_number = 1

    lane_index = 0  # TOP
    col_index = col_number - 1

    legal = is_legal_placement(board, lane_index, col_index, card_001)
    print(f"Is placement at {lane_name}-{col_number} legal?", legal)

    if legal:
        board.place_card(lane_name, col_number, card_001)
        print("\nBoard after placing card 001 at TOP-1:")
        board.print_board()


if __name__ == "__main__":
    main()
