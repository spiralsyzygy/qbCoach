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


def test_scope_resolution_global_and_lane(tmp_path: Path):
    cards = [
        {"id": "YA", "name": "YouA", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
        {"id": "YB", "name": "YouB", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
        {"id": "EA", "name": "EnemyA", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
        {"id": "EB", "name": "EnemyB", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
    ]
    effects = {"_meta": {"version": "test"}}
    db_path, reg_path = _write(tmp_path, cards, effects)

    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Allies on TOP-1 and MID-1
    board.tile_at(0, 0).card_id = "YA"
    board.tile_at(1, 0).card_id = "YB"

    # Enemies on TOP-5, MID-5, and MID-4 (set owner on neutral tile)
    board.tile_at(0, 4).card_id = "EA"
    board.tile_at(1, 4).card_id = "EB"
    mid_four = board.tile_at(1, 3)
    mid_four.owner = "E"
    mid_four.rank = 1
    mid_four.card_id = "EA"

    acting_side = "Y"
    source_pos = (1, 0)

    allies_global = engine.resolve_scope("allies_global", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in allies_global} == {(0, 0), (1, 0)}

    enemies_global = engine.resolve_scope("enemies_global", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in enemies_global} == {(0, 4), (1, 3), (1, 4)}

    all_cards_global = engine.resolve_scope("all_cards_global", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in all_cards_global} == {(0, 0), (1, 0), (0, 4), (1, 3), (1, 4)}

    allies_in_lane = engine.resolve_scope("allies_in_lane", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in allies_in_lane} == {(1, 0)}

    enemies_in_lane = engine.resolve_scope("enemies_in_lane", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in enemies_in_lane} == {(1, 3), (1, 4)}

    all_cards_in_lane = engine.resolve_scope("all_cards_in_lane", acting_side, source_pos, board)
    assert {(l, c) for (l, c, _) in all_cards_in_lane} == {(1, 0), (1, 3), (1, 4)}
