from __future__ import annotations

import copy
from typing import List

from qb_engine.card_hydrator import CardHydrator
from qb_engine.models import Card


class Hand:
    """
    Hand of hydrated Card objects with deterministic ordering and helpers to
    add/remove/sync from card IDs.
    """

    def __init__(self, hydrator: CardHydrator):
        self._hydrator = hydrator
        self.cards: List[Card] = []

    def from_card_ids(self, ids: List[str]) -> None:
        """Replace hand contents with hydrated cards for the provided IDs."""
        self.cards = [self._hydrator.get_card(cid) for cid in ids]

    def add_card(self, card_id: str) -> None:
        """Hydrate and append a card to the end of the hand."""
        self.cards.append(self._hydrator.get_card(card_id))

    def remove_index(self, idx: int) -> Card:
        """Remove and return the card at the given index."""
        if idx < 0 or idx >= len(self.cards):
            raise IndexError("Hand index out of range.")
        return self.cards.pop(idx)

    def as_card_ids(self) -> List[str]:
        """Return the list of card IDs in hand order."""
        return [card.id for card in self.cards]

    def sync_from_ids(self, ids: List[str]) -> None:
        """Overwrite the hand to exactly match the provided card IDs."""
        self.from_card_ids(ids)

    def clone(self) -> "Hand":
        clone = Hand(self._hydrator)
        clone.cards = [copy.deepcopy(card) for card in self.cards]
        return clone

    def __deepcopy__(self, memo):
        clone = self.clone()
        memo[id(self)] = clone
        return clone

