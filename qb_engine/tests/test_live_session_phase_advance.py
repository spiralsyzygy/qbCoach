from qb_engine.live_session import LiveSessionEngineBridge


def test_pawn_persists_across_phase_advance():
    bridge = LiveSessionEngineBridge(session_mode="live_coaching")
    bridge.init_match()
    bridge.sync_you_hand_from_ids(["001"])

    # Ensure placement tile is legal (boost rank/owner for the test board slot).
    tile = bridge._game_state.board.tile_at(2, 1)  # BOT, col=2 (0-based)
    tile.owner = "Y"
    tile.rank = max(tile.rank, 2)

    # Play a card that projects a pawn onto BOT-3 (lane=2, col=2).
    bridge.apply_you_move("001", row=2, col=1)  # play at BOT-2 (zero-based col=1)
    state_after_play = bridge.get_state()
    assert state_after_play["board"][2][2]["owner"] == "Y"

    # Advance to YOUR turn ready state (simulate enemy turn and draw).
    bridge.phase = "YOU_TURN_AWAITING_DRAW"
    bridge.side_to_act = "Y"
    bridge.turn_counter += 1
    bridge.apply_draw("001")  # use known card to satisfy hydrator

    snapshot = bridge.create_turn_snapshot(last_event="phase_ready_snapshot")
    assert snapshot["last_event"] == "phase_ready_snapshot"
    assert snapshot["session"]["phase"] == "YOU_TURN_READY_FOR_REC_OR_PLAY"
    assert snapshot["board"][2][2]["owner"] == "Y"
