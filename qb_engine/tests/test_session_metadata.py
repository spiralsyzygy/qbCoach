from qb_engine.live_session import LiveSessionEngineBridge


def test_default_coaching_mode_is_strategy():
    bridge = LiveSessionEngineBridge()
    assert bridge.coaching_mode == "strategy"
    bridge.init_match()
    assert bridge.coaching_mode == "strategy"


def test_deck_tags_persist_in_snapshot():
    bridge = LiveSessionEngineBridge()
    bridge.init_match(deck_tags=["regina", "anti-buff"])
    state = bridge.get_state()
    session = state.get("session", {})
    assert session.get("deck_tags") == ["regina", "anti-buff"]
