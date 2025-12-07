import json
from pathlib import Path

import pytest

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _write_test_files(tmp_path: Path, cards: list[dict], effects: dict) -> tuple[Path, Path]:
    db_path = tmp_path / "db.json"
    reg_path = tmp_path / "reg.json"
    db_path.write_text(json.dumps(cards), encoding="utf-8")
    reg_path.write_text(json.dumps(effects), encoding="utf-8")
    return db_path, reg_path


def _grid_with(center: str = "P", right: str | None = None) -> list[list[str]]:
    grid = [["."] * 5 for _ in range(5)]
    grid[2][2] = center
    if right:
        grid[2][3] = right
    return grid


def test_event_based_scaling_on_destroy(tmp_path: Path):
    # Card S scales when enemies are destroyed.
    cards = [
        {"id": "S", "name": "Scaler", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid_with(), "effect_id": "scale_destroy"},
        {"id": "V", "name": "Victim", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid_with()},
    ]
    effects = {
        "_meta": {"version": "test"},
        "scale_destroy": {
            "description": "",
            "trigger": "on_card_destroyed",
            "scope": "self",
            "operations": [
                {"type": "modify_power_scale", "per": "destroyed_enemy", "amount_per": 1}
            ],
        },
    }
    db_path, reg_path = _write_test_files(tmp_path, cards, effects)

    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Place scaler (you) at MID-1, victim (enemy) at MID-5
    board.tile_at(1, 0).card_id = "S"
    board.tile_at(1, 4).owner = "E"
    board.tile_at(1, 4).card_id = "V"

    engine._destroy_cards(board, [(1, 4)])

    tile = board.tile_at(1, 0)
    assert tile.scale_delta == 1
    assert engine.compute_effective_power(board, 1, 0) == 2  # base 1 + scale 1


def test_snapshot_scaling_while_in_play(tmp_path: Path):
    cards = [
        {"id": "W", "name": "Watcher", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid_with(), "effect_id": "scale_wip"},
        {"id": "E", "name": "Enemy", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid_with()},
    ]
    effects = {
        "_meta": {"version": "test"},
        "scale_wip": {
            "description": "",
            "trigger": "while_in_play",
            "scope": "self",
            "operations": [
                {"type": "modify_power_scale", "per": "enfeebled_enemy", "amount_per": 2}
            ],
        },
    }
    db_path, reg_path = _write_test_files(tmp_path, cards, effects)

    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    board.tile_at(1, 0).card_id = "W"
    enemy_tile = board.tile_at(1, 4)
    enemy_tile.owner = "E"
    enemy_tile.card_id = "E"
    enemy_tile.power_delta = -1  # enfeebled

    assert engine.compute_effective_power(board, 1, 0) == 3  # base 1 + 2 (one enfeebled enemy)

