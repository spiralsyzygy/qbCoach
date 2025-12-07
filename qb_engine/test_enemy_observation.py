import copy
from pathlib import Path

from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.enemy_observation import EnemyObservation
from qb_engine.game_state import GameState


def _make_state_with_enemy_card(card_id: str, turn: int = 1):
    # Minimal GameState with a specific enemy card on the board at MID-5
    hydrator = CardHydrator()
    effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    ids = [card_id] * 15
    state = GameState(
        player_deck=Deck(ids, seed=1),
        enemy_deck=Deck(ids, seed=2),
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=3,
    )
    state.turn = turn
    tile = state.board.tile_at(1, 4)  # MID-5
    tile.owner = "E"
    tile.card_id = card_id
    return state


def test_register_enemy_play_creates_observation():
    obs = EnemyObservation()
    obs.register_enemy_play("001", lane_index=0, col_index=4, turn=1, origin="deck")

    all_obs = obs.get_all_enemy_observations()
    assert len(all_obs) == 1
    oc = all_obs[0]
    assert oc.card_id == "001"
    assert oc.side == "E"
    assert oc.lane_index == 0
    assert oc.col_index == 4
    assert oc.origin == "deck"
    assert oc.turn_observed == 1


def test_update_from_game_state_tracks_board_presence():
    state = _make_state_with_enemy_card("002", turn=1)
    obs = EnemyObservation()

    obs.update_from_game_state(state)

    board_cards = obs.get_enemy_board_cards()
    assert len(board_cards) == 1
    oc = board_cards[0]
    assert oc.card_id == "002"
    assert oc.lane_index == 1
    assert oc.col_index == 4
    assert oc.destroyed_on_turn is None


def test_destroyed_cards_are_marked_with_turn():
    state1 = _make_state_with_enemy_card("003", turn=1)
    obs = EnemyObservation()
    obs.update_from_game_state(state1)

    state2 = copy.deepcopy(state1)
    state2.turn = 2
    tile = state2.board.tile_at(1, 4)
    tile.card_id = None  # removed

    obs.update_from_game_state(state2)

    destroyed = obs.get_enemy_destroyed_cards()
    assert len(destroyed) == 1
    oc = destroyed[0]
    assert oc.card_id == "003"
    assert oc.destroyed_on_turn == 2


def test_known_deck_remaining_ids_updates_as_enemy_plays():
    obs = EnemyObservation(known_enemy_deck_ids=["001", "002", "003"] * 5)

    obs.register_enemy_play("001", lane_index=0, col_index=0, turn=1, origin="deck")
    obs.register_enemy_play("002", lane_index=0, col_index=1, turn=1, origin="deck")

    remaining = obs.get_known_enemy_deck_remaining_ids()
    assert remaining.count("003") == 5
    assert "001" in obs.state.enemy_deck_knowledge.played_ids
    assert "002" in obs.state.enemy_deck_knowledge.played_ids


def test_multiset_behavior_for_duplicate_cards():
    obs = EnemyObservation(known_enemy_deck_ids=["001", "001", "002"] + ["003"] * 12)

    obs.register_enemy_play("001", lane_index=0, col_index=0, turn=1, origin="deck")
    remaining = sorted(obs.get_known_enemy_deck_remaining_ids())
    assert remaining.count("001") == 1
    assert "002" in remaining

    obs.register_enemy_play("001", lane_index=0, col_index=1, turn=2, origin="deck")
    remaining = obs.get_known_enemy_deck_remaining_ids()
    assert remaining.count("001") == 0
    assert "002" in remaining


def test_tokens_are_classified_by_origin():
    obs = EnemyObservation()
    obs.register_enemy_play("token_01", lane_index=0, col_index=0, turn=1, origin="token")

    tokens = obs.get_enemy_tokens()
    assert len(tokens) == 1
    assert tokens[0].origin == "token"


def test_observation_is_deterministic_for_given_state_sequence():
    state1 = _make_state_with_enemy_card("004", turn=1)
    state2 = copy.deepcopy(state1)
    state2.turn = 2
    state2.board.tile_at(1, 4).card_id = None

    obs_a = EnemyObservation()
    obs_b = EnemyObservation()

    for obs in (obs_a, obs_b):
        obs.update_from_game_state(state1)
        obs.update_from_game_state(state2)

    assert obs_a.get_all_enemy_observations() == obs_b.get_all_enemy_observations()
