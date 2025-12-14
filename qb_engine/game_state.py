from __future__ import annotations

import copy
import random
from typing import Literal, Optional

from qb_engine.board_state import BoardState, LANE_NAME_TO_INDEX
from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.hand import Hand
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    apply_effects_for_enemy,
    apply_effects_for_you,
    apply_pawns_for_enemy,
    apply_pawns_for_you,
    compute_projection_targets,
    compute_projection_targets_for_enemy,
)

LANE_INDEX_TO_NAME = {v: k for k, v in LANE_NAME_TO_INDEX.items()}


class GameState:
    """
    Deterministic simulation state machine for Phase C.
    Owns board, decks, hands, turn/side, and seeded RNG.
    """

    def __init__(
        self,
        player_deck: Deck,
        enemy_deck: Deck,
        hydrator: CardHydrator,
        effect_engine: EffectEngine,
        seed: Optional[int] = None,
        board: Optional[BoardState] = None,
        player_hand_ids: Optional[list[str]] = None,
        enemy_hand_ids: Optional[list[str]] = None,
    ):
        self.board = board or BoardState.create_initial_board()
        self.player_deck = player_deck
        self.enemy_deck = enemy_deck
        self.effect_engine = effect_engine
        self.rng = random.Random(0 if seed is None else seed)

        self.player_hand = Hand(hydrator)
        self.enemy_hand = Hand(hydrator)

        # Opening hands: draw 5 if not provided
        if player_hand_ids is not None:
            self.player_hand.from_card_ids(player_hand_ids)
        else:
            self.player_hand.from_card_ids(self.player_deck.draw_n(5))

        if enemy_hand_ids is not None:
            self.enemy_hand.from_card_ids(enemy_hand_ids)
        else:
            self.enemy_hand.from_card_ids(self.enemy_deck.draw_n(5))

        self.turn = 1
        self.side_to_act: Literal["Y", "E"] = "Y"
        self.consecutive_passes: int = 0
        self._mulligan_used = {"Y": False, "E": False}
        # Track per-side turn counts to handle first-turn draw skips.
        self._turns_taken = {"Y": 0, "E": 0}

    # ------------------------------------------------------------------ #
    # Turn mechanics
    # ------------------------------------------------------------------ #

    def draw_start_of_turn(self) -> None:
        """Side to act draws one card; skipped on that side's first turn."""
        if self._turns_taken[self.side_to_act] == 0:
            return
        if self.side_to_act == "Y":
            card_id = self.player_deck.draw()
            if card_id is not None:
                self.player_hand.add_card(card_id)
        else:
            card_id = self.enemy_deck.draw()
            if card_id is not None:
                self.enemy_hand.add_card(card_id)

    def play_card_from_hand(self, side: Literal["Y", "E"], hand_index: int, lane: int, col: int) -> None:
        """
        Play a card from hand onto the board with projections/effects.
        lane/col are zero-based indices.
        """
        if side != self.side_to_act:
            raise ValueError("Side to act mismatch.")

        hand = self.player_hand if side == "Y" else self.enemy_hand

        card = hand.remove_index(hand_index)

        # Legality check (mirrored for enemy)
        tile = self.board.tile_at(lane, col)
        owner_required = "Y" if side == "Y" else "E"
        if tile.card_id is not None or tile.owner != owner_required or tile.rank < card.cost:
            # reuse legality helper for YOU when applicable
            if side == "Y":
                legal = is_legal_placement(self.board, lane, col, card)
            else:
                legal = tile.card_id is None and tile.owner == "E" and tile.rank >= card.cost
            if not legal:
                raise ValueError("Illegal placement for side.")

        lane_name = LANE_INDEX_TO_NAME[lane]
        col_number = col + 1

        # Handle replace_ally pre-destruction
        effect_def = self.effect_engine.get_effect_for_card(card)
        replaced_ally_power = 0
        if effect_def and any(op.type == "replace_ally" for op in effect_def.operations):
            tile = self.board.tile_at(lane, col)
            occupant_id = tile.card_id
            if occupant_id and self.board.get_card_side(occupant_id) == side:
                replaced_ally_power = self.effect_engine.compute_effective_power(self.board, lane, col)
                self.effect_engine._destroy_cards(self.board, [(lane, col)])

        self.board.place_card(lane_name, col_number, card, placed_by=side, effect_engine=self.effect_engine)

        # Event-based scaling on card played
        self.effect_engine.handle_card_played(self.board, lane, col, card)

        if side == "Y":
            proj = compute_projection_targets(lane, col, card)
            apply_pawns_for_you(self.board, proj, card)
            apply_effects_for_you(self.board, proj, card)
        else:
            proj = compute_projection_targets_for_enemy(lane, col, card)
            apply_pawns_for_enemy(self.board, proj, card)
            apply_effects_for_enemy(self.board, proj, card)

        # Ensure influence recompute after projections
        self.board.recompute_influence_from_deltas()
        self.board.validate_invariants()

        # Handle stateful on_play effects (hands/tokens and replace follow-ups)
        self._apply_stateful_on_play_effects(card, side, replaced_ally_power=replaced_ally_power)

        # Any successful play resets pass counter
        self.consecutive_passes = 0

    def apply_enemy_play_from_card_id(self, card_id: str, lane: int, col: int, origin: str = "deck") -> None:
        """
        Apply an enemy card directly to the board by card_id (live coaching sync).
        Bypasses enemy hand/turn, but uses the same projection/effect flow.
        """
        card = self.effect_engine._card_hydrator.get_card(card_id)
        tile = self.board.tile_at(lane, col)

        if tile.card_id is not None or tile.owner != "E" or tile.rank < card.cost:
            raise ValueError("Illegal placement for enemy.")

        lane_name = LANE_INDEX_TO_NAME[lane]
        col_number = col + 1

        effect_def = self.effect_engine.get_effect_for_card(card)
        replaced_ally_power = 0
        if effect_def and any(op.type == "replace_ally" for op in effect_def.operations):
            tile = self.board.tile_at(lane, col)
            occupant_id = tile.card_id
            if occupant_id and self.board.get_card_side(occupant_id) == "E":
                replaced_ally_power = self.effect_engine.compute_effective_power(self.board, lane, col)
                self.effect_engine._destroy_cards(self.board, [(lane, col)])

        self.board.place_card(lane_name, col_number, card, placed_by="E", effect_engine=self.effect_engine)

        # Event-based scaling on card played
        self.effect_engine.handle_card_played(self.board, lane, col, card)

        proj = compute_projection_targets_for_enemy(lane, col, card)
        apply_pawns_for_enemy(self.board, proj, card)
        apply_effects_for_enemy(self.board, proj, card)

        self.board.recompute_influence_from_deltas()
        self.board.validate_invariants()
        self._apply_stateful_on_play_effects(card, "E", replaced_ally_power=replaced_ally_power)
        self.consecutive_passes = 0

    def cleanup(self) -> None:
        """Placeholder for destruction/effect cleanup; currently just recomputes influence."""
        self.board.recompute_influence_from_deltas()
        self.board.validate_invariants()

    def mulligan(self, side: Literal["Y", "E"], indices_to_replace: list[int]) -> None:
        """
        Perform a single mulligan for the given side before their first turn.
        """
        if self._turns_taken[side] > 0:
            raise ValueError("Mulligan allowed only before the side's first turn begins.")
        if self._mulligan_used[side]:
            raise ValueError("Mulligan already used for this side.")

        hand = self.player_hand if side == "Y" else self.enemy_hand
        deck = self.player_deck if side == "Y" else self.enemy_deck

        current_ids = hand.as_card_ids()
        new_ids = deck.mulligan(current_ids, indices_to_replace)
        hand.sync_from_ids(new_ids)
        self._mulligan_used[side] = True

    def suggest_opening_mulligan_indices(self, side: Literal["Y", "E"]) -> list[int]:
        """
        Deterministic placeholder mulligan heuristic.
        Currently mulligans cards with cost >= 4 (expensive openers).
        """
        hand = self.player_hand if side == "Y" else self.enemy_hand
        return [idx for idx, card in enumerate(hand.cards) if card.cost >= 4]

    def apply_opening_mulligan(self, side: Literal["Y", "E"], indices: Optional[list[int]] = None) -> None:
        """
        Apply an opening mulligan for the side using provided indices or a suggested heuristic.
        No-op if the suggested/explicit index list is empty.
        """
        indices_to_replace = self.suggest_opening_mulligan_indices(side) if indices is None else indices
        if not indices_to_replace:
            return
        self.mulligan(side, indices_to_replace)

    def perform_default_enemy_mulligan(self) -> None:
        """
        Convenience hook to run the enemy's opening mulligan through the same path as the player.
        """
        self.apply_opening_mulligan("E")

    def pass_turn(self) -> None:
        """Player passes without playing; used for game-end detection."""
        self.consecutive_passes += 1
        self.end_turn()

    def end_turn(self) -> None:
        acting_side = self.side_to_act
        self._turns_taken[acting_side] += 1
        self.side_to_act = "E" if acting_side == "Y" else "Y"
        self.turn += 1

    def is_game_over(self) -> bool:
        """Game ends if board full or two consecutive passes."""
        board_full = all(tile.card_id for row in self.board.tiles for tile in row)
        return board_full or self.consecutive_passes >= 2

    # ------------------------------------------------------------------ #
    # Cloning
    # ------------------------------------------------------------------ #

    def clone(self) -> "GameState":
        """Deep clone including RNG state and nested components."""
        clone = copy.deepcopy(self)
        return clone

    def __deepcopy__(self, memo):
        clone = object.__new__(self.__class__)
        memo[id(self)] = clone

        clone.board = copy.deepcopy(self.board, memo)
        clone.player_deck = copy.deepcopy(self.player_deck, memo)
        clone.enemy_deck = copy.deepcopy(self.enemy_deck, memo)
        clone.effect_engine = self.effect_engine  # stateless/shared OK
        clone.player_hand = copy.deepcopy(self.player_hand, memo)
        clone.enemy_hand = copy.deepcopy(self.enemy_hand, memo)

        clone.turn = self.turn
        clone.side_to_act = self.side_to_act
        clone.consecutive_passes = self.consecutive_passes
        clone._mulligan_used = dict(self._mulligan_used)
        clone._turns_taken = dict(self._turns_taken)

        clone.rng = random.Random()
        clone.rng.setstate(self.rng.getstate())

        return clone

    # ------------------------------------------------------------------ #
    # Stateful effect helpers
    # ------------------------------------------------------------------ #

    def _hand_for_side(self, side: Literal["Y", "E"]) -> Hand:
        return self.player_hand if side == "Y" else self.enemy_hand

    def _apply_stateful_on_play_effects(self, card: Card, side: Literal["Y", "E"], replaced_ally_power: int = 0) -> None:
        """
        Apply on_play effects that mutate hand/board state beyond power deltas.
        """
        effect_def = self.effect_engine.get_effect_for_card(card)
        if effect_def is None or effect_def.trigger != "on_play":
            return

        hand = self._hand_for_side(side)

        for op in effect_def.operations:
            if op.type == "add_to_hand" and op.card_ids:
                for cid in op.card_ids:
                    try:
                        hand.add_card(cid)
                    except KeyError:
                        # Skip unknown card ids to keep simulation deterministic
                        continue
            elif op.type == "spawn_token":
                token_id = op.raw.get("token_id") if op.raw else None
                if token_id is None:
                    continue
                per_pawns = bool(op.raw.get("per_pawns")) if op.raw else False
                # For each empty tile owned by the side, add token(s) to hand.
                for row in self.board.tiles:
                    for tile in row:
                        if tile.owner != side or tile.card_id is not None:
                            continue
                        count = tile.rank if per_pawns else 1
                        for _ in range(max(0, count)):
                            try:
                                hand.add_card(token_id)
                            except KeyError:
                                continue
            elif op.type == "replace_ally":
                # Follow-up effects handled in effect engine using replaced_ally_power.
                continue
