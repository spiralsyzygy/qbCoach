import pytest

from qb_engine.effect_aura import EffectAura
from qb_engine.live_session import LiveSessionEngineBridge, parse_resync_board_lines


def test_manual_resync_board_applies_and_logs(tmp_path, monkeypatch):
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    monkeypatch.setattr(bridge, "_ensure_log_path", lambda: tmp_path / "log.jsonl")

    lines = [
        "[Y1] [N0] [Y2] [N0] [E1]",
        "[Y1] [Y:001] [N0] [E1] [E1]",
        "[Y1] [N0] [E2] [N0] [E1]",
    ]
    snapshot = bridge.manual_resync_board(lines)
    board = bridge._game_state.board  # type: ignore[union-attr]
    tile = board.tile_at(1, 1)
    assert tile.card_id == "001"
    assert tile.owner == "Y"
    assert tile.placed_by == "Y"
    # Recompute should preserve occupied allegiance
    board.recompute_influence_from_deltas()
    tile_after = board.tile_at(1, 1)
    assert tile_after.owner == "Y"
    assert tile_after.rank >= 1
    assert snapshot["last_event"] == "manual_resync_board"
    assert snapshot.get("manual_override") is True


def test_resync_rejects_neutral_occupied():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    lines = [
        "[Y1] [N0] [001] [N0] [E1]",
        "[Y1] [N0] [N0] [N0] [E1]",
        "[Y1] [N0] [N0] [N0] [E1]",
    ]
    with pytest.raises(ValueError):
        parse_resync_board_lines(lines, bridge._game_state.board, bridge._hydrator)  # type: ignore[arg-type]


def test_resync_accepts_star_and_clears_effects(tmp_path, monkeypatch):
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    board = bridge._game_state.board  # type: ignore[union-attr]
    board.effect_auras.append(EffectAura(lane_index=0, col_index=2, card_id="TEST", description="aura"))
    board.direct_effects[(0, 0)] = []
    monkeypatch.setattr(bridge, "_ensure_log_path", lambda: tmp_path / "log.jsonl")

    lines = [
        "[Y1★] [N0] [Y2★] [N0] [E1]",
        "[Y1] [Y:001★] [N0] [E1] [E1★]",
        "[Y1] [N0] [E:020:5★] [N0] [E1]",
    ]
    bridge.manual_resync_board(lines)
    new_board = bridge._game_state.board  # type: ignore[union-attr]
    assert not new_board.effect_auras
    assert not new_board.direct_effects
    tile = new_board.tile_at(2, 2)
    assert tile.card_id == "020"
    assert tile.placed_by == "E"


def test_resync_cancel_leaves_board_unchanged():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    before = [[(t.owner, t.rank, t.card_id) for t in row] for row in bridge._game_state.board.tiles]  # type: ignore[union-attr]
    lines = [
        "[Y1] [N0] [Y2] [N0] [E1]",
        "[Y1] [Y:001] [N0] [E1] [E1]",
        "[Y1] [N0] [E2] [N0] [E1]",
    ]
    # Preview only; do not apply
    parse_resync_board_lines(lines, bridge._game_state.board, bridge._hydrator)  # type: ignore[arg-type]
    after = [[(t.owner, t.rank, t.card_id) for t in row] for row in bridge._game_state.board.tiles]  # type: ignore[union-attr]
    assert after == before


def test_resync_empty_token_clears_occupant():
    bridge = LiveSessionEngineBridge()
    bridge.init_match()
    board = bridge._game_state.board  # type: ignore[union-attr]
    tile = board.tile_at(1, 2)
    tile.owner = "Y"
    tile.rank = 2
    tile.card_id = "001"
    tile.placed_by = "Y"

    lines = [
        "[Y1] [N0] [N0] [N0] [E1]",
        "[Y1] [N0] [N0] [N0] [E1]",
        "[Y1] [N0] [N0] [N0] [E1]",
    ]
    bridge.manual_resync_board(lines)
    cleared_tile = bridge._game_state.board.tile_at(1, 2)  # type: ignore[union-attr]
    assert cleared_tile.card_id is None
    assert cleared_tile.owner == "N"
    assert cleared_tile.rank == 0
