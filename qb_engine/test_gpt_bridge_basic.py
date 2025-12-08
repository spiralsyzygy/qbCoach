import json
from pathlib import Path
import copy

import pytest

from qb_engine.card_hydrator import CardHydrator
from qb_engine.gpt_bridge import EngineBridge


def _first_n_card_ids(n: int) -> list[str]:
    hydrator = CardHydrator()
    return sorted(hydrator.index.keys())[:n]


@pytest.fixture
def bridge():
    db = json.load(Path("data/qb_DB_Complete_v2.json").open())
    return EngineBridge(card_db=db)


def test_init_match_creates_session_and_snapshot(bridge):
    deck_ids = _first_n_card_ids(15)
    resp = bridge.handle_request(
        {
            "session_id": "s1",
            "op": "init_match",
            "payload": {
                "you_deck_ids": deck_ids,
                "enemy_deck_ids": deck_ids,
                "seed": 123,
            },
        }
    )
    assert resp["ok"] is True
    state = resp["state"]
    assert state["you_deck_size"] + len(state["you_hand"]["cards"]) == 15
    assert state["enemy_deck_size"] + state["enemy_hand_size"] == 15
    assert state["side_to_act"] == "Y"
    assert state["turn_number"] == 1


def test_get_state_returns_consistent_snapshot(bridge):
    deck_ids = _first_n_card_ids(15)
    bridge.handle_request(
        {
            "session_id": "s2",
            "op": "init_match",
            "payload": {
                "you_deck_ids": deck_ids,
                "enemy_deck_ids": deck_ids,
            },
        }
    )
    resp = bridge.handle_request({"session_id": "s2", "op": "get_state"})
    assert resp["ok"] is True
    state = resp["state"]
    assert state["turn_number"] == 1
    assert state["you_deck_size"] == 10
    assert state["enemy_deck_size"] == 10
    assert len(state["you_hand"]["cards"]) == 5
    assert state["enemy_hand_size"] == 5


def test_invalid_session_for_get_state(bridge):
    resp = bridge.handle_request({"session_id": "missing", "op": "get_state"})
    assert resp["ok"] is False
    assert resp["error"]["type"] == "InvalidSession"


def test_bad_request_missing_decks(bridge):
    resp = bridge.handle_request({"session_id": "s3", "op": "init_match", "payload": {"you_deck_ids": []}})
    assert resp["ok"] is False
    assert resp["error"]["type"] == "BadRequest"


def _init_simple_session(bridge, session_id="s_move"):
    deck_ids = _first_n_card_ids(15)
    return bridge.handle_request(
        {
            "session_id": session_id,
            "op": "init_match",
            "payload": {"you_deck_ids": deck_ids, "enemy_deck_ids": deck_ids},
        }
    )


def _find_legal_tile(state, card):
    board = state.board
    for lane_idx, row in enumerate(board.tiles):
        for col_idx, tile in enumerate(row):
            if tile.owner == "Y" and tile.card_id is None and tile.rank >= card.cost:
                return lane_idx, col_idx
    raise RuntimeError("No legal tile found for test card.")


def _find_playable_card_and_tile(state):
    for idx, card in enumerate(state.player_hand.cards):
        try:
            lane, col = _find_legal_tile(state, card)
            return idx, card, lane, col
        except RuntimeError:
            continue
    raise RuntimeError("No playable card/tile found for YOU.")


def test_apply_you_move_legal_updates_state(bridge):
    _init_simple_session(bridge, "s4")
    session = bridge._sessions["s4"]
    hand_idx, card, lane, col = _find_playable_card_and_tile(session.game_state)
    resp = bridge.handle_request(
        {
            "session_id": "s4",
            "op": "apply_you_move",
            "payload": {
                "move": {
                    "card_id": card.id,
                    "hand_index": hand_idx,
                    "lane_index": lane,
                    "col_index": col,
                }
            },
        }
    )
    assert resp["ok"] is True
    # Hand reduced by one
    assert len(session.game_state.player_hand.cards) == 4
    # Board now occupied
    assert session.game_state.board.tile_at(lane, col).card_id == card.id
    # Observation updated
    assert session.enemy_obs.state.last_updated_turn >= session.game_state.turn


def test_apply_you_move_illegal_does_not_mutate_state(bridge):
    _init_simple_session(bridge, "s5")
    session = bridge._sessions["s5"]
    hand_idx, card, _, _ = _find_playable_card_and_tile(session.game_state)
    # Choose enemy-owned tile (0,4) initially
    lane, col = 0, 4
    state_before = session.game_state.clone()
    obs_before = copy.deepcopy(session.enemy_obs.state)
    resp = bridge.handle_request(
        {
            "session_id": "s5",
            "op": "apply_you_move",
            "payload": {
                "move": {
                    "card_id": card.id,
                    "hand_index": hand_idx,
                    "lane_index": lane,
                    "col_index": col,
                }
            },
        }
    )
    assert resp["ok"] is False
    assert resp["error"]["type"] == "IllegalMove"
    # Ensure state unchanged
    assert len(session.game_state.player_hand.cards) == len(state_before.player_hand.cards)
    assert session.game_state.player_deck.cards_remaining() == state_before.player_deck.cards_remaining()
    assert session.game_state.board.tile_at(lane, col).card_id == state_before.board.tile_at(lane, col).card_id
    assert session.enemy_obs.state.last_updated_turn == obs_before.last_updated_turn


def test_apply_you_move_bad_request_on_card_mismatch(bridge):
    _init_simple_session(bridge, "s6")
    session = bridge._sessions["s6"]
    hand_idx, card, lane, col = _find_playable_card_and_tile(session.game_state)
    resp = bridge.handle_request(
        {
            "session_id": "s6",
            "op": "apply_you_move",
            "payload": {
                "move": {
                    "card_id": "999",  # mismatch
                    "hand_index": hand_idx,
                    "lane_index": lane,
                    "col_index": col,
                }
            },
        }
    )
    assert resp["ok"] is False
    assert resp["error"]["type"] == "BadRequest"


def test_recommend_moves_returns_moves_and_does_not_mutate_state(bridge):
    _init_simple_session(bridge, "s7")
    session = bridge._sessions["s7"]
    state_before = session.game_state.clone()
    obs_before = copy.deepcopy(session.enemy_obs.state)

    resp = bridge.handle_request(
        {"session_id": "s7", "op": "recommend_moves", "payload": {"top_n": 3}}
    )
    assert resp["ok"] is True
    coaching = resp["coaching"]
    assert coaching is not None
    if coaching["moves"]:
        assert coaching["moves"][0]["quality_rank"] == 1
    # Ensure no mutation
    assert session.game_state.player_deck.cards_remaining() == state_before.player_deck.cards_remaining()
    assert session.game_state.enemy_deck.cards_remaining() == state_before.enemy_deck.cards_remaining()
    assert len(session.game_state.player_hand.cards) == len(state_before.player_hand.cards)
    assert session.enemy_obs.state.last_updated_turn == obs_before.last_updated_turn


def test_get_prediction_returns_threat_map_and_does_not_mutate_state(bridge):
    _init_simple_session(bridge, "s8")
    session = bridge._sessions["s8"]
    state_before = session.game_state.clone()
    obs_before = copy.deepcopy(session.enemy_obs.state)

    resp = bridge.handle_request(
        {"session_id": "s8", "op": "get_prediction", "payload": {"mode": "full"}}
    )
    assert resp["ok"] is True
    threat = resp["threat_map"]
    assert threat is not None
    assert "0" in threat["lane_pressure"]
    # Ensure no mutation
    assert session.game_state.player_deck.cards_remaining() == state_before.player_deck.cards_remaining()
    assert session.game_state.enemy_deck.cards_remaining() == state_before.enemy_deck.cards_remaining()
    assert len(session.game_state.player_hand.cards) == len(state_before.player_hand.cards)
    assert session.enemy_obs.state.last_updated_turn == obs_before.last_updated_turn


def test_recommend_moves_bad_request_on_missing_top_n(bridge):
    _init_simple_session(bridge, "s9")
    resp = bridge.handle_request({"session_id": "s9", "op": "recommend_moves", "payload": {}})
    assert resp["ok"] is False
    assert resp["error"]["type"] == "BadRequest"


def test_get_prediction_bad_request_on_unknown_mode(bridge):
    _init_simple_session(bridge, "s10")
    resp = bridge.handle_request({"session_id": "s10", "op": "get_prediction", "payload": {"mode": "foo"}})
    assert resp["ok"] is False
    assert resp["error"]["type"] == "BadRequest"


# --- Register enemy play (live coaching) ---


def test_register_enemy_play_requires_live_coaching_mode(bridge):
    _init_simple_session(bridge, "s11")
    resp = bridge.handle_request(
        {"session_id": "s11", "op": "register_enemy_play", "payload": {"card_id": "001", "lane_index": 0, "col_index": 4}}
    )
    assert resp["ok"] is False
    assert resp["error"]["type"] == "BadRequest"


def test_register_enemy_play_updates_board_and_observation(bridge):
    deck_ids = _first_n_card_ids(15)
    bridge.handle_request(
        {
            "session_id": "s12",
            "op": "init_match",
            "payload": {"you_deck_ids": deck_ids, "enemy_deck_ids": deck_ids, "session_mode": "live_coaching"},
        }
    )
    session = bridge._sessions["s12"]
    state_before = session.game_state.clone()
    resp = bridge.handle_request(
        {
            "session_id": "s12",
            "op": "register_enemy_play",
            "payload": {"card_id": "001", "lane_index": 0, "col_index": 4},
        }
    )
    assert resp["ok"] is True
    tile = session.game_state.board.tile_at(0, 4)
    assert tile.card_id == "001"
    assert tile.owner == "E"
    obs = resp["enemy_observation"]
    assert obs["last_updated_turn"] == session.game_state.turn


def test_register_enemy_play_illegal_does_not_mutate_state(bridge):
    deck_ids = _first_n_card_ids(15)
    bridge.handle_request(
        {
            "session_id": "s13",
            "op": "init_match",
            "payload": {"you_deck_ids": deck_ids, "enemy_deck_ids": deck_ids, "session_mode": "live_coaching"},
        }
    )
    session = bridge._sessions["s13"]
    state_before = session.game_state.clone()
    obs_before = copy.deepcopy(session.enemy_obs.state)
    # Illegal: attempt to play on YOUR tile
    resp = bridge.handle_request(
        {
            "session_id": "s13",
            "op": "register_enemy_play",
            "payload": {"card_id": "001", "lane_index": 0, "col_index": 0},
        }
    )
    assert resp["ok"] is False
    # Ensure unchanged
    assert session.game_state.board.tile_at(0, 0).card_id == state_before.board.tile_at(0, 0).card_id
    assert session.enemy_obs.state.last_updated_turn == obs_before.last_updated_turn
