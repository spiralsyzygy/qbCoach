from qb_engine.live_session import LiveSessionEngineBridge, format_turn_snapshot_for_ux


def test_coaching_mode_default_and_strategy():
    # Default should now be strategy
    bridge_default = LiveSessionEngineBridge()
    bridge_default.init_match()
    snap_default = bridge_default.create_turn_snapshot()
    rendered_default = format_turn_snapshot_for_ux(snap_default)
    assert "coaching_mode: strategy" in rendered_default

    # Explicit strategy
    bridge_strategy = LiveSessionEngineBridge(coaching_mode="strategy")
    bridge_strategy.init_match(coaching_mode="strategy")
    snap_strategy = bridge_strategy.create_turn_snapshot()
    rendered_strategy = format_turn_snapshot_for_ux(snap_strategy)
    assert "coaching_mode: strategy" in rendered_strategy
