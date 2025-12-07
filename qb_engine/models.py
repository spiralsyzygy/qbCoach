# qb_engine/models.py

from dataclasses import dataclass, field
from typing import List, Optional, Set


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
    effect_id: Optional[str] = None
    effect_description: Optional[str] = None  # mirror of DB text for human readability


@dataclass
class CardTriggerState:
    """Tracks per-card one-time trigger firings and thresholds."""

    first_enhanced_fired: bool = False
    first_enfeebled_fired: bool = False
    power_thresholds_fired: Set[int] = field(default_factory=set)


@dataclass
class SpawnContext:
    """Metadata for spawned tokens."""

    replaced_pawns: int = 0

    def __str__(self) -> str:
        """
        Simplified human-readable representation.
        """
        return f"<Card {self.id} {self.name} (cost={self.cost}, power={self.power})>"
