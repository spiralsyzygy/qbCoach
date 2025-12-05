import sys
from pathlib import Path

# Allow running the file directly (python qb_engine/test_board_effective_power.py)
if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _make_engine_and_board():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"

    cards_path = data_dir / "qb_DB_Complete_v2.json"
    effects_path = data_dir / "qb_effects_v1.json"

    hydrator = CardHydrator(str(cards_path))
    engine = EffectEngine(effects_path, hydrator)
    board = BoardState.create_initial_board()
    return hydrator, engine, board


def test_effective_power_print_with_mindflayer_debuff(capsys):
    hydrator, engine, board = _make_engine_and_board()

    mindflayer = hydrator.get_card("027")
    board.place_card("MID", 1, mindflayer)
    board.add_effect_aura(1, 1, "027", mindflayer.effect or "")

    target = hydrator.get_card("003")  # base power 1
    board.place_card("MID", 2, target)

    if capsys is None:
        from io import StringIO
        from contextlib import redirect_stdout

        buffer = StringIO()
        with redirect_stdout(buffer):
            board.print_board_with_effects_and_power(engine)
        output = buffer.getvalue()
    else:
        board.print_board_with_effects_and_power(engine)
        output = capsys.readouterr().out

    lines = [line.strip() for line in output.splitlines() if line.strip()]

    mid_row = lines[1]  # order is TOP, MID, BOT
    assert "[003:0★]" in mid_row


if __name__ == "__main__":
    test_effective_power_print_with_mindflayer_debuff(capsys=None)  # type: ignore[arg-type]
    print("test_effective_power_print_with_mindflayer_debuff: PASS")
