# qb_engine/card_hydrator.py

import json
from pathlib import Path
from typing import Dict, List

from qb_engine.models import Card, ProjectionCell


# Mapping from column letter to grid index (left→right): E,D,C,B,A
COL_TO_INDEX = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4}


def parse_pattern(pattern: str | None) -> List[ProjectionCell]:
    """
    Parse pattern notation like 'B3X,D2P,D4P' into projection cells.
    Placement tile is (0,0) with symbol 'W'.
    """
    cells: List[ProjectionCell] = [ProjectionCell(0, 0, "W")]
    if not pattern:
        return cells

    for token in pattern.split(","):
        token = token.strip()
        if not token:
            continue
        if len(token) < 3:
            raise ValueError(f"Invalid pattern token: {token}")
        col_letter = token[0].upper()
        symbol = token[-1].upper()
        row_part = token[1:-1]

        if col_letter not in COL_TO_INDEX:
            raise ValueError(f"Invalid column letter in token: {token}")
        try:
            row_number = int(row_part)
        except ValueError as exc:
            raise ValueError(f"Invalid row number in token: {token}") from exc
        if symbol not in ("P", "E", "X"):
            raise ValueError(f"Invalid projection symbol in token: {token}")

        row_index = row_number - 1  # rows 1..5 -> 0..4
        col_index = COL_TO_INDEX[col_letter]
        row_offset = row_index - 2
        col_offset = col_index - 2

        cells.append(ProjectionCell(row_offset=row_offset, col_offset=col_offset, symbol=symbol))

    return cells


class CardHydrator:
    """
    Loads card data from the Queen's Blood JSON DB and constructs Card objects.

    Rules/constraints:
    - Never infer data.
    - Use the JSON file in data/qb_DB_Complete_v2.json by default.
    """

    def __init__(self, db_path: str | None = None):
        # Default path based on your current repo layout
        if db_path is None:
            db_path = "data/qb_DB_Complete_v2.json"

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Card DB not found at: {self.db_path}")

        # Cache of hydrated Card objects, keyed by card id
        self.cache: Dict[str, Card] = {}

        # Load the raw JSON into memory once
        with self.db_path.open("r", encoding="utf-8") as f:
            self.db = json.load(f)

        # Build an index by card id for quick lookup
        self.index: Dict[str, dict] = {
            entry["id"]: entry
            for entry in self.db
            if isinstance(entry, dict) and "id" in entry
        }


    def get_card(self, card_id: str) -> Card:
        """
        Return a hydrated Card object for the given id.

        Uses an internal cache so repeated calls are cheap.
        """
        if card_id in self.cache:
            return self.cache[card_id]

        if card_id not in self.index:
            raise KeyError(f"Card '{card_id}' not found in database.")

        data = self.index[card_id]

        card = Card(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            cost=data["cost"],
            power=data["power"],
            pattern=data.get("pattern"),
            grid=data["grid"],
            effect=data.get("effect"),
            effect_id=data.get("effect_id"),
            effect_description=data.get("effect_description"),
            projection_cells=parse_pattern(data.get("pattern")),
        )

        self.cache[card_id] = card
        return card
