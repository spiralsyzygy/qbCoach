# qb_engine/board_state.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from qb_engine.effect_engine import EffectEngine, EffectOp

from qb_engine.models import Card, CardTriggerState, SpawnContext
from qb_engine.pawn_delta import PawnDelta
from qb_engine.effect_aura import EffectAura


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
    - owner: "Y", "E", or "N"  (You, Enemy, Neutral)
    - rank:  visible rank (0..3)
    - card_id: optional Card.id if occupied
    - base_influence: starting control value
        +1 = your side
         0 = neutral
        -1 = enemy side
    """

    owner: str         # "Y", "E", or "N"
    rank: int          # visible rank (0..3)
    card_id: Optional[str] = None
    base_influence: int = 0
    origin: Optional[str] = None  # e.g., "deck", "token", "effect"
    spawned_by: Optional[str] = None  # source card id if token/effect placed
    power_delta: int = 0  # net modify_power applied
    scale_delta: int = 0  # accumulated event-based scaling
    trigger_state: Optional[CardTriggerState] = None
    spawn_context: Optional[SpawnContext] = None

    def __str__(self) -> str:
        """
        Display rules (aligned with docs):
          - Occupied tile: [CARD_ID]
          - Empty tile:    [Y1] / [E2] / [N0], etc.
        """
        if self.card_id:
            return f"[{self.card_id}]"
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
    pawn_deltas: List[PawnDelta] = field(default_factory=list)
    effect_auras: List[EffectAura] = field(default_factory=list)
    direct_effects: Dict[Tuple[int, int], List["EffectOp"]] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Construction & visualization
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_initial_board() -> "BoardState":
        """
        Create the standard starting board:
        - Left column: YOUR tiles, rank 1, base_influence = +1
        - Right column: ENEMY tiles, rank 1, base_influence = -1
        - Middle columns: neutral, rank 0, base_influence = 0
        """
        grid: List[List[Tile]] = []

        for _ in range(3):  # rows: TOP, MID, BOT
            row: List[Tile] = []
            for col in range(5):  # 0..4 (1..5 to the player)
                if col == 0:
                    # Your side
                    row.append(Tile(owner="Y", rank=1, base_influence=1))
                elif col == 4:
                    # Enemy side
                    row.append(Tile(owner="E", rank=1, base_influence=-1))
                else:
                    # Neutral tiles
                    row.append(Tile(owner="N", rank=0, base_influence=0))
            grid.append(row)

        return BoardState(tiles=grid)

    def print_board(self) -> None:
        """
        Pretty-print the board as rows of tiles (no ★).
        """
        for row in self.tiles:
            print("  ".join(str(tile) for tile in row))

    def print_board_with_effects(self) -> None:
        """
        Pretty-print the board, overlaying ★ on tiles that have any effect aura.

        Conventions:
          - Empty tile, no aura:      [Y1] / [N0] / [E1]
          - Empty tile, with aura:    [Y1★] / [N0★] / [E1★]
          - Occupied tile, no aura:   [001]
          - Occupied tile, with aura: [001★]
        """
        for lane_index, row in enumerate(self.tiles):
            rendered_row: List[str] = []
            for col_index, tile in enumerate(row):
                base = str(tile)  # [CARD] or [Y1]/[N0]/[E1]
                auras = self.auras_at(lane_index, col_index)
                if auras:
                    if base.endswith("]"):
                        base = base[:-1] + "★]"
                    else:
                        base = base + "★"
                rendered_row.append(base)
            print("  ".join(rendered_row))

    def print_board_with_effects_and_power(self, effect_engine: "EffectEngine") -> None:
        """
        Pretty-print the board including auras and effective power for occupied tiles.

        Conventions:
          - Empty tile, no aura:      [Y1] / [N0] / [E1]
          - Empty tile, with aura:    [Y1★] / [N0★] / [E1★]
          - Occupied tile, no aura:   [CARD_ID:effective_power]
          - Occupied tile, with aura: [CARD_ID:effective_power★]
        """
        for lane_index, row in enumerate(self.tiles):
            rendered_row: List[str] = []
            for col_index, tile in enumerate(row):
                auras = self.auras_at(lane_index, col_index)
                if tile.card_id:
                    power = self.effective_power_at(lane_index, col_index, effect_engine)
                    base = f"[{tile.card_id}:{power}]"
                else:
                    base = str(tile)

                if auras:
                    if base.endswith("]"):
                        base = base[:-1] + "★]"
                    else:
                        base = base + "★"

                rendered_row.append(base)
            print("  ".join(rendered_row))

    # ------------------------------------------------------------------ #
    # Tile access
    # ------------------------------------------------------------------ #

    def tile_at(self, lane_index: int, col_index: int) -> Tile:
        return self.tiles[lane_index][col_index]

    def tile_at_name(self, lane_name: str, col_number: int) -> Tile:
        lane_index = LANE_NAME_TO_INDEX[lane_name.upper()]
        col_index = col_number - 1
        return self.tile_at(lane_index, col_index)

    def describe_tile(self, lane_index: int, col_index: int) -> Dict[str, object]:
        """
        Canonical tile descriptor used by legality/rendering paths.
        """
        tile = self.tile_at(lane_index, col_index)
        return {
            "lane": lane_index,
            "col": col_index,
            "owner": tile.owner,
            "rank": tile.rank,
            "card_id": tile.card_id,
            "has_auras": bool(self.auras_at(lane_index, col_index)),
        }

    # ------------------------------------------------------------------ #
    # Placing cards
    # ------------------------------------------------------------------ #

    def place_card(
        self,
        lane_name: str,
        col_number: int,
        card: Card,
        effect_engine: Optional["EffectEngine"] = None,
    ) -> None:
        lane_index = LANE_NAME_TO_INDEX[lane_name.upper()]
        col_index = col_number - 1

        # Clear any direct effects that belonged to a previous occupant.
        self.direct_effects.pop((lane_index, col_index), None)

        tile = self.tile_at(lane_index, col_index)
        tile.card_id = card.id
        tile.power_delta = 0
        tile.scale_delta = 0
        tile.trigger_state = CardTriggerState()
        tile.spawn_context = None
        # owner/rank are derived from influence; we don't change them here.

        if effect_engine is not None:
            effect_engine.apply_on_play_effects(self, lane_index, col_index, card)

    # ------------------------------------------------------------------ #
    # PawnDelta helpers
    # ------------------------------------------------------------------ #

    def add_pawn_delta_for_you(
        self,
        lane_index: int,
        col_index: int,
        card_id: str,
        amount: int = 1,
    ) -> None:
        """
        Log a pawn influence change for YOU at a tile.
        Positive amount increases your influence.
        """
        self.pawn_deltas.append(
            PawnDelta(
                lane_index=lane_index,
                col_index=col_index,
                card_id=card_id,
                delta=amount,
            )
        )

    def add_pawn_delta_for_enemy(
        self,
        lane_index: int,
        col_index: int,
        card_id: str,
        amount: int = 1,
    ) -> None:
        """
        Log a pawn influence change for the ENEMY at a tile.
        Negative amount decreases Y influence / increases E influence.
        """
        self.pawn_deltas.append(
            PawnDelta(
                lane_index=lane_index,
                col_index=col_index,
                card_id=card_id,
                delta=-amount,
            )
        )

    def recompute_influence_from_deltas(self) -> None:
        """
        Recompute tile owner/rank from:
          base_influence + sum of all PawnDeltas for that tile.

        Mapping:
          influence > 0  -> owner="Y", rank=min(influence, 3)
          influence < 0  -> owner="E", rank=min(-influence, 3)
          influence == 0 -> owner="N", rank=0
        """
        influences: List[List[int]] = [
            [tile.base_influence for tile in row] for row in self.tiles
        ]

        for delta in self.pawn_deltas:
            influences[delta.lane_index][delta.col_index] += delta.delta

        for lane_index, row in enumerate(self.tiles):
            for col_index, tile in enumerate(row):
                influence = influences[lane_index][col_index]
                if influence > 0:
                    tile.owner = "Y"
                    tile.rank = min(influence, 3)
                elif influence < 0:
                    tile.owner = "E"
                    tile.rank = min(-influence, 3)
                else:
                    tile.owner = "N"
                    tile.rank = 0

    # ------------------------------------------------------------------ #
    # Effect aura helpers
    # ------------------------------------------------------------------ #

    def add_effect_aura(
        self,
        lane_index: int,
        col_index: int,
        card_id: str,
        description: str,
    ) -> None:
        """
        Register an effect aura on a tile for a given source card.
        """
        self.effect_auras.append(
            EffectAura(
                lane_index=lane_index,
                col_index=col_index,
                card_id=card_id,
                description=description,
            )
        )

    def auras_at(self, lane_index: int, col_index: int) -> List[EffectAura]:
        """
        Return all effect auras currently affecting a given tile.
        """
        return [
            aura
            for aura in self.effect_auras
            if aura.lane_index == lane_index and aura.col_index == col_index
        ]

    def add_direct_effect(self, lane: int, col: int, op: "EffectOp") -> None:
        """
        Register a direct (one-time) effect operation on the card at (lane, col).
        """
        self.direct_effects.setdefault((lane, col), []).append(op)

    # ------------------------------------------------------------------ #
    # Card-side detection (for effect scopes)
    # ------------------------------------------------------------------ #

    def get_card_side(self, card_id: str) -> str | None:
        """
        Returns:
          "Y" if the card with this id is on a Y-owned tile,
          "E" if on an enemy tile,
          "N" if only found on neutral tiles,
          None if not found on the board.

        If multiple tiles hold the same card_id, we only care about which
        side (Y/E) it belongs to at all.
        """
        found_neutral = False

        num_lanes = len(self.tiles)
        num_cols = len(self.tiles[0]) if num_lanes > 0 else 0

        for lane in range(num_lanes):
            for col in range(num_cols):
                tile = self.tile_at(lane, col)
                if tile.card_id == card_id:
                    if tile.owner == "Y":
                        return "Y"
                    if tile.owner == "E":
                        return "E"
                    found_neutral = True

        if found_neutral:
            return "N"

        return None

    # ------------------------------------------------------------------ #
    # Effective power helper
    # ------------------------------------------------------------------ #

    def effective_power_at(self, lane: int, col: int, effect_engine) -> int:
        """
        Convenience wrapper around EffectEngine.compute_effective_power.
        """
        return effect_engine.compute_effective_power(self, lane, col)
