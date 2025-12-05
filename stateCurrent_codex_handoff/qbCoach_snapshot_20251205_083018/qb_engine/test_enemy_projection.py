from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.projection import (
    apply_effects_for_enemy,
    apply_pawns_for_enemy,
    compute_projection_targets,
    compute_projection_targets_for_enemy,
)


def _make_board_and_hydrator():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    hydrator = CardHydrator(data_dir / "qb_DB_Complete_v2.json")
    return BoardState.create_initial_board(), hydrator


def test_enemy_projection_symmetry():
    board, hydrator = _make_board_and_hydrator()
    card = hydrator.get_card("001")  # Security Officer, simple P-only grid

    you_proj = compute_projection_targets(root_lane_index=1, root_col_index=0, card=card)
    enemy_proj = compute_projection_targets_for_enemy(root_lane_index=1, root_col_index=4, card=card)

    mirrored = {(lane, 4 - col, kind) for lane, col, kind in you_proj.targets}
    enemy_set = set(enemy_proj.targets)

    assert mirrored == enemy_set


def test_enemy_pawns_influence_tiles():
    board, hydrator = _make_board_and_hydrator()
    card = hydrator.get_card("001")  # has P tiles

    proj = compute_projection_targets_for_enemy(root_lane_index=1, root_col_index=4, card=card)
    apply_pawns_for_enemy(board, proj, card)

    # Expect at least one neutral tile to become enemy owned (e.g., BOT-5 mirror).
    changed_tiles = []
    for lane_index, row in enumerate(board.tiles):
        for col_index, tile in enumerate(row):
            if tile.owner == "E" and tile.base_influence == 0:
                changed_tiles.append((lane_index, col_index, tile.rank))

    assert changed_tiles, "No tiles changed to enemy ownership"
    assert any(delta.delta < 0 for delta in board.pawn_deltas)


def test_enemy_effect_auras_marked():
    board, hydrator = _make_board_and_hydrator()
    card = hydrator.get_card("006")  # Toxirat has X projection and an effect string

    proj = compute_projection_targets_for_enemy(root_lane_index=1, root_col_index=4, card=card)
    apply_effects_for_enemy(board, proj, card)

    aura_tiles = [(lane, col) for lane in range(3) for col in range(5) if board.auras_at(lane, col)]
    assert aura_tiles, "Expected at least one aura from enemy placement"

    # Ensure the aura tiles correspond to the projection targets of kind E/X
    expected = {(lane, col) for lane, col, kind in proj.targets if kind in ("E", "X")}
    assert set(aura_tiles) == expected


if __name__ == "__main__":
    test_enemy_projection_symmetry()
    test_enemy_pawns_influence_tiles()
    test_enemy_effect_auras_marked()
    print("enemy projection tests: PASS")
