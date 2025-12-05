# qb_engine/effect_engine.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.models import Card


Trigger = Literal["while_in_play", "on_play", "on_destroy"]

Scope = Literal[
    "self",
    "allies_on_affected_tiles",
    "enemies_on_affected_tiles",
    "all_cards_on_affected_tiles",
    "allies_in_lane",
    "enemies_in_lane",
    "all_cards_in_lane",
]

EffectOpType = Literal["modify_power"]


@dataclass
class EffectOp:
    type: EffectOpType
    stat: Literal["power"]
    amount: int


@dataclass
class EffectDef:
    id: str
    description: str
    trigger: Trigger
    scope: Scope
    operations: List[EffectOp]


class EffectEngine:
    """
    Deterministic effect engine.

    Responsibilities:
      - Load structured effect definitions from qb_effects_v1.json.
      - Given a BoardState and a tile (lane, col), compute the card's
        effective power by applying all relevant while_in_play effects.
    """

    def __init__(self, registry_path: Path, card_hydrator: CardHydrator) -> None:
        self._card_hydrator = card_hydrator
        self._effects: Dict[str, EffectDef] = self._load_registry(registry_path)

    # --------------------------------------------------------------------- #
    # Registry loading
    # --------------------------------------------------------------------- #

    def _load_registry(self, registry_path: Path) -> Dict[str, EffectDef]:
        import json

        with registry_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        effects: Dict[str, EffectDef] = {}
        for effect_id, data in raw.items():
            if effect_id == "_meta":
                continue

            description = data.get("description", "")
            trigger: Trigger = data["trigger"]
            scope: Scope = data["scope"]

            ops: List[EffectOp] = []
            for op_data in data.get("operations", []):
                op = EffectOp(
                    type=op_data["type"],
                    stat=op_data["stat"],
                    amount=int(op_data["amount"]),
                )
                ops.append(op)

            effects[effect_id] = EffectDef(
                id=effect_id,
                description=description,
                trigger=trigger,
                scope=scope,
                operations=ops,
            )

        return effects

    def get_effect_for_card(self, card: Card) -> Optional[EffectDef]:
        """
        Returns the EffectDef for a given card, if it has effect_id and
        that effect_id exists in the registry.
        """
        effect_id = getattr(card, "effect_id", None)
        if not effect_id:
            return None
        return self._effects.get(effect_id)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def compute_effective_power(
        self,
        board: BoardState,
        lane: int,
        col: int,
    ) -> int:
        """
        Returns the effective power for the card (if any) currently on (lane, col),
        after applying all relevant while_in_play effects from EffectAuras.

        For v0.1, we:
          - Ignore on_play / on_destroy triggers here.
          - Focus only on while_in_play effects (e.g. Mindflayer / 027).
        """
        tile = board.tile_at(lane, col)
        if tile.card_id is None:
            # No card on this tile; effective power is not meaningful.
            return 0

        card = self._card_hydrator.get_card(tile.card_id)
        base_power = card.power

        # Gather all effect definitions that apply to this tile/card
        effect_defs = self._effects_applying_to_tile(board, lane, col, card)

        delta_power = 0
        for effect_def in effect_defs:
            for op in effect_def.operations:
                if op.type == "modify_power" and op.stat == "power":
                    delta_power += op.amount

        return base_power + delta_power

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    def _effects_applying_to_tile(
        self,
        board: BoardState,
        lane: int,
        col: int,
        target_card: Card,
    ) -> List[EffectDef]:
        """
        Find all EffectDef instances whose auras + scope/trigger conditions
        match the card currently at (lane, col).

        v0.1: only while_in_play triggers are considered.
        """
        applicable: List[EffectDef] = []

        # 1) Look at all auras present on this tile
        auras = board.auras_at(lane, col)
        for aura in auras:
            source_card = self._card_hydrator.get_card(aura.card_id)
            effect_def = self.get_effect_for_card(source_card)
            if effect_def is None:
                continue

            # v0.1: only apply while_in_play effects in this pipeline
            if effect_def.trigger != "while_in_play":
                continue

            if self._scope_matches(effect_def.scope, board, lane, col, aura, target_card):
                applicable.append(effect_def)

        # 2) Optionally: handle self-targeted effects without an aura in the future.
        #    For now we assume all continuous effects are delivered via auras.

        return applicable

    def _scope_matches(
        self,
        scope: Scope,
        board: BoardState,
        lane: int,
        col: int,
        aura,
        target_card: Card,
    ) -> bool:
        """
        Determine if the given scope applies to the card at (lane, col),
        given an EffectAura coming from aura.card_id.
        """
        tile = board.tile_at(lane, col)
        tile_owner = tile.owner  # "Y", "E", or "N"

        # Determine which side the source card belongs to.
        # For now, we infer from the tile that holds the source card.
        source_side = board.get_card_side(aura.card_id)  # "Y" or "E" (or "N"/None if not found)

        if scope == "all_cards_on_affected_tiles":
            return True

        if scope == "allies_on_affected_tiles":
            # Allies = cards on tiles owned by the same side as the source
            return tile_owner == source_side

        if scope == "enemies_on_affected_tiles":
            # Enemies = cards on tiles owned by the opposite side (non-neutral)
            return tile_owner != "N" and tile_owner != source_side

        if scope == "self":
            # The effect only applies to the source card itself
            return target_card.id == aura.card_id

        # Lane-wide scopes are reserved for future work (when rules require).
        if scope in {"allies_in_lane", "enemies_in_lane", "all_cards_in_lane"}:
            # TODO: implement when lane-wide effects are needed.
            return False

        return False
