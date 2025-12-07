from __future__ import annotations

"""
Lightweight helpers for inspecting effect definitions and current board effect state.

Usage:
    python -m qb_engine.debug_effects              # list all cards with effect_id
    python -m qb_engine.debug_effects --card 027   # filter by card id substring
    python -m qb_engine.debug_effects --effect mindflayer
"""

import argparse
from pathlib import Path
from typing import Iterable

from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine


def _iter_cards_with_effects(hydrator: CardHydrator, effect_engine: EffectEngine):
    for card_id in hydrator.index.keys():
        card = hydrator.get_card(card_id)
        if not getattr(card, "effect_id", None):
            continue
        effect_def = effect_engine.get_effect_for_card(card)
        yield card, effect_def


def main() -> None:
    parser = argparse.ArgumentParser(description="List cards with effects.")
    parser.add_argument("--card", help="Filter by card id substring", default=None)
    parser.add_argument("--effect", help="Filter by effect_id substring", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / "data" / "qb_DB_Complete_v2.json"
    reg_path = repo_root / "data" / "qb_effects_v1.1.json"

    hydrator = CardHydrator(str(db_path))
    engine = EffectEngine(reg_path, hydrator)

    def _matches(text: str | None, needle: str | None) -> bool:
        if needle is None:
            return True
        return needle.lower() in (text or "").lower()

    for card, effect_def in _iter_cards_with_effects(hydrator, engine):
        if not _matches(card.id, args.card):
            continue
        if not _matches(card.effect_id, args.effect):
            continue
        trigger = effect_def.trigger if effect_def else "?"
        desc = effect_def.description if effect_def else ""
        print(f"{card.id}: {card.name} | effect_id={card.effect_id} | trigger={trigger} | {desc}")


if __name__ == "__main__":
    main()
