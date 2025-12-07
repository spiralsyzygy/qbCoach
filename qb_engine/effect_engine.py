# qb_engine/effect_engine.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_aura import EffectAura
from qb_engine.models import Card, CardTriggerState, SpawnContext
from qb_engine.scoring import LaneScore

Trigger = str
Scope = str


@dataclass
class EffectOp:
    """A single operation from the effect registry."""

    type: str
    stat: Optional[str] = None
    amount: Optional[int] = None
    apply_to: Optional[str] = None
    per: Optional[str] = None
    amount_per: Optional[int] = None
    card_ids: Optional[List[str]] = None
    adjustment: Optional[str] = None
    mode: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    raw: Dict[str, Any] | None = None


@dataclass
class EffectDef:
    """Structured definition of a card effect loaded from qb_effects_v1.x.json."""

    id: str
    description: str
    trigger: str
    scope: str
    operations: List[EffectOp]


class EffectEngine:
    """
    Deterministic effect engine.

    Responsibilities:
      - Load structured effect definitions from qb_effects_v1.x.json.
      - Given a BoardState and a tile (lane, col), compute the card's
        effective power by applying all relevant while_in_play effects.
    """

    def __init__(self, registry_path: Path, card_hydrator: CardHydrator) -> None:
        self._card_hydrator = card_hydrator
        self._effects: Dict[str, EffectDef] = self._load_registry(registry_path)
        self._debug = False

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
                    stat=op_data.get("stat"),
                    amount=int(op_data["amount"]) if "amount" in op_data else None,
                    apply_to=op_data.get("apply_to"),
                    per=op_data.get("per"),
                    amount_per=op_data.get("amount_per"),
                    card_ids=op_data.get("card_ids"),
                    adjustment=op_data.get("adjustment"),
                    mode=op_data.get("mode"),
                    conditions=op_data.get("conditions"),
                    raw=op_data,
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

    def set_debug(self, enabled: bool) -> None:
        """Toggle debug logging for effect resolution."""

        self._debug = enabled

    # --------------------------------------------------------------------- #
    # Scope resolution (global/lane)
    # --------------------------------------------------------------------- #

    def resolve_scope(
        self,
        scope: str,
        acting_side: Optional[str],
        source_pos: Optional[Tuple[int, int]],
        board: BoardState,
        lane_context: Optional[int] = None,
    ) -> List[Tuple[int, int, Card]]:
        """
        Resolve scope to card locations.

        Returns list of (lane, col, card) tuples. For lane-scoped lookups,
        lane_context takes precedence over source_pos.
        """
        results: List[Tuple[int, int, Card]] = []
        lane_idx = lane_context
        if lane_idx is None and source_pos is not None:
            lane_idx = source_pos[0]

        for r_lane, row in enumerate(board.tiles):
            for r_col, tile in enumerate(row):
                if tile.card_id is None:
                    continue
                card = self._card_hydrator.get_card(tile.card_id)
                side = board.get_card_side(tile.card_id)

                if scope == "all_cards_global":
                    results.append((r_lane, r_col, card))
                elif scope == "allies_global" and side == acting_side:
                    results.append((r_lane, r_col, card))
                elif (
                    scope == "enemies_global"
                    and side is not None
                    and acting_side is not None
                    and side != acting_side
                ):
                    results.append((r_lane, r_col, card))
                elif scope in {"all_cards_in_lane", "allies_in_lane", "enemies_in_lane"}:
                    if lane_idx is not None and r_lane != lane_idx:
                        continue
                    if scope == "all_cards_in_lane":
                        results.append((r_lane, r_col, card))
                    elif scope == "allies_in_lane" and side == acting_side:
                        results.append((r_lane, r_col, card))
                    elif (
                        scope == "enemies_in_lane"
                        and side is not None
                        and acting_side is not None
                        and side != acting_side
                    ):
                        results.append((r_lane, r_col, card))
        return results

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
        tile_state = self._get_tile_state(board, lane, col)

        persistent_delta = tile_state.power_delta + tile_state.scale_delta

        direct_delta = 0
        direct_ops = board.direct_effects.get((lane, col), [])
        for op in direct_ops:
            if op.type == "modify_power" and op.stat == "power" and op.amount is not None:
                direct_delta += op.amount

        # Gather all effect definitions that apply to this tile/card (while_in_play)
        effect_defs = self._effects_applying_to_tile(board, lane, col, card)

        aura_modify_delta = 0
        snapshot_scale_delta = 0

        if self._debug:
            self._debug_log(
                f"Tile ({lane}, {col}) base_power={base_power}"
                f" applicable_effects={[e.id for e in effect_defs]}"
            )

        for effect_def in effect_defs:
            for op in effect_def.operations:
                if op.type == "modify_power" and op.stat == "power" and op.amount is not None:
                    aura_modify_delta += op.amount
                elif op.type == "modify_power_scale" and op.amount_per is not None:
                    snapshot_scale_delta += self._compute_snapshot_scale_delta(
                        board, card, effect_def, op
                    )

        return base_power + persistent_delta + direct_delta + aura_modify_delta + snapshot_scale_delta

    def apply_score_modifiers(
        self,
        board: BoardState,
        lane_scores: List[LaneScore],
    ) -> None:
        """
        Apply score_bonus effects for lane-win bonuses and lane_min_transfer.
        """
        for lane_score in lane_scores:
            winner = lane_score.winner
            if winner is None:
                continue

            lane_idx = lane_score.lane_index

            # Lane-win flat bonuses
            for col_idx, tile in enumerate(board.tiles[lane_idx]):
                if tile.card_id is None:
                    continue
                if board.get_card_side(tile.card_id) != winner:
                    continue
                card = self._card_hydrator.get_card(tile.card_id)
                effect_def = self.get_effect_for_card(card)
                if effect_def is None or effect_def.trigger != "on_lane_win":
                    continue
                for op in effect_def.operations:
                    if op.type == "score_bonus" and op.amount is not None:
                        lane_score.lane_points += op.amount

            # lane_min_transfer
            lower = min(lane_score.power_you, lane_score.power_enemy)
            if lower <= 0:
                continue

            transfer_count = 0
            for col_idx, tile in enumerate(board.tiles[lane_idx]):
                if tile.card_id is None:
                    continue
                if board.get_card_side(tile.card_id) != winner:
                    continue
                card = self._card_hydrator.get_card(tile.card_id)
                effect_def = self.get_effect_for_card(card)
                if effect_def is None or effect_def.trigger != "on_round_end":
                    continue
                for op in effect_def.operations:
                    if op.type == "score_bonus" and op.mode == "lane_min_transfer":
                        transfer_count += 1
            if transfer_count:
                lane_score.lane_points += lower * transfer_count

    def apply_on_play_effects(
        self,
        board: BoardState,
        lane: int,
        col: int,
        card: Card,
        replaced_ally_power: int = 0,
    ) -> None:
        """
        Apply any on_play effects from `card` to currently occupied projection targets.

        Supported ops:
          - modify_power (direct, one-time)
          - destroy_cards (remove occupants in scope)
          - modify_tile_ranks (apply rank delta to target tile)
          - spawn_token (spawn to board)
          - replace_ally follow-ups (raise/lower by replaced power)
          - expand_positions
        """
        effect_def = self.get_effect_for_card(card)
        if effect_def is None or effect_def.trigger != "on_play":
            return

        # Certain on_play effects are handled upstream (e.g., supercharged P tiles).
        if effect_def.id in {
            "on_play_raise_positions_rank_2",
            "on_play_raise_positions_rank_3",
        }:
            return

        self._apply_effect_operations(
            board,
            card,
            effect_def,
            lane,
            col,
            record_direct=True,
            replaced_ally_power=replaced_ally_power,
        )

    def handle_card_played(
        self,
        board: BoardState,
        lane: int,
        col: int,
        card: Card,
    ) -> None:
        """
        Apply on_card_played scaling watchers (event-based modify_power_scale).
        """
        # For every card on board with trigger on_card_played, evaluate per and bump scale_delta.
        for (c_lane, c_col, effect_card, effect_def) in self._iter_effect_cards(board):
            if effect_def.trigger != "on_card_played":
                continue
            per = None
            for op in effect_def.operations:
                if op.type == "modify_power_scale":
                    per = op.per
                    amount_per = op.amount_per or 0
                    if self._played_event_matches(per, board, effect_card, card):
                        self._increment_scale_delta(board, c_lane, c_col, amount_per, effect_card)
                        self._check_power_thresholds(board, c_lane, c_col, effect_card)

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    def _get_tile_state(self, board: BoardState, lane: int, col: int):
        return board.tile_at(lane, col)

    def _apply_effect_operations(
        self,
        board: BoardState,
        source_card: Card,
        effect_def: EffectDef,
        source_lane: int,
        source_col: int,
        record_direct: bool = False,
        replaced_ally_power: int = 0,
    ) -> None:
        """
        Apply operations in effect_def to projection targets from source_card's position.
        """
        from qb_engine.projection import compute_projection_targets, compute_projection_targets_for_enemy

        source_side = board.get_card_side(source_card.id)
        if source_side == "E":
            proj = compute_projection_targets_for_enemy(source_lane, source_col, source_card)
        else:
            proj = compute_projection_targets(source_lane, source_col, source_card)

        to_destroy: List[Tuple[int, int]] = []

        for t_lane, t_col, kind in proj.targets:
            if kind not in ("P", "E", "X"):
                continue

            tile = board.tile_at(t_lane, t_col)
            target_card = self._card_hydrator.get_card(tile.card_id) if tile.card_id else None

            for op in effect_def.operations:
                if op.type == "modify_power" and op.stat == "power" and op.amount is not None:
                    if target_card is not None and self._scope_matches(
                        effect_def.scope,
                        board,
                        t_lane,
                        t_col,
                        aura=None,
                        target_card=target_card,
                        source_card=source_card,
                        source_pos=(source_lane, source_col),
                    ):
                        # Conditional application: check replaced_pawns if provided
                        cond = op.conditions or {}
                        if "replaced_pawns" in cond:
                            ctx = board.tile_at(t_lane, t_col).spawn_context
                            if ctx is None or ctx.replaced_pawns != cond["replaced_pawns"]:
                                continue
                        if record_direct:
                            board.add_direct_effect(t_lane, t_col, op)
                        else:
                            self._apply_modify_power(board, t_lane, t_col, target_card, op.amount, source_card)
                elif op.type == "destroy_cards":
                    if target_card is not None and self._scope_matches(
                        effect_def.scope,
                        board,
                        t_lane,
                        t_col,
                        aura=None,
                        target_card=target_card,
                        source_card=source_card,
                        source_pos=(source_lane, source_col),
                    ):
                        to_destroy.append((t_lane, t_col))
                elif op.type == "modify_tile_ranks" and op.amount is not None:
                    target_tile = board.tile_at(t_lane, t_col)
                    target_tile.rank = max(0, min(3, target_tile.rank + op.amount))
                elif op.type == "spawn_token":
                    token_id = op.raw.get("token_id") if op.raw else None
                    apply_to = op.raw.get("apply_to") if op.raw else None
                    per_pawns = bool(op.raw.get("per_pawns")) if op.raw else False
                    self._spawn_tokens_to_board(board, source_card, token_id, apply_to, per_pawns)
                elif op.type == "replace_ally":
                    # follow-up using replaced_ally_power
                    if op.mode in ("lower", "raise") and op.adjustment == "replaced_ally_power":
                        amount = replaced_ally_power if op.mode == "raise" else -replaced_ally_power
                        if target_card is not None and self._scope_matches(
                            effect_def.scope,
                            board,
                            t_lane,
                            t_col,
                            aura=None,
                            target_card=target_card,
                            source_card=source_card,
                            source_pos=(source_lane, source_col),
                        ):
                            self._apply_modify_power(board, t_lane, t_col, target_card, amount, source_card)
                elif op.type == "expand_positions":
                    self._apply_expand_positions(board, source_card, source_lane, source_col)

        if to_destroy:
            self._destroy_cards(board, to_destroy)

    def _apply_modify_power(
        self,
        board: BoardState,
        lane: int,
        col: int,
        target_card: Card,
        amount: int,
        source_card: Optional[Card] = None,
    ) -> None:
        """Apply modify_power to a card, updating power_delta and firing triggers."""
        tile = board.tile_at(lane, col)
        old_delta = tile.power_delta
        old_power = self.compute_effective_power(board, lane, col)

        tile.power_delta += amount

        # on_enfeebled: every negative modify_power
        if amount < 0:
            self._fire_self_trigger("on_enfeebled", board, lane, col, target_card)

        # first_enhanced / first_enfeebled based on sign change
        trigger_state = tile.trigger_state
        if trigger_state is None:
            trigger_state = CardTriggerState()
            tile.trigger_state = trigger_state

        if old_delta <= 0 < tile.power_delta and not trigger_state.first_enhanced_fired:
            self._fire_self_trigger("on_first_enhanced", board, lane, col, target_card)
            trigger_state.first_enhanced_fired = True
        if old_delta >= 0 > tile.power_delta and not trigger_state.first_enfeebled_fired:
            self._fire_self_trigger("on_first_enfeebled", board, lane, col, target_card)
            trigger_state.first_enfeebled_fired = True

        # Threshold check
        self._check_power_thresholds(board, lane, col, target_card, old_power=old_power)

    def _fire_self_trigger(
        self,
        trigger: str,
        board: BoardState,
        lane: int,
        col: int,
        card: Card,
    ) -> None:
        effect_def = self.get_effect_for_card(card)
        if effect_def is None or effect_def.trigger != trigger:
            return
        self._apply_effect_operations(board, card, effect_def, lane, col, record_direct=False)

    def _compute_snapshot_scale_delta(
        self,
        board: BoardState,
        card: Card,
        effect_def: EffectDef,
        op: EffectOp,
    ) -> int:
        per = op.per
        amount_per = op.amount_per or 0
        if per is None:
            return 0

        source_side = board.get_card_side(card.id)
        count = 0
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id is None:
                    continue
                target_side = board.get_card_side(tile.card_id)
                target_card = self._card_hydrator.get_card(tile.card_id)
                delta = self._classification_delta(board, lane_idx, col_idx, target_card)
                enhanced = delta > 0
                enfeebled = delta < 0

                if per == "enhanced_all" and enhanced:
                    count += 1
                elif per == "enhanced_ally" and enhanced and target_side == source_side:
                    count += 1
                elif per == "enhanced_enemy" and enhanced and target_side != source_side and target_side is not None:
                    count += 1
                elif per == "enhanced_or_enfeebled_all" and delta != 0:
                    count += 1
                elif per == "enfeebled_all" and enfeebled:
                    count += 1
                elif per == "enfeebled_ally" and enfeebled and target_side == source_side:
                    count += 1
                elif per == "enfeebled_enemy" and enfeebled and target_side != source_side and target_side is not None:
                    count += 1
        return amount_per * count

    def _classification_delta(self, board: BoardState, lane: int, col: int, card: Card) -> int:
        tile = board.tile_at(lane, col)
        persistent = tile.power_delta + tile.scale_delta
        aura_delta = 0
        effect_defs = self._effects_applying_to_tile(board, lane, col, card)
        for eff in effect_defs:
            for op in eff.operations:
                if op.type == "modify_power" and op.stat == "power" and op.amount is not None:
                    aura_delta += op.amount
        # Include own direct modify_power effects on this tile
        direct_ops = board.direct_effects.get((lane, col), [])
        for op in direct_ops:
            if op.type == "modify_power" and op.stat == "power" and op.amount is not None:
                aura_delta += op.amount
        return persistent + aura_delta

    def _increment_scale_delta(
        self,
        board: BoardState,
        lane: int,
        col: int,
        amount: int,
        card: Card,
    ) -> None:
        tile = board.tile_at(lane, col)
        old_power = self.compute_effective_power(board, lane, col)
        tile.scale_delta += amount
        self._check_power_thresholds(board, lane, col, card, old_power=old_power)

    def _played_event_matches(self, per: Optional[str], board: BoardState, effect_card: Card, played_card: Card) -> bool:
        if per is None:
            return False
        effect_side = board.get_card_side(effect_card.id)
        played_side = board.get_card_side(played_card.id)
        if per == "played_all":
            return True
        if per == "played_ally":
            return effect_side == played_side
        if per == "played_enemy":
            return effect_side is not None and played_side is not None and effect_side != played_side
        return False

    def _destroy_cards(self, board: BoardState, positions: List[Tuple[int, int]]) -> None:
        # Deduplicate
        unique_positions = list({pos for pos in positions})

        # on_destroy first
        for lane, col in unique_positions:
            tile = board.tile_at(lane, col)
            if tile.card_id is None:
                continue
            card = self._card_hydrator.get_card(tile.card_id)
            effect_def = self.get_effect_for_card(card)
            if effect_def is None or effect_def.trigger != "on_destroy":
                continue
            self._apply_effect_operations(board, card, effect_def, lane, col, record_direct=False)

        # on_card_destroyed watchers
        for lane, col in unique_positions:
            tile = board.tile_at(lane, col)
            if tile.card_id is None:
                continue
            destroyed_card = self._card_hydrator.get_card(tile.card_id)
            destroyed_side = board.get_card_side(tile.card_id)
            for w_lane, w_col, watcher_card, watcher_effect in self._iter_effect_cards(board):
                if watcher_effect.trigger != "on_card_destroyed":
                    continue
                for op in watcher_effect.operations:
                    if op.type != "modify_power_scale" or op.amount_per is None:
                        continue
                    per = op.per
                    if self._destroy_event_matches(per, watcher_card, destroyed_side, board):
                        self._increment_scale_delta(board, w_lane, w_col, op.amount_per, watcher_card)

        # remove cards and associated auras/direct effects
        for lane, col in unique_positions:
            tile = board.tile_at(lane, col)
            if tile.card_id is None:
                continue
            card_id = tile.card_id
            tile.card_id = None
            tile.power_delta = 0
            tile.scale_delta = 0
            tile.trigger_state = None
            tile.spawn_context = None
            # remove auras created by this card
            board.effect_auras = [a for a in board.effect_auras if a.card_id != card_id]
            board.direct_effects.pop((lane, col), None)

    def _destroy_event_matches(
        self,
        per: Optional[str],
        watcher_card: Card,
        destroyed_side: Optional[str],
        board: BoardState,
    ) -> bool:
        watcher_side = board.get_card_side(watcher_card.id)
        if per is None:
            return False
        if per == "destroyed_all":
            return True
        if per == "destroyed_ally":
            return watcher_side == destroyed_side
        if per == "destroyed_enemy":
            return watcher_side is not None and destroyed_side is not None and watcher_side != destroyed_side
        return False

    def _spawn_tokens_to_board(
        self,
        board: BoardState,
        source_card: Card,
        token_id: Optional[str],
        apply_to: Optional[str],
        per_pawns: bool,
    ) -> None:
        if token_id is None or apply_to != "empty_positions":
            return
        source_side = board.get_card_side(source_card.id)
        if source_side is None:
            return
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id is not None:
                    continue
                if tile.owner != source_side or tile.rank <= 0:
                    continue
                rank_before = tile.rank
                try:
                    token_card = self._card_hydrator.get_card(token_id)
                except KeyError:
                    continue
                tile.card_id = token_card.id
                tile.origin = "token"
                tile.spawned_by = source_card.id
                tile.spawn_context = SpawnContext(replaced_pawns=rank_before if per_pawns else 0)
                tile.power_delta = 0
                tile.scale_delta = 0
                tile.trigger_state = CardTriggerState()
                # on_spawned trigger on the token itself
                self._fire_self_trigger("on_spawned", board, lane_idx, col_idx, token_card)

    def _apply_expand_positions(
        self,
        board: BoardState,
        source_card: Card,
        source_lane: int,
        source_col: int,
    ) -> None:
        source_side = board.get_card_side(source_card.id)
        if source_side is None:
            return
        offsets = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        for d_lane, d_col in offsets:
            lane = source_lane + d_lane
            col = source_col + d_col
            if not (0 <= lane < len(board.tiles) and 0 <= col < len(board.tiles[0])):
                continue
            tile = board.tile_at(lane, col)
            if tile.owner == "N":
                tile.owner = source_side
                tile.rank = 1
            elif tile.owner == source_side:
                tile.rank = min(tile.rank + 1, 3)
            # enemy tiles untouched

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

            if self._scope_matches(
                effect_def.scope,
                board,
                lane,
                col,
                aura,
                target_card,
                source_pos=(aura.lane_index, aura.col_index),
            ):
                applicable.append(effect_def)

        # 2) Optionally: handle self-targeted effects without an aura in the future.
        #    Include the card's own while_in_play effect (self) if present.
        self_effect = self.get_effect_for_card(target_card)
        if self_effect and self_effect.trigger == "while_in_play":
            applicable.append(self_effect)

        return applicable

    def _iter_effect_cards(self, board: BoardState) -> List[Tuple[int, int, Card, EffectDef]]:
        out: List[Tuple[int, int, Card, EffectDef]] = []
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id is None:
                    continue
                card = self._card_hydrator.get_card(tile.card_id)
                eff = self.get_effect_for_card(card)
                if eff is None:
                    continue
                out.append((lane_idx, col_idx, card, eff))
        return out

    def _check_power_thresholds(
        self,
        board: BoardState,
        lane: int,
        col: int,
        card: Card,
        old_power: Optional[int] = None,
    ) -> None:
        effect_def = self.get_effect_for_card(card)
        if effect_def is None or effect_def.trigger != "on_power_threshold":
            return
        for op in effect_def.operations:
            conditions = op.conditions or {}
            threshold = conditions.get("threshold") if isinstance(conditions, dict) else None
            if not threshold:
                continue
            value = threshold.get("value")
            if value is None:
                continue
            if old_power is None:
                old_power = self.compute_effective_power(board, lane, col)
            new_power = self.compute_effective_power(board, lane, col)
            if old_power < value <= new_power:
                first_only = bool(conditions.get("first_time"))
                trigger_state = board.tile_at(lane, col).trigger_state or CardTriggerState()
                if first_only and value in trigger_state.power_thresholds_fired:
                    continue
                self._apply_effect_operations(board, card, effect_def, lane, col, record_direct=False)
                trigger_state.power_thresholds_fired.add(value)
                board.tile_at(lane, col).trigger_state = trigger_state

    def _scope_matches(
        self,
        scope: str,
        board: BoardState,
        lane: int,
        col: int,
        aura: EffectAura | None,
        target_card: Card,
        source_card: Card | None = None,
        source_pos: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        Determine if the given scope applies to the card at (lane, col),
        given an EffectAura coming from aura.card_id (or a direct source card).
        """
        tile = board.tile_at(lane, col)
        tile_owner = tile.owner  # "Y", "E", or "N"

        # Determine which side the source card belongs to.
        # For now, we infer from the tile that holds the source card.
        source_card_id = None
        if aura is not None:
            source_card_id = aura.card_id
        elif source_card is not None:
            source_card_id = source_card.id

        source_side = board.get_card_side(source_card_id) if source_card_id else None  # "Y" or "E" (or "N"/None if not found)
        if source_pos is None:
            # Fall back to locating the source card on the board if needed.
            if aura is not None:
                source_pos = (aura.lane_index, aura.col_index)
            elif source_card_id:
                found = self._find_card_position(board, source_card_id)
                if found is not None:
                    source_pos = found

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
            return source_card_id is not None and target_card.id == source_card_id

        if scope in {
            "allies_global",
            "enemies_global",
            "all_cards_global",
            "allies_in_lane",
            "enemies_in_lane",
            "all_cards_in_lane",
        }:
            resolved = self.resolve_scope(scope, source_side, source_pos, board)
            return any(l == lane and c == col for (l, c, _) in resolved)

        if scope == "lane_owner":
            # lane_owner is used for scoring-time logic; it does not target cards directly here.
            return False

        return False

    def _find_card_position(self, board: BoardState, card_id: str) -> Optional[Tuple[int, int]]:
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id == card_id:
                    return (lane_idx, col_idx)
        return None

    def _debug_log(self, message: str) -> None:
        """Internal helper for consistent debug logging hooks."""

        # Replace with logging.debug if/when a logger is wired in.
        # print(message)
        _ = message  # satisfy linters when debug printing is disabled

    # ------------------------------------------------------------------ #
    # Debug helpers
    # ------------------------------------------------------------------ #

    def pretty_print_effect_state(self, board: BoardState) -> None:
        """
        Print a readable snapshot of effect-related state for each card on the board.
        Intended for debugging only.
        """
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id is None:
                    continue
                card = self._card_hydrator.get_card(tile.card_id)
                side = board.get_card_side(tile.card_id) or "?"
                eff_power = self.compute_effective_power(board, lane_idx, col_idx)
                classification_delta = self._classification_delta(board, lane_idx, col_idx, card)
                if classification_delta > 0:
                    status = "enhanced"
                elif classification_delta < 0:
                    status = "enfeebled"
                else:
                    status = "neutral"
                eff = self.get_effect_for_card(card)
                effect_label = eff.id if eff else "-"
                print(
                    f"{side} lane {lane_idx} col {col_idx}: "
                    f"{card.name} ({card.id}) base={card.power} "
                    f"power_delta={tile.power_delta} scale_delta={tile.scale_delta} "
                    f"effective={eff_power} status={status} effect_id={effect_label}"
                )
