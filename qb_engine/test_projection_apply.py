from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    compute_projection_targets,
    apply_pawns_for_you,
    apply_effects_for_you,
)
from qb_engine.models import Card


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

    expected_targets = {
        (0, 0, "P"),  # TOP-1 (pattern col C, row 2)
        (1, 1, "P"),  # MID-2 (pattern col B, row 3)
        (2, 0, "P"),  # BOT-1 (pattern col C, row 4)
    }
    assert set(proj.targets) == expected_targets

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


def _make_x_test_card(card_id: str = "XTEST", effect: str = "test aura") -> Card:
    grid = [["."] * 5 for _ in range(5)]
    grid[2][2] = "W"
    grid[2][3] = "X"  # project to the right of placement
    projection_cells = [
        # W plus one X to the right
        type("pc", (), {"row_offset": 0, "col_offset": 0, "symbol": "W"})(),
        type("pc", (), {"row_offset": 0, "col_offset": 1, "symbol": "X"})(),
    ]
    return Card(
        id=card_id,
        name="X Card",
        category="Test",
        cost=0,
        power=0,
        pattern="",
        grid=grid,
        effect_description=effect,
        projection_cells=projection_cells,
    )


def _apply_you_projection(board: BoardState, lane: int, col: int, card: Card):
    proj = compute_projection_targets(lane, col, card)
    apply_pawns_for_you(board, proj, card)
    apply_effects_for_you(board, proj, card)


def test_x_applies_pawn_and_effect():
    board = BoardState.create_initial_board()
    card = _make_x_test_card()
    # Place at MID-3 (lane 1, col 2); X targets lane 1, col 3
    _apply_you_projection(board, 1, 2, card)
    target = board.tile_at(1, 3)
    assert target.owner == "Y"
    assert target.rank >= 1
    auras = board.auras_at(1, 3)
    assert any(a.card_id == card.id for a in auras)


def test_x_on_enemy_occupied_tile_flips_and_marks():
    board = BoardState.create_initial_board()
    card = _make_x_test_card(card_id="FLIP")
    enemy_card = _make_x_test_card(card_id="ENEMY")
    # Simulate enemy occupying MID-4 (lane 1, col 3)
    board.place_card("MID", 4, enemy_card)
    board.tile_at(1, 3).owner = "E"
    board.tile_at(1, 3).rank = 1
    # Your X projection onto that tile (from MID-3)
    _apply_you_projection(board, 1, 2, card)
    target = board.tile_at(1, 3)
    assert target.owner == "Y"  # flipped by pawn part
    assert target.rank >= 1
    assert any(a.card_id == card.id for a in board.auras_at(1, 3))  # effect part


def test_archdragon_x_projection_applies_pawn_and_effect():
    board = BoardState.create_initial_board()
    hydrator = CardHydrator()
    archdragon = hydrator.get_card("020")

    # Archdragon at MID-1: its X hits MID-2 (1,1) per pattern.
    _apply_you_projection(board, 1, 0, archdragon)

    tile = board.tile_at(1, 1)
    assert tile.owner == "Y"
    assert tile.rank == 1  # pawn component applied
    assert board.auras_at(1, 1)  # effect component applied


def test_x_claims_neutral_tile():
    board = BoardState.create_initial_board()
    card = _make_x_test_card(card_id="CLAIM")
    # Aim at a neutral tile (MID-3 targets MID-4)
    _apply_you_projection(board, 1, 2, card)
    target = board.tile_at(1, 3)
    assert target.owner == "Y"
    assert target.rank >= 1


if __name__ == "__main__":
    test_apply_pawn_projections_for_security_officer()
    print("test_apply_pawn_projections_for_security_officer: PASS")
