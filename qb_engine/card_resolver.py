from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Dict, List

from qb_engine.card_hydrator import CardHydrator
from qb_engine.models import Card


class CardResolveError(Exception):
    """Raised when a card identifier cannot be resolved or is ambiguous."""


def _strip_quotes(raw: str) -> str:
    raw = raw.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1].strip()
    return raw


class _CardResolver:
    def __init__(self, hydrator: CardHydrator | None = None) -> None:
        self._hydrator = hydrator or CardHydrator()
        self.id_index: Dict[str, Card] = {}
        self.lower_name_index: Dict[str, Card] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for entry in self._hydrator.db:
            if not isinstance(entry, dict) or "id" not in entry or "name" not in entry:
                continue
            cid = entry["id"]
            card = self._hydrator.get_card(cid)
            self.id_index[cid] = card
            self.lower_name_index[card.name.lower()] = card

    def resolve(self, raw: str) -> Card:
        token = _strip_quotes(raw)
        if not token:
            raise CardResolveError("Empty card identifier.")

        # Direct id match
        if token in self.id_index:
            return self.id_index[token]

        # Case-insensitive name match
        lower = token.lower()
        if lower in self.lower_name_index:
            return self.lower_name_index[lower]

        # Suggest close matches (names only)
        candidates = get_close_matches(lower, list(self.lower_name_index.keys()), n=3, cutoff=0.6)
        hint = f" Unknown card '{raw}'."
        if candidates:
            pretty = ", ".join(self.lower_name_index[c].name for c in candidates)
            hint += f" Did you mean: {pretty}?"
        raise CardResolveError(hint.strip())


_DEFAULT_RESOLVER = _CardResolver()


def resolve_card_identifier(raw: str) -> Card:
    """
    Resolve a raw user token to a Card using the canonical DB.

    Accepts:
      - exact id ("020")
      - exact official name ("Archdragon")
      - case-insensitive name ("archdragon")
    Strips whitespace and quotes.
    """
    return _DEFAULT_RESOLVER.resolve(raw)


_QUANTITY_RE = re.compile(r"^(?P<name>.+?)[x×]\s*(?P<count>\d+)$", re.IGNORECASE)


def parse_card_list(raw: str) -> List[Card]:
    """
    Parse a comma- or space-separated list of identifiers into Cards.
    Supports simple quantity syntax in comma-delimited form, e.g. "Queen Bee x2".
    """
    tokens: List[str] = []
    if "," in raw:
        tokens = [t.strip() for t in raw.split(",") if t.strip()]
    else:
        tokens = [t.strip() for t in raw.split() if t.strip()]

    cards: List[Card] = []
    for tok in tokens:
        tok_clean = _strip_quotes(tok)
        qty = 1
        m = _QUANTITY_RE.match(tok_clean)
        if m:
            tok_clean = m.group("name").strip()
            qty = int(m.group("count"))
        card = resolve_card_identifier(tok_clean)
        cards.extend([card] * qty)
    return cards


def resolve_cards_from_tokens(tokens: List[str]) -> List[Card]:
    """Resolve a list of raw tokens to Cards."""
    return [resolve_card_identifier(tok) for tok in tokens]
