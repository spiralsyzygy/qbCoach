# qb_engine/test_board.py

from qb_engine.board_state import BoardState


def test_initial_board_layout():
    board = BoardState.create_initial_board()

    assert len(board.tiles) == 3
    assert all(len(row) == 5 for row in board.tiles)

    for row in board.tiles:
        left = row[0]
        right = row[-1]

        assert left.owner == "Y"
        assert left.rank == 1
        assert left.base_influence == 1
        assert left.card_id is None

        assert right.owner == "E"
        assert right.rank == 1
        assert right.base_influence == -1
        assert right.card_id is None

        for tile in row[1:-1]:
            assert tile.owner == "N"
            assert tile.rank == 0
            assert tile.base_influence == 0
            assert tile.card_id is None


if __name__ == "__main__":
    test_initial_board_layout()
    print("test_initial_board_layout: PASS")
