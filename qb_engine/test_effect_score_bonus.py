import json
from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine
from qb_engine.scoring import compute_match_score


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


def test_lane_win_bonus_stacks(tmp_path: Path):
    cards = [
        {"id": "BON1", "name": "Bonus1", "category": "Test", "cost": 0, "power": 2, "pattern": "", "grid": _grid(), "effect_id": "lane_bonus"},
        {"id": "BON2", "name": "Bonus2", "category": "Test", "cost": 0, "power": 2, "pattern": "", "grid": _grid(), "effect_id": "lane_bonus"},
        {"id": "ALLY", "name": "Ally", "category": "Test", "cost": 0, "power": 2, "pattern": "", "grid": _grid()},
        {"id": "LOS", "name": "Loser", "category": "Test", "cost": 0, "power": 1, "pattern": "", "grid": _grid()},
    ]
    effects = {
        "_meta": {"version": "test"},
        "lane_bonus": {
            "description": "",
            "trigger": "on_lane_win",
            "scope": "lane_owner",
            "operations": [{"type": "score_bonus", "amount": 3}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # Place winning side cards in MID lane (lane 1)
    board.tile_at(1, 0).card_id = "BON1"  # Y owned
    mid_one = board.tile_at(1, 1)
    mid_one.owner = "Y"
    mid_one.rank = 1
    mid_one.card_id = "BON2"

    # Enemy card on MID-5
    board.tile_at(1, 4).card_id = "LOS"

    match_score = compute_match_score(board, engine)
    lane = match_score.lanes[1]
    # Base power_you = 4, enemy = 1, winner Y. Bonuses +6 from two cards.
    assert lane.lane_points == 10
    assert match_score.total_you == 10
    assert match_score.total_enemy == 0
    assert match_score.winner == "Y"


def test_lane_min_transfer_stacks(tmp_path: Path):
    cards = [
        {"id": "WIN1", "name": "Winner1", "category": "Test", "cost": 0, "power": 4, "pattern": "", "grid": _grid(), "effect_id": "lane_transfer"},
        {"id": "WIN2", "name": "Winner2", "category": "Test", "cost": 0, "power": 4, "pattern": "", "grid": _grid(), "effect_id": "lane_transfer"},
        {"id": "YOU5", "name": "YouFive", "category": "Test", "cost": 0, "power": 5, "pattern": "", "grid": _grid()},
    ]
    effects = {
        "_meta": {"version": "test"},
        "lane_transfer": {
            "description": "",
            "trigger": "on_round_end",
            "scope": "lane_owner",
            "operations": [{"type": "score_bonus", "mode": "lane_min_transfer"}],
        },
    }
    db_path, reg_path = _write(tmp_path, cards, effects)
    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)
    board = BoardState.create_initial_board()

    # You have 5 power on MID-1
    board.tile_at(1, 0).card_id = "YOU5"

    # Enemy cards with lane_min_transfer on MID-5 and MID-4
    board.tile_at(1, 4).card_id = "WIN1"  # owner E already
    mid_four = board.tile_at(1, 3)
    mid_four.owner = "E"
    mid_four.rank = 1
    mid_four.card_id = "WIN2"

    match_score = compute_match_score(board, engine)
    lane = match_score.lanes[1]
    assert lane.winner == "E"
    # Base enemy power = 8, you = 5, lower = 5; two cards stack => +10
    assert lane.lane_points == 18
    assert match_score.total_enemy == 18
    assert match_score.total_you == 0
