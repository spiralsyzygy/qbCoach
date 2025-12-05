from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _make_engine_and_board():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"

    cards_path = data_dir / "qb_DB_Complete_v2.json"
    effects_path = data_dir / "qb_effects_v1.json"

    hydrator = CardHydrator(cards_path)
    engine = EffectEngine(effects_path, hydrator)
    board = BoardState.create_initial_board()
    return hydrator, engine, board


def test_mindflayer_while_in_play_debuff():
    """
    Mindflayer (027) should apply a -1 power debuff to cards on its affected tiles
    while it is in play.
    """
    hydrator, engine, board = _make_engine_and_board()

    mindflayer = hydrator.get_card("027")
    board.place_card("MID", 1, mindflayer)
    board.add_effect_aura(1, 1, "027", mindflayer.effect)

    target = hydrator.get_card("003")
    board.place_card("MID", 2, target)

    effective = engine.compute_effective_power(board, 1, 1)
    base = target.power
    expected = base - 1

    assert effective == expected, f"Expected {expected}, got {effective}"


if __name__ == "__main__":
    # still let you run it directly if you want
    test_mindflayer_while_in_play_debuff()
    ("test_mindflayer_while_in_play_debuff: PASS")
