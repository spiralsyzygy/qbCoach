"""
Analyze a live session JSONL log and emit a timeline for a single board tile.

Usage examples:
python tools/analyze_live_jsonl_tile_timeline.py logs/live/<file>.jsonl --tile BOT-3
python tools/analyze_live_jsonl_tile_timeline.py logs/live/<file>.jsonl --lane 2 --col 2 --show-delta --show-events
python tools/analyze_live_jsonl_tile_timeline.py logs/live/<file>.jsonl --format json --limit 5
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_TILE_LABEL = "BOT-3"
DEFAULT_LANE = 2  # engine coordinate for BOT
DEFAULT_COL = 2  # engine coordinate for column 3 (1-based)


@dataclass
class TileState:
    owner: Any
    rank: Any
    player_rank: Any
    enemy_rank: Any
    card_id: Any
    card_name: Any
    has_auras: Any
    raw: Dict[str, Any]

    def compare_key(self) -> Tuple:
        return (
            self.owner,
            self.rank,
            self.player_rank,
            self.enemy_rank,
            self.card_id,
            self.card_name,
            bool(self.has_auras),
        )


def parse_tile_label(tile_label: str) -> Tuple[int, int, str]:
    label = tile_label.strip().upper()
    if "-" not in label:
        raise ValueError(f"Invalid tile format: {tile_label}")
    lane_text, col_text = label.split("-", 1)
    lane_map = {"TOP": 0, "MID": 1, "BOT": 2}
    if lane_text not in lane_map:
        raise ValueError(f"Invalid lane in tile label: {tile_label}")
    if not col_text.isdigit():
        raise ValueError(f"Invalid column in tile label: {tile_label}")
    col_human = int(col_text)
    if not (1 <= col_human <= 5):
        raise ValueError(f"Column out of range in tile label: {tile_label}")
    return lane_map[lane_text], col_human - 1, f"{lane_text}-{col_human}"


def resolve_tile_spec(tile: Optional[str], lane: Optional[int], col: Optional[int]) -> Tuple[int, int, str]:
    if tile:
        return parse_tile_label(tile)
    if lane is not None and col is not None:
        if lane not in (0, 1, 2) or col not in (0, 1, 2, 3, 4):
            raise ValueError("Lane must be 0/1/2 and col must be 0..4.")
        human_lane = {0: "TOP", 1: "MID", 2: "BOT"}[lane]
        return lane, col, f"{human_lane}-{col + 1}"
    return DEFAULT_LANE, DEFAULT_COL, DEFAULT_TILE_LABEL


def load_log_lines(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open() as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            yield idx, json.loads(line)


def get_snapshot_container(record: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(record.get("snapshot"), dict):
        return record["snapshot"]
    return record


def normalize_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def flatten_board(board_obj: Any) -> List[Dict[str, Any]]:
    tiles: List[Dict[str, Any]] = []
    if isinstance(board_obj, list):
        if board_obj and isinstance(board_obj[0], list):
            # Matrix form: rows -> cols
            for lane_idx, row in enumerate(board_obj):
                for col_idx, cell in enumerate(row):
                    if isinstance(cell, dict):
                        tile = dict(cell)
                        tile.setdefault("lane", lane_idx)
                        tile.setdefault("col", col_idx)
                        tiles.append(tile)
        else:
            for cell in board_obj:
                if isinstance(cell, dict):
                    tiles.append(dict(cell))
    elif isinstance(board_obj, dict) and "tiles" in board_obj and isinstance(board_obj["tiles"], list):
        tiles.extend(flatten_board(board_obj["tiles"]))
    return tiles


def find_tile(snapshot: Dict[str, Any], lane: int, col: int) -> Optional[Dict[str, Any]]:
    board_obj = snapshot.get("board")
    if board_obj is None and isinstance(snapshot.get("state"), dict):
        board_obj = snapshot["state"].get("board")
    if board_obj is None:
        return None
    for tile in flatten_board(board_obj):
        lane_val = normalize_int(tile.get("lane"))
        col_val = normalize_int(tile.get("col"))
        if lane_val is None or col_val is None:
            continue
        if lane_val == lane and col_val == col:
            return tile
    return None


def has_effect_marker(record: Dict[str, Any], lane: int, col: int) -> bool:
    effect_tiles = record.get("effect_tiles") or record.get("effects") or []
    for item in effect_tiles:
        if not isinstance(item, dict):
            continue
        lane_val = normalize_int(item.get("lane"))
        col_val = normalize_int(item.get("col"))
        if lane_val == lane and col_val == col:
            return True
    return False


def extract_tile_state(record: Dict[str, Any], snapshot: Dict[str, Any], lane: int, col: int) -> Optional[TileState]:
    tile = find_tile(snapshot, lane, col)
    if tile is None:
        return None
    return TileState(
        owner=tile.get("owner"),
        rank=tile.get("rank"),
        player_rank=tile.get("playerRank"),
        enemy_rank=tile.get("enemyRank"),
        card_id=tile.get("card_id"),
        card_name=tile.get("card_name") or tile.get("name"),
        has_auras=tile.get("has_auras") or has_effect_marker(record, lane, col),
        raw=tile,
    )


def extract_session(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    session = snapshot.get("session", {})
    return {
        "session_id": session.get("session_id"),
        "turn": session.get("turn"),
        "side_to_act": session.get("side_to_act"),
        "phase": session.get("phase") or session.get("state"),
    }


def extract_timestamp(record: Dict[str, Any], snapshot: Dict[str, Any]) -> Optional[Any]:
    for source in (record, snapshot, snapshot.get("session", {})):
        if not isinstance(source, dict):
            continue
        ts = source.get("timestamp")
        if ts is not None:
            return ts
    return None


def extract_attribution(record: Dict[str, Any], snapshot: Dict[str, Any], include_events: bool) -> str:
    parts: List[str] = []
    if include_events:
        for key in ("op", "event"):
            val = record.get(key)
            if val:
                parts.append(f"{key}={val}")
    move = record.get("chosen_move") or snapshot.get("chosen_move") or snapshot.get("last_move")
    if isinstance(move, dict):
        side = move.get("side") or move.get("actor")
        card = move.get("card_name") or move.get("card_id")
        lane_val = move.get("lane") if move.get("lane") is not None else move.get("row")
        col_val = move.get("col")
        coord = f"@({lane_val},{col_val})" if lane_val is not None and col_val is not None else ""
        parts.append(f"move:{side or '?'}:{card or '?'}{coord}")
    if not parts:
        return "(no move attribution in log line)"
    return "; ".join(parts)


def summarize_state(state: TileState) -> str:
    occ = state.card_name or state.card_id or "-"
    ranks = []
    if state.rank is not None:
        ranks.append(f"r{state.rank}")
    if state.player_rank is not None:
        ranks.append(f"p{state.player_rank}")
    if state.enemy_rank is not None:
        ranks.append(f"e{state.enemy_rank}")
    aura = " aura" if state.has_auras else ""
    return f"{state.owner}{''.join(ranks)} {occ}{aura}".strip()


def detect_changes(
    path: Path,
    lane: int,
    col: int,
    include_events: bool,
    include_delta: bool,
    show_all: bool,
    limit: Optional[int],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    prev_state: Optional[TileState] = None
    change_points: List[Dict[str, Any]] = []
    scanned = 0
    first_state: Optional[TileState] = None
    last_state: Optional[TileState] = None

    for idx, record in load_log_lines(path):
        snapshot = get_snapshot_container(record)
        tile_state = extract_tile_state(record, snapshot, lane, col)
        if tile_state is None:
            continue
        scanned += 1
        if first_state is None:
            first_state = tile_state
        session = extract_session(snapshot)
        timestamp = extract_timestamp(record, snapshot)
        attribution = extract_attribution(record, snapshot, include_events)
        delta_fields: Dict[str, Any] = {}
        diff_keys: List[str] = []
        changed = prev_state is None
        if prev_state and tile_state.compare_key() != prev_state.compare_key():
            changed = True
            for field in ("owner", "rank", "player_rank", "enemy_rank", "card_id", "card_name", "has_auras"):
                before = getattr(prev_state, field)
                after = getattr(tile_state, field)
                if before != after:
                    diff_keys.append(field)
                    if include_delta:
                        delta_fields[field] = {"from": before, "to": after}
        if show_all or changed:
            row = {
                "idx": idx,
                "timestamp": timestamp,
                "session_id": session.get("session_id"),
                "turn": session.get("turn"),
                "side_to_act": session.get("side_to_act"),
                "phase": session.get("phase"),
                "tile": {
                    "owner": tile_state.owner,
                    "rank": tile_state.rank,
                    "player_rank": tile_state.player_rank,
                    "enemy_rank": tile_state.enemy_rank,
                    "card_id": tile_state.card_id,
                    "card_name": tile_state.card_name,
                    "has_auras": tile_state.has_auras,
                },
                "attribution": attribution,
            }
            if include_delta and delta_fields:
                row["delta"] = delta_fields
            timeline.append(row)
            if changed:
                change_points.append(
                    {"idx": idx, "turn": session.get("turn"), "delta": diff_keys or ["initial"]}
                )
        prev_state = tile_state
        last_state = tile_state
        if limit and len(timeline) >= limit:
            break

    summary = {
        "snapshots_scanned": scanned,
        "changes_detected": len(change_points),
        "first_state": summarize_state(first_state) if first_state else None,
        "last_state": summarize_state(last_state) if last_state else None,
        "change_points": change_points,
    }
    return timeline, summary


def format_markdown(timeline: List[Dict[str, Any]], summary: Dict[str, Any], include_delta: bool) -> str:
    has_timestamp = any(row.get("timestamp") is not None for row in timeline)
    headers = ["idx"]
    if has_timestamp:
        headers.append("ts")
    headers += ["turn", "side", "phase", "tile_owner/rank", "occupant", "auras", "attribution"]
    if include_delta:
        headers.append("delta")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]

    for row in timeline:
        tile = row["tile"]
        tile_info = f"{tile.get('owner')} {tile.get('rank')}"
        if tile.get("player_rank") is not None or tile.get("enemy_rank") is not None:
            pr = tile.get("player_rank")
            er = tile.get("enemy_rank")
            extra = []
            if pr is not None:
                extra.append(f"p{pr}")
            if er is not None:
                extra.append(f"e{er}")
            tile_info += f" ({'/'.join(extra)})"
        occupant = tile.get("card_name") or tile.get("card_id") or "-"
        auras = "yes" if tile.get("has_auras") else "-"
        row_cells = [str(row["idx"])]
        if has_timestamp:
            row_cells.append(str(row.get("timestamp") or "-"))
        row_cells += [
            str(row.get("turn") or "-"),
            str(row.get("side_to_act") or "-"),
            str(row.get("phase") or "-"),
            tile_info,
            occupant,
            auras,
            row.get("attribution") or "-",
        ]
        if include_delta:
            delta_str = "-"
            if row.get("delta"):
                delta_parts = [f"{k}: {v['from']} -> {v['to']}" for k, v in row["delta"].items()]
                delta_str = "; ".join(delta_parts)
            row_cells.append(delta_str)
        lines.append("| " + " | ".join(row_cells) + " |")

    summary_lines = [
        "",
        "Summary:",
        f"- snapshots scanned: {summary.get('snapshots_scanned', 0)}",
        f"- changes detected: {summary.get('changes_detected', 0)}",
        f"- first state: {summary.get('first_state')}",
        f"- last state: {summary.get('last_state')}",
        f"- change points: {summary.get('change_points')}",
    ]
    return "\n".join(lines + summary_lines)


def format_json_output(timeline: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    return json.dumps({"timeline": timeline, "summary": summary}, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a live session JSONL log for tile changes.")
    parser.add_argument("path", type=str, help="Path to a live session JSONL file.")
    parser.add_argument("--tile", type=str, help='Human tile spec like "BOT-3".')
    parser.add_argument("--lane", type=int, help="Engine lane index (0=TOP,1=MID,2=BOT).")
    parser.add_argument("--col", type=int, help="Engine col index (0-based).")
    parser.add_argument("--show-events", action="store_true", help="Include op/event fields in attribution.")
    parser.add_argument("--show-delta", action="store_true", help="Show per-field changes vs previous snapshot.")
    parser.add_argument("--show-all", action="store_true", help="Show every snapshot (not just changes).")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--limit", type=int, help="Limit the number of emitted rows.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.path)
    if not path.is_file():
        raise SystemExit(f"Log file not found: {path}")

    try:
        lane, col, label = resolve_tile_spec(args.tile, args.lane, args.col)
    except ValueError as exc:
        raise SystemExit(str(exc))

    timeline, summary = detect_changes(
        path=path,
        lane=lane,
        col=col,
        include_events=args.show_events,
        include_delta=args.show_delta,
        show_all=args.show_all,
        limit=args.limit,
    )

    if args.format == "markdown":
        print(f"# Tile timeline for {label} (lane={lane}, col={col})")
        print(format_markdown(timeline, summary, include_delta=args.show_delta))
    else:
        print(format_json_output(timeline, summary))


if __name__ == "__main__":
    main()
