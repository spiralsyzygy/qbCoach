# qb_engine/test_legality.py

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement


def _make_board_and_card():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()
    card_001 = hydrator.get_card("001")  # Security Officer, cost 1
    return board, card_001


def test_legality_allows_owned_tile_with_sufficient_rank():
    board, card_001 = _make_board_and_card()

    assert is_legal_placement(board, lane_index=0, col_index=0, card=card_001) is True


def test_legality_rejects_neutral_and_enemy_tiles():
    board, card_001 = _make_board_and_card()

    assert is_legal_placement(board, lane_index=0, col_index=1, card=card_001) is False
    assert is_legal_placement(board, lane_index=0, col_index=4, card=card_001) is False


if __name__ == "__main__":
    test_legality_allows_owned_tile_with_sufficient_rank()
    test_legality_rejects_neutral_and_enemy_tiles()
    print("test_legality_allows_owned_tile_with_sufficient_rank: PASS")
    print("test_legality_rejects_neutral_and_enemy_tiles: PASS")
