from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _make_engine_and_board():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"

    cards_path = data_dir / "qb_DB_Complete_v2.json"
    effects_path = data_dir / "qb_effects_v1.1.json"

    hydrator = CardHydrator(cards_path)
    engine = EffectEngine(effects_path, hydrator)
    board = BoardState.create_initial_board()
    return hydrator, engine, board


def test_grenadier_on_play_applies_enemy_debuff():
    hydrator, engine, board = _make_engine_and_board()

    grenadier = hydrator.get_card("003")
    target = hydrator.get_card("001")  # base power 1

    target_tile = board.tile_at(1, 2)  # MID-3
    target_tile.owner = "E"
    target_tile.rank = 1
    target_tile.card_id = target.id

    board.place_card("MID", 1, grenadier, effect_engine=engine)

    effective = board.effective_power_at(1, 2, engine)
    assert effective == target.power - 4
    assert board.direct_effects[(1, 2)]


def test_archdragon_on_play_applies_enemy_debuff():
    hydrator, engine, board = _make_engine_and_board()

    archdragon = hydrator.get_card("020")
    target = hydrator.get_card("001")  # base power 1

    target_tile = board.tile_at(0, 1)  # TOP-2 (aligned with pattern X)
    target_tile.owner = "E"
    target_tile.rank = 1
    target_tile.card_id = target.id

    board.place_card("MID", 1, archdragon, effect_engine=engine)

    effective = board.effective_power_at(0, 1, engine)
    assert effective == target.power - 3
    assert board.direct_effects[(0, 1)]


def test_toxirat_on_play_applies_to_all_affected_tiles():
    hydrator, engine, board = _make_engine_and_board()

    toxirat = hydrator.get_card("006")
    target_a = hydrator.get_card("001")
    target_b = hydrator.get_card("001")

    bot1 = board.tile_at(2, 0)  # BOT-1 (P)
    bot1.card_id = target_a.id

    bot2 = board.tile_at(2, 1)  # BOT-2 (X)
    bot2.owner = "E"  # show scope ignores side for all_affected_tiles
    bot2.rank = 1
    bot2.card_id = target_b.id

    board.place_card("MID", 1, toxirat, effect_engine=engine)

    assert board.effective_power_at(2, 0, engine) == target_a.power - 3
    assert board.effective_power_at(2, 1, engine) == target_b.power - 3
    assert (2, 0) in board.direct_effects
    assert (2, 1) in board.direct_effects


if __name__ == "__main__":
    test_grenadier_on_play_applies_enemy_debuff()
    test_archdragon_on_play_applies_enemy_debuff()
    test_toxirat_on_play_applies_to_all_affected_tiles()
    print("on_play tests: PASS")
