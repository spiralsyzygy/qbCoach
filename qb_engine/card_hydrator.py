# qb_engine/card_hydrator.py

import json
from pathlib import Path
from typing import Dict

from qb_engine.models import Card


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
        self.index: Dict[str, dict] = {entry["id"]: entry for entry in self.db}

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
        )

        self.cache[card_id] = card
        return card
