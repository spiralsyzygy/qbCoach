from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from qb_engine.card_db_validator import pattern_to_grid


def load_db(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_db(path: Path, data: List[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fix_mismatches(db: List[Dict[str, Any]]) -> List[Tuple[str, Tuple[int, int], str, str]]:
    """
    For each card, overwrite non-dot cells in grid with the expected pattern-derived symbol.
    Returns a list of corrections: (card_id, (row, col), old, new).
    """
    corrections: List[Tuple[str, Tuple[int, int], str, str]] = []
    for entry in db:
        if not isinstance(entry, dict) or "id" not in entry or "grid" not in entry:
            continue
        expected = pattern_to_grid(entry.get("pattern"))
        grid = entry["grid"]
        for r in range(5):
            for c in range(5):
                if expected[r][c] != ".":
                    if grid[r][c] != expected[r][c]:
                        corrections.append((entry["id"], (r, c), grid[r][c], expected[r][c]))
                        grid[r][c] = expected[r][c]
    return corrections


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix pattern/grid mismatches in card DB.")
    parser.add_argument(
        "db_path",
        type=Path,
        nargs="?",
        default=Path("data/qb_DB_Complete_v2.json"),
        help="Path to the card DB JSON file.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        help="Optional path to write a corrections log.",
    )
    args = parser.parse_args()

    db_path: Path = args.db_path
    if not db_path.exists():
        raise SystemExit(f"DB file not found: {db_path}")

    data = load_db(db_path)
    corrections = fix_mismatches(data)
    save_db(db_path, data)

    if corrections:
        print(f"Applied {len(corrections)} corrections to {db_path}")
    else:
        print("No corrections needed.")

    if args.log:
        lines = []
        for card_id, (r, c), old, new in corrections:
            lines.append(f"{card_id} @ ({r},{c}): {old} -> {new}")
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote corrections log to {args.log}")


if __name__ == "__main__":
    main()
