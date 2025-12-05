# qb_engine/models.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Card:
    """
    Fundamental card data model, loaded directly from data/qb_DB_Complete_v2.json.

    All fields must match the JSON database exactly.
    """
    id: str
    name: str
    category: str
    cost: int
    power: int
    pattern: str
    grid: List[List[str]]
    effect: Optional[str] = None
    effect_id: Optional[str] = None  # <-- NEW

    def __str__(self) -> str:
        """
        Simplified human-readable representation.
        """
        return f"<Card {self.id} {self.name} (cost={self.cost}, power={self.power})>"
