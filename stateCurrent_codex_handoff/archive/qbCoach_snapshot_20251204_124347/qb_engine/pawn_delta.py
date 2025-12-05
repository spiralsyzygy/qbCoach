# qb_engine/pawn_delta.py

from dataclasses import dataclass


@dataclass
class PawnDelta:
    """
    Represents a single pawn influence change on a tile,
    caused by a particular card.

    delta:
      +1 for a pawn contributed by YOU
      -1 for a pawn contributed by ENEMY
    """
    lane_index: int   # 0=TOP, 1=MID, 2=BOT
    col_index: int    # 0..4 for columns 1..5
    card_id: str
    delta: int
