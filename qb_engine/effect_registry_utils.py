from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

REGISTRY_PATH = Path("data/qb_effects_v1.1.json")
DB_PATH = Path("data/qb_DB_Complete_v2.json")


def load_effect_registry(path: Path | None = None) -> Dict[str, dict]:
    """Load the effect registry JSON into a dict keyed by effect_id."""
    registry_path = path or REGISTRY_PATH
    with registry_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if k != "_meta"}


def get_all_effect_ids_from_db(
    db_path: Path | None = None,
) -> Tuple[set[str], List[Tuple[str, str, str | None, str | None]]]:
    """
    Scan the card DB and return:
      - set of all effect_id values present
      - list of tuples (card_id, name, effect, effect_id) for debugging
    """
    path = db_path or DB_PATH
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    effect_ids: set[str] = set()
    rows: List[Tuple[str, str, str | None, str | None]] = []
    for entry in data:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        eid = entry.get("effect_id")
        if eid:
            effect_ids.add(eid)
        rows.append(
            (
                entry.get("id", ""),
                entry.get("name", ""),
                entry.get("effect"),
                entry.get("effect_id"),
            )
        )
    return effect_ids, rows

