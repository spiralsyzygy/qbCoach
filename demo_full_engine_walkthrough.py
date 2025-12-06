"""
demo_full_engine_walkthrough.py

Deterministic Phase C walkthrough:
- Seeded Deck/Hand/GameState wiring
- Opening draws + start-of-turn draw
- Play from hand (YOU), mirrored play (ENEMY)
- Projection/effects application and influence recompute
- Effective power overlays via EffectEngine
- Lane + match scoring via compute_match_score
"""

from __future__ import annotations

from pathlib import Path

from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.game_state import GameState
from qb_engine.legality import is_legal_placement
from qb_engine.scoring import compute_match_score

LANE_NAMES = ["TOP", "MID", "BOT"]


def header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def card_ids_for_demo(hydrator: CardHydrator) -> list[str]:
    # Grab a deterministic set of 10 IDs (skips _meta)
    return sorted(cid for cid in hydrator.index.keys() if cid != "_meta")[:10]


def describe_hand(label: str, hand) -> None:
    ids = hand.as_card_ids()
    print(f"{label} hand ({len(ids)} cards): {ids}")


def describe_deck(label: str, deck: Deck) -> None:
    print(f"{label} deck remaining: {deck.cards_remaining()}")


def describe_board(board, effect_engine) -> None:
    board.print_board_with_effects_and_power(effect_engine)


def describe_match_score(board, effect_engine) -> None:
    match_score = compute_match_score(board, effect_engine)
    for lane_score in match_score.lanes:
        lane_name = LANE_NAMES[lane_score.lane_index]
        print(
            f"{lane_name}: you={lane_score.power_you}, "
            f"enemy={lane_score.power_enemy}, "
            f"winner={lane_score.winner}, "
            f"lane_points={lane_score.lane_points}"
        )
    print(
        "\nMATCH TOTAL:"
        f"\n  YOU   = {match_score.total_you}"
        f"\n  ENEMY = {match_score.total_enemy}"
        f"\n  WINNER= {match_score.winner}"
        f"\n  MARGIN= {match_score.margin}"
    )


def find_first_play(board, side: str, hand):
    """
    Find the first playable (hand_index, lane, col) for the given side across the hand.
    Returns None if no play exists.
    """
    for h_idx, card in enumerate(hand.cards):
        for lane in range(3):
            for col in range(5):
                tile = board.tile_at(lane, col)
                if side == "Y":
                    if is_legal_placement(board, lane, col, card):
                        return h_idx, lane, col
                else:
                    if (
                        tile.card_id is None
                        and tile.owner == "E"
                        and tile.rank >= card.cost
                    ):
                        return h_idx, lane, col
    return None


def main() -> None:
    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"

    header("Phase C demo — deterministic engine walkthrough")
    print(f"Project root: {project_root}")

    hydrator = CardHydrator(str(data_dir / "qb_DB_Complete_v2.json"))
    effect_engine = EffectEngine(data_dir / "qb_effects_v1.json", hydrator)

    # Build seeded decks so the walkthrough is reproducible
    demo_ids = card_ids_for_demo(hydrator)
    player_deck = Deck(demo_ids, seed=123)
    enemy_deck = Deck(demo_ids, seed=456)

    # Initialize GameState (auto-draws 3-card opening hands)
    state = GameState(
        player_deck=player_deck,
        enemy_deck=enemy_deck,
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=999,
    )

    header("Step 1 — Opening hands and initial board")
    describe_hand("YOU", state.player_hand)
    describe_hand("ENEMY", state.enemy_hand)
    describe_deck("YOU", state.player_deck)
    describe_deck("ENEMY", state.enemy_deck)
    print("Initial board:")
    state.board.print_board()

    # ------------------------------------------------------------------ #
    # Turn 1: YOU
    # ------------------------------------------------------------------ #
    header("Step 2 — Start of YOUR turn: draw 1")
    state.draw_start_of_turn()
    describe_hand("YOU", state.player_hand)
    describe_deck("YOU", state.player_deck)

    header("Step 3 — YOU play first legal card from hand")
    you_play = find_first_play(state.board, "Y", state.player_hand)
    if you_play is None:
        print("No legal placement found for YOU; stopping demo.")
        return
    hand_idx_y, lane_y, col_y = you_play
    print(f"Placing YOU card hand[{hand_idx_y}] at {LANE_NAMES[lane_y]}-{col_y + 1}")
    state.play_card_from_hand("Y", hand_index=hand_idx_y, lane=lane_y, col=col_y)
    describe_board(state.board, effect_engine)

    # ------------------------------------------------------------------ #
    # Turn 2: ENEMY
    # ------------------------------------------------------------------ #
    header("Step 4 — End YOUR turn → switch to ENEMY")
    state.end_turn()
    print(f"Turn: {state.turn}, side_to_act: {state.side_to_act}")

    header("Step 5 — Start of ENEMY turn: draw 1")
    state.draw_start_of_turn()
    describe_hand("ENEMY", state.enemy_hand)
    describe_deck("ENEMY", state.enemy_deck)

    header("Step 6 — ENEMY plays first legal card (mirrored projection)")
    enemy_play = find_first_play(state.board, "E", state.enemy_hand)
    if enemy_play is None:
        print("No legal placement found for ENEMY; stopping demo before scoring.")
        return
    hand_idx_e, lane_e, col_e = enemy_play
    print(f"Placing ENEMY card hand[{hand_idx_e}] at {LANE_NAMES[lane_e]}-{col_e + 1}")
    state.play_card_from_hand("E", hand_index=hand_idx_e, lane=lane_e, col=col_e)
    describe_board(state.board, effect_engine)

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #
    header("Step 7 — Scoring summary (lane scores + match total)")
    describe_match_score(state.board, effect_engine)


if __name__ == "__main__":
    main()
