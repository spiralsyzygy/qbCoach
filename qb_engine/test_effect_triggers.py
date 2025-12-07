import json
from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _write(tmp_path: Path, cards: list[dict], effects: dict) -> tuple[Path, Path]:
    db_path = tmp_path / "db.json"
    reg_path = tmp_path / "reg.json"
    db_path.write_text(json.dumps(cards), encoding="utf-8")
    reg_path.write_text(json.dumps(effects), encoding="utf-8")
    return db_path, reg_path


def _grid(center: str = "P", right: str | None = None) -> list[list[str]]:
    g = [["."] * 5 for _ in range(5)]
    g[2][2] = center
    if right:
        g[2][3] = right
    return g


def test_first_enhanced_and_enfeebled(tmp_path: Path):
    cards = [
        {"id": "FE", "name": "FirstEnhanced", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "first_enh"},
        {"id": "FF", "name": "FirstEnfeebled", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "first_enf"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "first_enh": {
            "description": "",
            "trigger": "on_first_enhanced",
            "scope": "self",
            "operations": [{"type": "modify_power", "stat": "power", "amount": 1}],
        },
        "first_enf": {
            "description": "",
            "trigger": "on_first_enfeebled",
            "scope": "self",
            "operations": [{"type": "modify_power", "stat": "power", "amount": 1}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # First enhanced fires once
    board.tile_at(1, 0).card_id = "FE"
    card = hydrator.get_card("FE")
    engine._apply_modify_power(board, 1, 0, card, 1)
    tile = board.tile_at(1, 0)
    assert tile.power_delta == 2  # +1 direct, +1 from first_enhanced trigger
    assert tile.trigger_state and tile.trigger_state.first_enhanced_fired
    engine._apply_modify_power(board, 1, 0, card, 1)
    assert tile.power_delta == 3  # trigger did not fire again

    # First enfeebled fires once on first drop below 0
    board.tile_at(1, 1).owner = "Y"
    board.tile_at(1, 1).card_id = "FF"
    card_ff = hydrator.get_card("FF")
    engine._apply_modify_power(board, 1, 1, card_ff, -1)
    tile_ff = board.tile_at(1, 1)
    assert tile_ff.power_delta == 0  # -1 then +1 from trigger
    assert tile_ff.trigger_state and tile_ff.trigger_state.first_enfeebled_fired
    engine._apply_modify_power(board, 1, 1, card_ff, -1)
    assert tile_ff.power_delta == -1  # trigger does not fire again


def test_on_enfeebled_fires_each_time(tmp_path: Path):
    cards = [
        {"id": "ENF", "name": "Enfeeble", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "on_enf"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "on_enf": {
            "description": "",
            "trigger": "on_enfeebled",
            "scope": "self",
            "operations": [{"type": "modify_power", "stat": "power", "amount": 1}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    board.tile_at(1, 0).card_id = "ENF"
    card = hydrator.get_card("ENF")
    engine._apply_modify_power(board, 1, 0, card, -1)
    engine._apply_modify_power(board, 1, 0, card, -1)
    tile = board.tile_at(1, 0)
    # Each -1 is followed by +1 from trigger => net 0
    assert tile.power_delta == 0


def test_on_destroy_then_on_card_destroyed_order(tmp_path: Path):
    # R has on_destroy that buffs ally in its E projection by +2
    # W watches destroyed_ally and gains +1 scale
    grid_r = _grid(right="E")
    cards = [
        {"id": "R", "name": "Rattle", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": grid_r, "effect_id": "death_rattle"},
        {"id": "W", "name": "Watcher", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "watch_destroy"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "death_rattle": {
            "description": "",
            "trigger": "on_destroy",
            "scope": "all_cards_on_affected_tiles",
            "operations": [{"type": "modify_power", "stat": "power", "amount": 2}],
        },
        "watch_destroy": {
            "description": "",
            "trigger": "on_card_destroyed",
            "scope": "self",
            "operations": [{"type": "modify_power_scale", "per": "destroyed_ally", "amount_per": 1}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Place R at MID-2, W at MID-3 (so R's E projection hits W)
    board.tile_at(1, 1).card_id = "R"
    board.tile_at(1, 2).card_id = "W"

    engine._destroy_cards(board, [(1, 1)])

    tile_w = board.tile_at(1, 2)
    # on_destroy applied +2, watcher scale +1
    assert tile_w.power_delta == 2
    assert tile_w.scale_delta == 1
    assert engine.compute_effective_power(board, 1, 2) == 4  # base1 +2 +1


def test_power_threshold(tmp_path: Path):
    cards = [
        {"id": "T", "name": "Threshold", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "threshold_eff"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "threshold_eff": {
            "description": "",
            "trigger": "on_power_threshold",
            "scope": "self",
            "operations": [
                {
                    "type": "modify_power",
                    "stat": "power",
                    "amount": 1,
                    "conditions": {"threshold": {"stat": "power", "value": 3}, "first_time": True},
                }
            ],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    board.tile_at(1, 0).card_id = "T"
    card = hydrator.get_card("T")
    engine._apply_modify_power(board, 1, 0, card, 2)  # base 1 -> 3 triggers threshold
    tile = board.tile_at(1, 0)
    assert tile.power_delta == 3  # +2 direct, +1 threshold
    # Additional boost does not retrigger (first_time)
    engine._apply_modify_power(board, 1, 0, card, 1)
    assert tile.power_delta == 4
