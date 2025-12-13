# qb_engine/test_effect_auras.py

from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    compute_projection_targets,
    apply_pawns_for_you,
    apply_effects_for_you,
)


def _make_board_and_card():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()

    # For now we can use card 001 as a test harness.
    # If its grid has no E/X tiles, you won't see ★, but the code path will run.
    card = hydrator.get_card("001")
    return board, card


def test_apply_effects_for_p_only_card_adds_no_auras():
    board, card = _make_board_and_card()

    lane_name = "MID"
    col_number = 1
    lane_index = LANE_NAME_TO_INDEX[lane_name]
    col_index = col_number - 1

    assert is_legal_placement(board, lane_index, col_index, card) is True

    board.place_card(lane_name, col_number, card)

    proj = compute_projection_targets(lane_index, col_index, card)

    expected_targets = {
        (0, 0, "P"),
        (1, 1, "P"),
        (2, 0, "P"),
    }
    assert set(proj.targets) == expected_targets

    apply_pawns_for_you(board, proj, card)
    apply_effects_for_you(board, proj, card)

    assert board.effect_auras == []
    assert board.pawn_deltas  # pawn projections were applied

    for t_lane_index, t_col_index, kind in expected_targets:
        tile = board.tile_at(t_lane_index, t_col_index)
        assert tile.owner == "Y"
        assert kind == "P"  # No E/X tiles for this card


if __name__ == "__main__":
    test_apply_effects_for_p_only_card_adds_no_auras()
    print("test_apply_effects_for_p_only_card_adds_no_auras: PASS")
