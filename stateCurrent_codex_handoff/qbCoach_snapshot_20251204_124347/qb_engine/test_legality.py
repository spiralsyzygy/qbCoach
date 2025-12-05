# qb_engine/test_legality.py

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement


def main():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()

    # Load a couple of real cards
    card_001 = hydrator.get_card("001")  # Security Officer, cost 1
    # If you know a higher-cost card ID, you can add it later

    print("Initial board:")
    board.print_board()
    print()

    # Test 1: legal placement - YOUR tile at TOP-1 with cost 1 card
    print("Test 1: TOP-1, card 001 (cost 1)")
    legal_1 = is_legal_placement(board, lane_index=0, col_index=0, card=card_001)
    print("  Expected: True")
    print("  Actual:  ", legal_1)
    print()

    # Test 2: illegal placement - NEUTRAL tile at TOP-2
    print("Test 2: TOP-2, card 001 (cost 1) - neutral tile")
    legal_2 = is_legal_placement(board, lane_index=0, col_index=1, card=card_001)
    print("  Expected: False")
    print("  Actual:  ", legal_2)
    print()

    # Test 3: illegal placement - ENEMY tile at TOP-5
    print("Test 3: TOP-5, card 001 (cost 1) - enemy tile")
    legal_3 = is_legal_placement(board, lane_index=0, col_index=4, card=card_001)
    print("  Expected: False")
    print("  Actual:  ", legal_3)
    print()

    # (Later we can add more tests for rank < cost, occupied tiles, etc.)


if __name__ == "__main__":
    main()
