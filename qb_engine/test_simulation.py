from pathlib import Path

import pytest

from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.game_state import GameState
from qb_engine.hand import Hand


def _make_hydrator():
    root = Path(__file__).resolve().parents[1]
    return CardHydrator(str(root / "data" / "qb_DB_Complete_v2.json"))


def _make_effect_engine(hydrator):
    root = Path(__file__).resolve().parents[1]
    return EffectEngine(root / "data" / "qb_effects_v1.json", hydrator)


def _first_card_ids(hydrator, n=10):
    ids = sorted(cid for cid in hydrator.index.keys() if cid != "_meta")
    return ids[:n]


# ---------------------- Deck Tests ---------------------- #


def test_seeded_shuffle_determinism():
    hydrator = _make_hydrator()
    ids = _first_card_ids(hydrator)
    deck_a = Deck(ids, seed=123)
    deck_b = Deck(ids, seed=123)

    assert deck_a.draw_n(10) == deck_b.draw_n(10)


def test_draw_order_and_exhaustion():
    hydrator = _make_hydrator()
    ids = _first_card_ids(hydrator)
    deck = Deck(ids, seed=99)

    first_three = deck.draw_n(3)
    assert len(first_three) == 3
    assert deck.cards_remaining() == 7

    deck.draw_n(7)
    with pytest.raises(RuntimeError):
        deck.draw()


def test_mulligan_replaces_and_preserves_kept_slots():
    hydrator = _make_hydrator()
    ids = _first_card_ids(hydrator)
    deck = Deck(ids, seed=7)

    opening = deck.draw_n(3)
    new_hand = deck.mulligan(opening, [1])

    assert len(new_hand) == 3
    assert new_hand[0] == opening[0]
    assert new_hand[2] == opening[2]
    assert deck.cards_remaining() == 7


# ---------------------- Hand Tests ---------------------- #


def test_hand_add_remove_and_sync():
    hydrator = _make_hydrator()
    hand = Hand(hydrator)

    hand.from_card_ids(["001", "002"])
    assert hand.as_card_ids() == ["001", "002"]

    removed = hand.remove_index(0)
    assert removed.id == "001"
    assert hand.as_card_ids() == ["002"]

    hand.add_card("003")
    assert hand.as_card_ids() == ["002", "003"]

    hand.sync_from_ids(["001"])
    assert hand.as_card_ids() == ["001"]

    with pytest.raises(IndexError):
        hand.remove_index(5)


# ---------------------- GameState Tests ---------------------- #


def _make_state(player_ids=None, enemy_ids=None, seed=5):
    hydrator = _make_hydrator()
    effect_engine = _make_effect_engine(hydrator)
    base_ids = _first_card_ids(hydrator)

    p_ids = player_ids or base_ids
    e_ids = enemy_ids or base_ids

    player_deck = Deck(p_ids, seed=seed)
    enemy_deck = Deck(e_ids, seed=seed + 1)

    return GameState(player_deck, enemy_deck, hydrator, effect_engine, seed=seed)


def test_draw_start_of_turn_increases_hand_and_consumes_deck():
    state = _make_state()

    assert len(state.player_hand.cards) == 3
    before = state.player_deck.cards_remaining()

    state.draw_start_of_turn()

    assert len(state.player_hand.cards) == 4
    assert state.player_deck.cards_remaining() == before - 1


def test_play_card_from_hand_for_you_and_enemy():
    hydrator = _make_hydrator()
    effect_engine = _make_effect_engine(hydrator)
    ids = ["001"] * 10

    state = GameState(
        player_deck=Deck(ids, seed=11),
        enemy_deck=Deck(ids, seed=12),
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=99,
    )

    initial_hand = len(state.player_hand.cards)
    state.play_card_from_hand("Y", 0, 0, 0)
    assert len(state.player_hand.cards) == initial_hand - 1
    assert state.board.tile_at(0, 0).card_id == "001"

    state.end_turn()
    state.draw_start_of_turn()
    enemy_initial_hand = len(state.enemy_hand.cards)
    state.play_card_from_hand("E", 0, 1, 4)
    assert len(state.enemy_hand.cards) == enemy_initial_hand - 1
    assert state.board.tile_at(1, 4).card_id == "001"


def test_clone_is_isolated_and_preserves_rng_state():
    state = _make_state()
    clone = state.clone()

    drawn_state = state.player_deck.draw()
    drawn_clone = clone.player_deck.draw()

    assert drawn_state == drawn_clone

    state.board.tile_at(0, 0).owner = "N"
    assert clone.board.tile_at(0, 0).owner == "Y"


def test_multi_turn_flow():
    hydrator = _make_hydrator()
    effect_engine = _make_effect_engine(hydrator)
    ids = ["001"] * 10

    state = GameState(
        player_deck=Deck(ids, seed=21),
        enemy_deck=Deck(ids, seed=22),
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=21,
    )

    state.draw_start_of_turn()
    state.play_card_from_hand("Y", 0, 0, 0)
    state.end_turn()

    assert state.side_to_act == "E"
    assert state.turn == 2

    state.draw_start_of_turn()
    state.play_card_from_hand("E", 0, 1, 4)
    state.end_turn()

    assert state.turn == 3
    assert state.board.tile_at(0, 0).card_id == "001"
    assert state.board.tile_at(1, 4).card_id == "001"

