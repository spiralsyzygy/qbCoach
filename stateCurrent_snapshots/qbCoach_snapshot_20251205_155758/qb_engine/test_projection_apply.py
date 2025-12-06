from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    compute_projection_targets,
    apply_pawns_for_you,
)


def _make_board_and_card():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()
    card = hydrator.get_card("001")  # Security Officer
    return board, card


def test_apply_pawn_projections_for_security_officer():
    board, card = _make_board_and_card()

    lane_name = "MID"
    col_number = 1
    lane_index = LANE_NAME_TO_INDEX[lane_name]
    col_index = col_number - 1

    assert is_legal_placement(board, lane_index, col_index, card) is True

    board.place_card(lane_name, col_number, card)

    proj = compute_projection_targets(lane_index, col_index, card)

    expected_targets = [
        (2, 0, "P"),  # BOT-1
        (1, 1, "P"),  # MID-2
        (0, 0, "P"),  # TOP-1
    ]
    assert proj.targets == expected_targets

    apply_pawns_for_you(board, proj, card)

    tile_expectations = {
        (2, 0): ("Y", 2),
        (1, 1): ("Y", 1),
        (0, 0): ("Y", 2),
    }

    for (t_lane, t_col), (owner, rank) in tile_expectations.items():
        tile = board.tile_at(t_lane, t_col)
        assert tile.owner == owner
        assert tile.rank == rank

    assert len(board.pawn_deltas) == len(expected_targets)
    assert board.tile_at(lane_index, col_index).card_id == card.id


if __name__ == "__main__":
    test_apply_pawn_projections_for_security_officer()
    print("test_apply_pawn_projections_for_security_officer: PASS")
