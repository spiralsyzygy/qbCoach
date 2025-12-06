from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import compute_projection_targets, LANE_INDEX_TO_NAME


def _make_board_and_card():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()
    card = hydrator.get_card("001")  # Security Officer
    return board, card


def test_projection_targets_for_security_officer():
    board, card = _make_board_and_card()

    lane_name = "MID"
    col_number = 1
    lane_index = LANE_NAME_TO_INDEX[lane_name]
    col_index = col_number - 1

    assert is_legal_placement(board, lane_index, col_index, card) is True

    proj_result = compute_projection_targets(lane_index, col_index, card)

    expected_targets = [
        (2, 0, "P"),  # BOT-1
        (1, 1, "P"),  # MID-2
        (0, 0, "P"),  # TOP-1
    ]
    assert proj_result.targets == expected_targets
    assert proj_result.root_lane_index == lane_index
    assert proj_result.root_col_index == col_index

    for (t_lane_index, t_col_index, kind), (exp_lane, exp_col, exp_kind) in zip(
        proj_result.targets, expected_targets
    ):
        assert (t_lane_index, t_col_index, kind) == (exp_lane, exp_col, exp_kind)
        assert LANE_INDEX_TO_NAME[t_lane_index] in ("TOP", "MID", "BOT")


if __name__ == "__main__":
    test_projection_targets_for_security_officer()
    print("test_projection_targets_for_security_officer: PASS")
