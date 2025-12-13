from qb_engine.effect_aura import EffectAura
from qb_engine.live_session import LiveSessionEngineBridge, format_turn_snapshot_for_ux


def test_effect_overlay_on_empty_tile():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    # Add an aura to a neutral tile (MID, col 2 => indices 1,2)
    gs = bridge._game_state
    assert gs is not None
    card_id = gs.player_hand.as_card_ids()[0]
    gs.board.effect_auras.append(EffectAura(lane_index=1, col_index=2, card_id=card_id, description="buff"))
    snapshot = bridge.create_turn_snapshot()
    rendered = format_turn_snapshot_for_ux(snapshot)
    assert "[N0★]" in rendered


def test_effect_overlay_on_occupied_tile():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    gs = bridge._game_state
    assert gs is not None
    # Place a card on MID-3 (lane 1, col 2) and add an aura there
    tile = gs.board.tile_at(1, 2)
    tile.owner = "Y"
    tile.rank = 1
    tile.card_id = gs.player_hand.as_card_ids()[0]
    gs.board.effect_auras.append(EffectAura(lane_index=1, col_index=2, card_id=tile.card_id, description="buff"))
    snapshot = bridge.create_turn_snapshot()
    rendered = format_turn_snapshot_for_ux(snapshot)
    assert "★" in rendered
    # Ensure the specific tile token contains the star and card id
    assert f"[Y{tile.rank}:{tile.card_id}★]" in rendered
