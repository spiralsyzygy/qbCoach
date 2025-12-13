import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "analyze_live_jsonl_tile_timeline.py"
spec = importlib.util.spec_from_file_location("analyze_live_jsonl_tile_timeline", MODULE_PATH)
analyzer = importlib.util.module_from_spec(spec)  # type: ignore
assert spec and spec.loader
spec.loader.exec_module(analyzer)  # type: ignore

FIXTURE_LOG = ROOT / "qb_engine" / "tests" / "fixtures" / "live_tile_timeline.jsonl"


def test_tile_spec_parsing_defaults_and_explicit():
    lane, col, label = analyzer.resolve_tile_spec(None, None, None)
    assert (lane, col, label) == (2, 2, "BOT-3")

    lane, col, label = analyzer.resolve_tile_spec("TOP-5", None, None)
    assert (lane, col, label) == (0, 4, "TOP-5")

    lane, col, label = analyzer.resolve_tile_spec(None, 1, 3)
    assert (lane, col, label) == (1, 3, "MID-4")


def test_detect_changes_reports_expected_timeline():
    timeline, summary = analyzer.detect_changes(
        path=FIXTURE_LOG,
        lane=2,
        col=2,
        include_events=True,
        include_delta=True,
        show_all=False,
        limit=None,
    )

    assert summary["snapshots_scanned"] == 5
    assert summary["changes_detected"] == 5  # initial + four changes
    assert summary["first_state"].startswith("N")
    assert summary["last_state"].startswith("N")

    assert len(timeline) == 5
    # Initial state
    assert timeline[0]["tile"]["owner"] == "N"
    # First change: applied move
    assert timeline[1]["tile"]["owner"] == "Y"
    assert timeline[1]["tile"]["card_id"] == "001"
    assert set(timeline[1]["delta"].keys()) == {"owner", "rank", "card_id", "card_name"}  # type: ignore[index]
    # Second change: rank/effect update
    assert timeline[2]["tile"]["rank"] == 2
    assert "player_rank" in timeline[2]["delta"]  # type: ignore[index]
    # Third change: occupant swap + aura
    assert timeline[3]["tile"]["card_id"] == "002"
    assert timeline[3]["tile"]["has_auras"] is True
    # Fourth change: flip back to neutral
    assert timeline[4]["tile"]["owner"] == "N"

    # Attribution should include event/op when requested
    assert "apply_move" in timeline[1]["attribution"]
    assert "effect_tick" in timeline[2]["attribution"]
