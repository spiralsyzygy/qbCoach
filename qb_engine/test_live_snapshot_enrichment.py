from qb_engine.live_session import LiveSessionEngineBridge


def test_recommend_moves_enriched_snapshot():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    moves = bridge.recommend_moves(top_n=1)
    assert moves, "Expected at least one recommendation"
    rec = moves[0]
    move = rec.get("move", {})
    assert "card_id" in move
    assert "card_name" in move
    assert "lane" in move and "col" in move
    assert "move_strength" in rec
    assert isinstance(rec["move_strength"], (int, float))
    assert "lane_delta" in rec and isinstance(rec["lane_delta"], dict)
    projection = rec.get("projection_summary", {})
    assert "tile_deltas" in projection

    snapshot = bridge.create_turn_snapshot(engine_output={"recommend_moves": moves})
    assert "lanes" in snapshot and "global" in snapshot
    for lane in ["top", "mid", "bot"]:
        assert lane in snapshot["lanes"]
        lane_entry = snapshot["lanes"][lane]
        assert "you_power" in lane_entry and "enemy_power" in lane_entry and "net_power" in lane_entry
    assert "you_score_estimate" in snapshot["global"]
    assert "enemy_score_estimate" in snapshot["global"]

