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


def test_spawn_token_on_spawned(tmp_path: Path):
    cards = [
        {"id": "SRC", "name": "Spawner", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "spawn_eff"},
        {"id": "TOK", "name": "Token", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "spawned_gain"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "spawn_eff": {
            "description": "",
            "trigger": "on_play",
            "scope": "self",
            "operations": [
                {"type": "spawn_token", "token_id": "TOK", "apply_to": "empty_positions", "per_pawns": True}
            ],
        },
        "spawned_gain": {
            "description": "",
            "trigger": "on_spawned",
            "scope": "self",
            "operations": [
                {"type": "modify_power", "stat": "power", "amount": 2, "conditions": {"replaced_pawns": 2}},
                {"type": "modify_power", "stat": "power", "amount": 3, "conditions": {"replaced_pawns": 3}},
            ],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Make three owned empty tiles with ranks 1,2,3
    ranks = [1, 2, 3]
    cols = [0, 1, 2]
    for rank, col in zip(ranks, cols):
        tile = board.tile_at(1, col)
        tile.owner = "Y"
        tile.rank = rank
        tile.card_id = None

    # Place spawner at MID-5 so it doesn't occupy the target tiles
    src_tile = board.tile_at(1, 4)
    src_tile.owner = "Y"
    src_tile.rank = 1
    src_tile.card_id = "SRC"
    engine.apply_on_play_effects(board, 1, 4, hydrator.get_card("SRC"))

    for rank, col in zip(ranks, cols):
        tile = board.tile_at(1, col)
        assert tile.card_id == "TOK"
        assert tile.origin == "token"
        assert tile.spawned_by == "SRC"
        assert tile.spawn_context and tile.spawn_context.replaced_pawns == rank
        # on_spawned should set power_delta based on replaced_pawns
        expected = 1  # base
        if rank == 2:
            expected += 2
        elif rank == 3:
            expected += 3
        assert engine.compute_effective_power(board, 1, col) == expected


def test_replace_ally(tmp_path: Path):
    grid_repl = _grid(center="P", right="E")
    cards = [
            {"id": "ALLY", "name": "Ally", "category": "Test", "cost": 0, "power": 2, "pattern": "", "grid": _grid()},
            {
                "id": "REPL",
                "name": "Replacer",
                "category": "Test",
                "cost": 0,
                "power": 1,
                "pattern": "B3E",
                "grid": grid_repl,
                "effect_id": "replace_eff",
            },
            {"id": "TARGET", "name": "Target", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
    ]
    effects = {
        "_meta": {"version": "test"},
        "replace_eff": {
            "description": "",
            "trigger": "on_play",
            "scope": "all_cards_on_affected_tiles",
            "operations": [
                {"type": "replace_ally", "mode": "raise", "adjustment": "replaced_ally_power"},
                {"type": "modify_power", "stat": "power", "amount": -1},  # ensure scope application occurs
            ],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Place ally at MID-3, buff it by +1 (power_delta=1) so effective=3
    board.tile_at(1, 2).card_id = "ALLY"
    ally = hydrator.get_card("ALLY")
    engine._apply_modify_power(board, 1, 2, ally, 1)

    # Place target at MID-4 (right of replacer projection E)
    board.tile_at(1, 3).card_id = "TARGET"
    board.tile_at(1, 3).owner = "Y"
    board.tile_at(1, 3).rank = 1

    # Compute replaced ally power then destroy ally (simulate replace)
    replaced_power = engine.compute_effective_power(board, 1, 2)
    engine._destroy_cards(board, [(1, 2)])

    # Place replacer on the tile and apply its on_play with replaced power
    repl_tile = board.tile_at(1, 2)
    repl_tile.owner = "Y"
    repl_tile.rank = 1
    repl_tile.card_id = "REPL"
    engine.apply_on_play_effects(board, 1, 2, hydrator.get_card("REPL"), replaced_ally_power=replaced_power)

    # Replace effect should have raised target by replaced_ally_power (3) and then -1 modify in scope => net +2
    assert engine.compute_effective_power(board, 1, 3) == 3  # base1 +2
