import pytest

from qb_engine.live_session import LiveSessionEngineBridge


def test_draw_appends_and_phase_gate():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    # Simulate enemy turn end -> awaiting draw
    bridge.phase = "YOU_TURN_AWAITING_DRAW"
    bridge.side_to_act = "Y"
    original_hand = bridge._game_state.player_hand.as_card_ids()  # type: ignore[attr-defined]
    bridge.apply_draw(original_hand[0])
    new_hand = bridge._game_state.player_hand.as_card_ids()  # type: ignore[attr-defined]
    assert len(new_hand) == len(original_hand) + 1
    assert bridge.phase == "YOU_TURN_READY_FOR_REC_OR_PLAY"


def test_set_hand_replaces():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    bridge.sync_you_hand_from_ids(["005", "007", "019"])
    assert bridge._game_state.player_hand.as_card_ids() == ["005", "007", "019"]  # type: ignore[attr-defined]


def test_turn_flow_gates_enemy_and_play():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    # Initially should be ready for you
    assert bridge.phase == "YOU_TURN_READY_FOR_REC_OR_PLAY"
    # Choose a legal move
    legal = bridge.legal_moves()[0]
    bridge.apply_you_move(legal["card_id"], legal["lane_index"], legal["col_index"])
    assert bridge.phase == "ENEMY_TURN_AWAITING_PLAY"
    # Enemy play not allowed during enemy phase for you-side moves
    with pytest.raises(ValueError):
        bridge.apply_you_move(legal["card_id"], legal["lane_index"], legal["col_index"])
    # Make a legal enemy play by ensuring the tile is enemy-owned and ranked
    gs = bridge._game_state  # type: ignore[attr-defined]
    tile = gs.board.tile_at(0, 4)
    tile.owner = "E"
    tile.rank = 3
    enemy_cid = gs.enemy_hand.as_card_ids()[0]
    bridge.register_enemy_play(enemy_cid, 0, 4)
    assert bridge.phase == "YOU_TURN_AWAITING_DRAW"
