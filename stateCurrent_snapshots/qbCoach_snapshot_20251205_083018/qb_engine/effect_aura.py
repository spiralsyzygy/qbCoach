# qb_engine/effect_aura.py

from dataclasses import dataclass


@dataclass
class EffectAura:
    """
    Represents an effect "aura" on a tile caused by a particular card.

    This is where X/E projections land:
      - It exists whether or not the tile is occupied.
      - Any card currently on, or later played onto, this tile is affected.
      - The actual semantics (buff/debuff/destroy/etc.) are defined by the
        source card's effect text and the effect engine, not here.
    """
    lane_index: int   # 0=TOP, 1=MID, 2=BOT
    col_index: int    # 0..4  (columns 1..5)
    card_id: str      # source card
    description: str  # raw effect text from the card (for reference)
