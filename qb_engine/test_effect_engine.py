from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"

    cards_path = data_dir / "qb_DB_Complete_v2.json"
    effects_path = data_dir / "qb_effects_v1.json"

    hydrator = CardHydrator(cards_path)
    engine = EffectEngine(effects_path, hydrator)

    # Fresh board
    board = BoardState.create_initial_board()

    # Put a Mindflayer (027) on MID-1 (lane_index=1, col=0)
    mindflayer = hydrator.get_card("027")
    print("Mindflayer effect_id:", mindflayer.effect_id)
    board.place_card("MID", 1, mindflayer)

    # Manually add its aura to MID-2 (lane_index=1, col=1)
    board.add_effect_aura(1, 1, "027", mindflayer.effect)

    # Put another card on MID-2
    target = hydrator.get_card("003")  # Grenadier (just a simple body for this test)
    board.place_card("MID", 2, target)

    effective = engine.compute_effective_power(board, 1, 1)
    base = target.power
    expected = base - 1  # Mindflayer gives -1 while_in_play

    print("Base:", base)
    print("Effective:", effective)
    print("Expected:", expected)

    assert effective == expected, f"Expected {expected}, got {effective}"
    print("test_effect_engine: PASS")


if __name__ == "__main__":
    main()
