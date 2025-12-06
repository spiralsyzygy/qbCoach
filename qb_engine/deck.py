from __future__ import annotations

import copy
import random
from typing import List, Optional


class Deck:
    """
    Deterministic deck of card IDs with seeded shuffle/draw and mulligan support.
    No hydration occurs here; cards are represented by their IDs only.
    """

    def __init__(self, card_ids: List[str], seed: Optional[int] = None):
        if len(card_ids) != 15:
            raise ValueError("Deck must contain exactly 15 card IDs.")

        self._seed = 0 if seed is None else seed
        self._rng = random.Random(self._seed)
        self._original_order = list(card_ids)
        self._order: List[str] = []
        self._draw_pointer = 0

        self.shuffle()

    def shuffle(self) -> None:
        """Deterministically shuffle the deck using the stored seed."""
        self._order = list(self._original_order)
        self._rng.shuffle(self._order)
        self._draw_pointer = 0

    def draw(self) -> Optional[str]:
        """Draw the next card ID; returns None if deck is exhausted."""
        if self._draw_pointer >= len(self._order):
            return None

        card_id = self._order[self._draw_pointer]
        self._draw_pointer += 1
        return card_id

    def draw_n(self, n: int) -> List[str]:
        """Draw n cards in order."""
        drawn: List[str] = []
        for _ in range(n):
            card = self.draw()
            if card is None:
                break
            drawn.append(card)
        return drawn

    def cards_remaining(self) -> int:
        return len(self._order) - self._draw_pointer

    def mulligan(self, opening_hand_ids: List[str], indices_to_replace: List[int]) -> List[str]:
        """
        Perform a mulligan on an opening hand.

        Steps:
          1. Take cards at indices_to_replace out of the hand.
          2. Return those IDs to the undealt deck pool.
          3. Reshuffle the remaining deck pool deterministically.
          4. Draw replacements for the removed cards.
          5. Return the updated opening hand (order preserved).
        """
        if any(idx < 0 or idx >= len(opening_hand_ids) for idx in indices_to_replace):
            raise IndexError("Mulligan index out of range.")

        replace_set = set(indices_to_replace)
        replaced_cards = [opening_hand_ids[idx] for idx in indices_to_replace]
        kept_cards = [cid for idx, cid in enumerate(opening_hand_ids) if idx not in replace_set]

        # Pool for reshuffle: remaining undealt cards + replaced cards
        remaining_deck = self._order[self._draw_pointer :]
        pool = list(remaining_deck) + replaced_cards

        # Deterministic reshuffle using the same seed
        reshuffler = random.Random(self._seed)
        reshuffler.shuffle(pool)

        self._order = pool
        self._draw_pointer = 0

        replacements = self.draw_n(len(replaced_cards))

        # Build new hand preserving original order
        new_hand = list(opening_hand_ids)
        for idx, card_id in zip(indices_to_replace, replacements):
            new_hand[idx] = card_id

        return new_hand

    def clone(self) -> "Deck":
        """Deep clone including RNG state and draw pointer."""
        clone = Deck(self._original_order, self._seed)
        clone._order = list(self._order)
        clone._draw_pointer = self._draw_pointer
        clone._rng.setstate(self._rng.getstate())
        return clone

    def __deepcopy__(self, memo):
        clone = self.clone()
        memo[id(self)] = clone
        return clone
