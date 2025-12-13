import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "analyze_live_jsonl_board_diff.py"
spec = importlib.util.spec_from_file_location("analyze_live_jsonl_board_diff", MODULE_PATH)
module = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(module)  # type: ignore

FIXTURE_LOG = ROOT / "qb_engine" / "tests" / "fixtures" / "live_board_diff.jsonl"


def test_board_diff_basic_changes():
    deltas, summary = module.board_diffs(
        path=FIXTURE_LOG,
        start_idx=None,
        end_idx=None,
        focus_tile=None,
        focus_lane=None,
        focus_owner=None,
        min_change_count=0,
        show_all=False,
        include_nonboard=False,
    )

    # Three transitions with board changes (0->1 is a no-op and omitted)
    assert [d.idx_prev for d in deltas] == [1, 2, 3]
    assert [d.idx_next for d in deltas] == [2, 3, 4]
    assert summary["largest_change"] == 2  # multi-tile rank change at idx3
    assert summary["earliest_change_idx"] == 2
    assert summary["first_divergence_candidate"] == 2

    # Single-tile change BOT-3: owner and occupant
    first = deltas[0].tile_deltas[0]
    assert (first.lane, first.col) == (2, 2)
    assert first.changes["owner"]["to"] == "Y"
    assert first.changes["card_id"]["to"] == "001"

    # Multi-tile change includes TOP-1 and MID-5 rank bumps
    second_coords = {(td.lane, td.col) for td in deltas[1].tile_deltas}
    assert second_coords == {(0, 0), (1, 4)}

    # Occupant + owner flip with aura marker
    last = deltas[2].tile_deltas[0]
    assert last.changes["owner"]["to"] == "E"
    assert last.changes["card_id"]["to"] == "002"
    assert last.changes["has_auras"]["to"] is True


def test_focus_filters_tile_and_owner():
    # Focus BOT-3 should keep the first and last transitions only
    deltas, _ = module.board_diffs(
        path=FIXTURE_LOG,
        start_idx=None,
        end_idx=None,
        focus_tile=(2, 2),
        focus_lane=None,
        focus_owner=None,
        min_change_count=0,
        show_all=False,
        include_nonboard=False,
    )
    assert [d.idx_next for d in deltas] == [2, 4]

    # Focus owner E keeps only the enemy flip
    deltas_e, _ = module.board_diffs(
        path=FIXTURE_LOG,
        start_idx=None,
        end_idx=None,
        focus_tile=None,
        focus_lane=None,
        focus_owner="E",
        min_change_count=0,
        show_all=False,
        include_nonboard=False,
    )
    assert [d.idx_next for d in deltas_e] == [4]
    assert deltas_e[0].tile_deltas[0].changes["owner"]["to"] == "E"


def test_show_all_and_include_nonboard_adds_noop_transition():
    deltas, summary = module.board_diffs(
        path=FIXTURE_LOG,
        start_idx=None,
        end_idx=None,
        focus_tile=None,
        focus_lane=None,
        focus_owner=None,
        min_change_count=0,
        show_all=True,  # include no-op
        include_nonboard=True,
    )
    # With show_all we expect four transitions (0->1 included)
    assert len(deltas) == 4
    assert deltas[0].idx_prev == 0 and deltas[0].idx_next == 1
    assert summary["snapshots_scanned"] == 5  # total snapshots processed


def test_json_format_outputs_human_coords():
    deltas, _ = module.board_diffs(
        path=FIXTURE_LOG,
        start_idx=None,
        end_idx=None,
        focus_tile=None,
        focus_lane=None,
        focus_owner=None,
        min_change_count=0,
        show_all=False,
        include_nonboard=False,
    )
    payload = module.format_json(deltas)
    assert "TOP-1" in payload
    assert "BOT-3" in payload
