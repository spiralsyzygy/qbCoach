import json

from qb_engine.live_session import LiveSessionEngineBridge
from qb_engine.live_session import format_turn_snapshot_for_ux


def test_live_session_bridge_smoke():
    bridge = LiveSessionEngineBridge(session_mode="live_coaching")
    bridge.init_match(you_deck_ids=None, enemy_deck_tag=None)

    snapshot = bridge.get_state()
    assert isinstance(snapshot, dict)
    assert "session" in snapshot
    assert "board" in snapshot
    assert snapshot["session"]["mode"] == "live_coaching"


def test_resolve_card_id_roundtrip():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    first_id = list(bridge._card_index.keys())[0]  # type: ignore[attr-defined]
    assert bridge.resolve_card_id(first_id) == first_id


def test_format_turn_snapshot_does_not_crash():
    snapshot = {
        "session": {"mode": "live_coaching", "session_id": "sid", "turn": 1, "side_to_act": "Y"},
        "board": [
            [
                {"lane": 0, "col": 0, "owner": "Y", "rank": 1, "card_id": None},
                {"lane": 0, "col": 1, "owner": "Y", "rank": 1, "card_id": "001"},
            ],
            [
                {"lane": 1, "col": 0, "owner": "Y", "rank": 1, "card_id": None},
                {"lane": 1, "col": 1, "owner": "Y", "rank": 1, "card_id": None},
            ],
            [
                {"lane": 2, "col": 0, "owner": "Y", "rank": 1, "card_id": None},
                {"lane": 2, "col": 1, "owner": "Y", "rank": 1, "card_id": None},
            ],
        ],
        "you_hand": ["001", "002"],
        "engine_output": {"recommend_moves": [{"move": {"card_id": "001", "lane_index": 0, "col_index": 1}}]},
    }
    formatted = format_turn_snapshot_for_ux(snapshot)
    assert "[SESSION]" in formatted
    assert "[BOARD]" in formatted
    assert "[YOU_HAND]" in formatted
    assert "coaching_mode: strict" in formatted


def test_append_turn_snapshot(tmp_path):
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    snapshot = bridge.create_turn_snapshot()
    bridge.log_path = tmp_path / "log.jsonl"
    bridge.append_turn_snapshot(snapshot)
    assert bridge.log_path.exists()
    content = bridge.log_path.read_text().strip()
    assert content
    # Ensure JSON is valid
    line_obj = json.loads(content.splitlines()[0])
    assert "session" in line_obj


def test_create_turn_snapshot_has_keys():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    snapshot = bridge.create_turn_snapshot(engine_output={"recommend_moves": []}, chosen_move={"card_id": "001"})
    assert "session" in snapshot
    assert "board" in snapshot
    assert "you_hand" in snapshot
    assert "engine_output" in snapshot
    assert snapshot["engine_output"] == {"recommend_moves": []}
    assert snapshot["chosen_move"] == {"card_id": "001"}
