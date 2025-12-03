# qb_engine/board_state.py

from dataclasses import dataclass, field
from typing import Optional, List
from qb_engine.models import Card


# Mapping from human lane names to indices
LANE_NAME_TO_INDEX = {
    "TOP": 0,
    "MID": 1,
    "BOT": 2,
}


@dataclass
class Tile:
    """
    Represents a single square (tile) on the 3x5 Queen's Blood board.

    Attributes:
    - owner: "Y", "E", or "N"
      (You, Enemy, Neutral)
    - rank: int indicating ownership strength (0, 1, 2, 3)
    - card_id: optional string linking to a Card.id if a card is occupying this tile
    """

    owner: str         # "Y", "E", or "N"
    rank: int          # e.g. 1, 2, 3, or 0 for neutral
    card_id: Optional[str] = None

    def __str__(self) -> str:
        """
        Human-readable representation for debugging and printing.
        """
        if self.card_id:
            return f"[{self.owner}{self.rank}:{self.card_id}]"
        else:
            return f"[{self.owner}{self.rank}]"


@dataclass
class BoardState:
    """
    Represents the entire 3x5 Queen's Blood board with row-major tiles.

       1      2      3      4      5
    T [Y1]  [N0]   [N0]   [N0]   [E1]
    M [Y1]  [N0]   [N0]   [N0]   [E1]
    B [Y1]  [N0]   [N0]   [N0]   [E1]
    """

    tiles: List[List[Tile]] = field(default_factory=list)

    @staticmethod
    def create_initial_board() -> "BoardState":
        """
        Create the standard starting board:
        - Left column: YOUR tiles, rank 1
        - Right column: ENEMY tiles, rank 1
        - Middle columns: neutral, rank 0
        """
        grid: List[List[Tile]] = []

        for _ in range(3):  # rows: TOP, MID, BOT
            row: List[Tile] = []
            for col in range(5):  # columns: 0..4 (1..5 to the player)
                if col == 0:
                    # Left side: your tiles
                    row.append(Tile(owner="Y", rank=1))
                elif col == 4:
                    # Right side: enemy tiles
                    row.append(Tile(owner="E", rank=1))
                else:
                    # Middle tiles: neutral, rank 0
                    row.append(Tile(owner="N", rank=0))
            grid.append(row)

        return BoardState(tiles=grid)

    def print_board(self) -> None:
        """
        Pretty-print the board as rows of tiles.
        """
        for row in self.tiles:
            print("  ".join(str(tile) for tile in row))

    # --- helpers for accessing tiles ---

    def tile_at(self, lane_index: int, col_index: int) -> Tile:
        """
        Access a tile using numeric indices (0-based).
        lane_index: 0=TOP, 1=MID, 2=BOT
        col_index:  0..4  (1..5 to the player)
        """
        return self.tiles[lane_index][col_index]

    def tile_at_name(self, lane_name: str, col_number: int) -> Tile:
        """
        Access a tile using human-readable coordinates like ("TOP", 1).
        """
        lane_index = LANE_NAME_TO_INDEX[lane_name.upper()]
        col_index = col_number - 1  # columns: 1..5 for humans → 0..4 in the list
        return self.tile_at(lane_index, col_index)

    # --- placing cards ---

    def place_card(self, lane_name: str, col_number: int, card: Card) -> None:
        """
        Place a card on the given tile, assuming legality has already been checked.
        """
        tile = self.tile_at_name(lane_name, col_number)
        tile.card_id = card.id
