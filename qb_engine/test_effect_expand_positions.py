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


def _grid(center: str = "P") -> list[list[str]]:
    g = [["."] * 5 for _ in range(5)]
    g[2][2] = center
    return g


def test_expand_positions_adjacent(tmp_path: Path):
    cards = [
        {"id": "EXP", "name": "Expander", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid(), "effect_id": "expand_eff"},
    ]
    effects = {
        "_meta": {"version": "test"},
        "expand_eff": {
            "description": "",
            "trigger": "on_play",
            "scope": "self",
            "operations": [{"type": "expand_positions", "apply_to": "adjacent"}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Place expander at MID-3 (1,2)
    tile_src = board.tile_at(1, 2)
    tile_src.card_id = "EXP"
    tile_src.owner = "Y"
    tile_src.rank = 1

    # Surroundings: set some neutral, some owned, some enemy
    neighbors = [
        (0, 1), (0, 2), (0, 3),
        (1, 1),         (1, 3),
        (2, 1), (2, 2), (2, 3),
    ]
    for lane, col in neighbors:
        tile = board.tile_at(lane, col)
        tile.owner = "N"
        tile.rank = 0
        tile.card_id = None
    # Make (0,1) already Y2, (2,3) enemy E1
    board.tile_at(0, 1).owner = "Y"
    board.tile_at(0, 1).rank = 2
    board.tile_at(2, 3).owner = "E"
    board.tile_at(2, 3).rank = 1

    engine.apply_on_play_effects(board, 1, 2, hydrator.get_card("EXP"))

    # Neutral neighbors -> Y1
    for lane, col in neighbors:
        tile = board.tile_at(lane, col)
        if (lane, col) == (2, 3):  # enemy untouched
            assert tile.owner == "E" and tile.rank == 1
            continue
        if (lane, col) == (0, 1):
            # owned neighbor rank+1 clamped
            assert tile.owner == "Y" and tile.rank == 3
            continue
        assert tile.owner == "Y"
        assert tile.rank == 1

