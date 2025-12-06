# qb_engine/test_place_card.py

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement


def _make_board_and_card():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()
    card_001 = hydrator.get_card("001")
    return board, card_001


def test_place_card_on_owned_tile():
    board, card_001 = _make_board_and_card()

    lane_name = "TOP"
    col_number = 1
    lane_index = 0
    col_index = col_number - 1

    assert is_legal_placement(board, lane_index, col_index, card_001) is True

    board.place_card(lane_name, col_number, card_001)

    tile = board.tile_at(lane_index, col_index)
    assert tile.card_id == card_001.id
    assert tile.owner == "Y"
    assert tile.rank == 1


if __name__ == "__main__":
    test_place_card_on_owned_tile()
    print("test_place_card_on_owned_tile: PASS")
