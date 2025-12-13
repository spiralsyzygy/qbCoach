"""
Analyze consecutive board diffs in a live session JSONL log to find divergences.

Examples:
- python tools/analyze_live_jsonl_board_diff.py logs/live/<file>.jsonl
- python tools/analyze_live_jsonl_board_diff.py logs/live/<file>.jsonl --focus-tile BOT-3
- python tools/analyze_live_jsonl_board_diff.py logs/live/<file>.jsonl --format json --show-all --include-nonboard
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


LANE_TO_HUMAN = {0: "TOP", 1: "MID", 2: "BOT"}
HUMAN_TO_LANE = {"TOP": 0, "MID": 1, "BOT": 2}


def parse_tile_label(label: str) -> Tuple[int, int]:
    text = label.strip().upper()
    if "-" not in text:
        raise ValueError(f"Invalid tile format: {label}")
    lane_text, col_text = text.split("-", 1)
    if lane_text not in HUMAN_TO_LANE:
        raise ValueError(f"Invalid lane in tile label: {label}")
    if not col_text.isdigit():
        raise ValueError(f"Invalid column in tile label: {label}")
    col_human = int(col_text)
    if not (1 <= col_human <= 5):
        raise ValueError(f"Column out of range in tile label: {label}")
    return HUMAN_TO_LANE[lane_text], col_human - 1


def human_coord(lane: int, col: int) -> str:
    return f"{LANE_TO_HUMAN.get(lane, lane)}-{col + 1}"


def load_log_lines(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open() as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            yield idx, json.loads(line)


def get_snapshot_container(record: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("snapshot", "turn_snapshot", "state"):
        if isinstance(record.get(key), dict):
            return record[key]
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
    elif isinstance(board_obj, dict) and isinstance(board_obj.get("tiles"), list):
        tiles.extend(flatten_board(board_obj["tiles"]))
    return tiles


def effect_marker_present(record: Dict[str, Any], lane: int, col: int) -> bool:
    for key in ("effect_tiles", "effects"):
        items = record.get(key) or []
        for item in items:
            if not isinstance(item, dict):
                continue
            lane_val = normalize_int(item.get("lane"))
            col_val = normalize_int(item.get("col"))
            if lane_val == lane and col_val == col:
                return True
    return False


def canonical_tile(tile: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    lane = normalize_int(tile.get("lane"))
    col = normalize_int(tile.get("col"))
    owner = tile.get("owner")
    rank = tile.get("rank") if "rank" in tile else tile.get("visible_rank")
    player_rank = tile.get("playerRank")
    enemy_rank = tile.get("enemyRank")
    card_id = tile.get("card_id") or tile.get("cardId")
    card_name = tile.get("card_name") or tile.get("name")
    has_auras = tile.get("has_auras") or tile.get("hasAuras") or effect_marker_present(record, lane or -1, col or -1)
    return {
        "lane": lane,
        "col": col,
        "owner": owner,
        "rank": rank,
        "player_rank": player_rank,
        "enemy_rank": enemy_rank,
        "card_id": card_id,
        "card_name": card_name,
        "has_auras": bool(has_auras),
    }


def build_board(record: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    board_obj = snapshot.get("board", record.get("board"))
    board: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for tile in flatten_board(board_obj):
        canon = canonical_tile(tile, record)
        lane = canon["lane"]
        col = canon["col"]
        if lane is None or col is None:
            continue
        board[(lane, col)] = canon
    # Ensure 3x5 coverage with defaults
    for lane in range(3):
        for col in range(5):
            board.setdefault(
                (lane, col),
                {
                    "lane": lane,
                    "col": col,
                    "owner": None,
                    "rank": None,
                    "player_rank": None,
                    "enemy_rank": None,
                    "card_id": None,
                    "card_name": None,
                    "has_auras": False,
                },
            )
    return board


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
        if isinstance(source, dict) and source.get("timestamp") is not None:
            return source["timestamp"]
    return None


def extract_attribution(record: Dict[str, Any], snapshot: Dict[str, Any]) -> str:
    parts: List[str] = []
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


@dataclass
class TileDelta:
    lane: int
    col: int
    changes: Dict[str, Dict[str, Any]]

    @property
    def human_coord(self) -> str:
        return human_coord(self.lane, self.col)


@dataclass
class BoardDelta:
    idx_prev: int
    idx_next: int
    meta: Dict[str, Any]
    tile_deltas: List[TileDelta]
    meta_delta: Optional[Dict[str, Any]] = None


def diff_tiles(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    changes: Dict[str, Dict[str, Any]] = {}
    for key in ("owner", "rank", "player_rank", "enemy_rank", "card_id", "card_name", "has_auras"):
        if prev.get(key) != curr.get(key):
            changes[key] = {"from": prev.get(key), "to": curr.get(key)}
    return changes


def diff_meta(prev_snapshot: Dict[str, Any], curr_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    diffs: Dict[str, Any] = {}
    prev_session = prev_snapshot.get("session", {})
    curr_session = curr_snapshot.get("session", {})
    for key in ("turn", "side_to_act", "phase"):
        if prev_session.get(key) != curr_session.get(key):
            diffs[key] = {"from": prev_session.get(key), "to": curr_session.get(key)}
    if prev_snapshot.get("you_hand") != curr_snapshot.get("you_hand"):
        diffs["you_hand"] = {"from": prev_snapshot.get("you_hand"), "to": curr_snapshot.get("you_hand")}
    return diffs


def board_diffs(
    path: Path,
    start_idx: Optional[int],
    end_idx: Optional[int],
    focus_tile: Optional[Tuple[int, int]],
    focus_lane: Optional[int],
    focus_owner: Optional[str],
    min_change_count: int,
    show_all: bool,
    include_nonboard: bool,
) -> Tuple[List[BoardDelta], Dict[str, Any]]:
    deltas: List[BoardDelta] = []
    prev_board: Optional[Dict[Tuple[int, int], Dict[str, Any]]] = None
    prev_snapshot: Optional[Dict[str, Any]] = None
    prev_idx: Optional[int] = None
    scanned = 0
    largest_change = 0
    earliest_change = None
    first_divergence = None

    records = list(load_log_lines(path))
    total_lines = len(records)
    for idx, record in records:
        if start_idx is not None and idx < start_idx:
            continue
        if end_idx is not None and idx > end_idx:
            break
        snapshot = get_snapshot_container(record)
        board = build_board(record, snapshot)
        scanned += 1
        if prev_board is None:
            prev_board = board
            prev_snapshot = snapshot
            prev_idx = idx
            continue
        tile_deltas: List[TileDelta] = []
        for lane in range(3):
            for col in range(5):
                changes = diff_tiles(prev_board[(lane, col)], board[(lane, col)])
                if not changes:
                    continue
                if focus_tile and (lane, col) != focus_tile:
                    continue
                if focus_lane is not None and lane != focus_lane:
                    continue
                if focus_owner is not None:
                    new_owner = changes.get("owner", {}).get("to") or board[(lane, col)].get("owner")
                    if new_owner != focus_owner:
                        continue
                tile_deltas.append(TileDelta(lane=lane, col=col, changes=changes))
        meta_delta = diff_meta(prev_snapshot, snapshot) if include_nonboard and prev_snapshot else None
        if tile_deltas:
            largest_change = max(largest_change, len(tile_deltas))
            earliest_change = earliest_change if earliest_change is not None else idx
            if first_divergence is None:
                attribution = extract_attribution(record, snapshot)
                if attribution != "(no move attribution in log line)":
                    first_divergence = idx
        if show_all or tile_deltas or (include_nonboard and meta_delta):
            meta = extract_session(snapshot)
            meta["timestamp"] = extract_timestamp(record, snapshot)
            meta["attribution"] = extract_attribution(record, snapshot)
            board_delta = BoardDelta(
                idx_prev=prev_idx if prev_idx is not None else idx - 1,
                idx_next=idx,
                meta=meta,
                tile_deltas=tile_deltas,
                meta_delta=meta_delta,
            )
            if show_all or len(tile_deltas) >= min_change_count:
                deltas.append(board_delta)
        prev_board = board
        prev_snapshot = snapshot
        prev_idx = idx

    summary = {
        "snapshots_scanned": scanned,
        "board_transitions": len(deltas),
        "largest_change": largest_change,
        "earliest_change_idx": earliest_change,
        "first_divergence_candidate": first_divergence,
        "total_lines": total_lines,
    }
    return deltas, summary


def format_markdown(deltas: List[BoardDelta], summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    for delta in deltas:
        header = (
            f"idx {delta.idx_prev} \u2192 {delta.idx_next} | "
            f"turn {delta.meta.get('turn')} | side_to_act {delta.meta.get('side_to_act')} | "
            f"phase {delta.meta.get('phase')}"
        )
        lines.append(f"## {header}")
        if delta.meta.get("timestamp") is not None:
            lines.append(f"- timestamp: {delta.meta.get('timestamp')}")
        lines.append(f"- attribution: {delta.meta.get('attribution')}")
        if delta.meta_delta:
            lines.append(f"- meta_delta: {delta.meta_delta}")
        if not delta.tile_deltas:
            lines.append("_no board changes_")
            continue
        lines.append("| coord | owner | rank | occupant | auras | other |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for td in delta.tile_deltas:
            changes = td.changes
            owner = changes.get("owner", {})
            rank = changes.get("rank", {})
            player_rank = changes.get("player_rank", {})
            enemy_rank = changes.get("enemy_rank", {})
            occ = changes.get("card_name") or changes.get("card_id") or {}
            auras = changes.get("has_auras", {})
            owner_str = f"{owner.get('from')} \u2192 {owner.get('to')}" if owner else "-"
            rank_parts = []
            if rank:
                rank_parts.append(f"r:{rank.get('from')}→{rank.get('to')}")
            if player_rank:
                rank_parts.append(f"p:{player_rank.get('from')}→{player_rank.get('to')}")
            if enemy_rank:
                rank_parts.append(f"e:{enemy_rank.get('from')}→{enemy_rank.get('to')}")
            rank_str = "; ".join(rank_parts) if rank_parts else "-"
            occ_str = f"{occ.get('from')} → {occ.get('to')}" if occ else "-"
            aura_str = f"{auras.get('from')} → {auras.get('to')}" if auras else "-"
            other_keys = {k: v for k, v in changes.items() if k not in {"owner", "rank", "player_rank", "enemy_rank", "card_id", "card_name", "has_auras"}}
            other_str = json.dumps(other_keys) if other_keys else "-"
            lines.append(f"| {td.human_coord} | {owner_str} | {rank_str} | {occ_str} | {aura_str} | {other_str} |")
        lines.append("")
    lines.append("### Summary")
    lines.append(f"- snapshots scanned: {summary.get('snapshots_scanned')}")
    lines.append(f"- board-changing transitions: {summary.get('board_transitions')}")
    lines.append(f"- largest change (tiles): {summary.get('largest_change')}")
    lines.append(f"- earliest change idx: {summary.get('earliest_change_idx')}")
    lines.append(f"- first divergence candidate: {summary.get('first_divergence_candidate')}")
    return "\n".join(lines)


def format_json(deltas: List[BoardDelta]) -> str:
    payload = []
    for delta in deltas:
        payload.append(
            {
                "idx_prev": delta.idx_prev,
                "idx_next": delta.idx_next,
                "meta": delta.meta,
                "tile_deltas": [
                    {"lane": td.lane, "col": td.col, "human_coord": td.human_coord, "changes": td.changes}
                    for td in delta.tile_deltas
                ],
                "meta_delta": delta.meta_delta,
            }
        )
    return json.dumps(payload, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diff consecutive board states in a live JSONL log.")
    parser.add_argument("path", type=str, help="Path to JSONL log.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    parser.add_argument("--limit", type=int, help="Maximum number of diff records to print.")
    parser.add_argument("--start-idx", type=int, help="Start JSONL index (inclusive).")
    parser.add_argument("--end-idx", type=int, help="End JSONL index (inclusive).")
    parser.add_argument("--show-all", action="store_true", help="Include transitions even with no board changes.")
    parser.add_argument("--include-nonboard", action="store_true", help="Include session/hand deltas.")
    parser.add_argument("--focus-tile", type=str, help='Filter to a single tile like "BOT-3".')
    parser.add_argument("--focus-lane", type=str, help="Filter to a lane: TOP|MID|BOT.")
    parser.add_argument("--focus-owner", type=str, help="Filter to changes where owner becomes this value (Y|E|N).")
    parser.add_argument("--min-change-count", type=int, default=0, help="Minimum tile changes required to emit a diff.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.path)
    if not path.is_file():
        raise SystemExit(f"Log file not found: {path}")

    focus_tile = None
    if args.focus_tile:
        try:
            focus_tile = parse_tile_label(args.focus_tile)
        except ValueError as exc:
            raise SystemExit(str(exc))
    focus_lane = None
    if args.focus_lane:
        lane_upper = args.focus_lane.upper()
        if lane_upper not in HUMAN_TO_LANE:
            raise SystemExit("focus-lane must be TOP, MID, or BOT.")
        focus_lane = HUMAN_TO_LANE[lane_upper]
    focus_owner = None
    if args.focus_owner:
        focus_owner = args.focus_owner.upper()
        if focus_owner not in {"Y", "E", "N"}:
            raise SystemExit("focus-owner must be Y, E, or N.")

    deltas, summary = board_diffs(
        path=path,
        start_idx=args.start_idx,
        end_idx=args.end_idx,
        focus_tile=focus_tile,
        focus_lane=focus_lane,
        focus_owner=focus_owner,
        min_change_count=args.min_change_count,
        show_all=args.show_all,
        include_nonboard=args.include_nonboard,
    )

    if args.limit is not None:
        deltas = deltas[: args.limit]

    if args.format == "json":
        print(format_json(deltas))
    else:
        print(format_markdown(deltas, summary))


if __name__ == "__main__":
    main()
