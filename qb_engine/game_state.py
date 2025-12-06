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

        # Opening hands: draw 3 if not provided
        if player_hand_ids is not None:
            self.player_hand.from_card_ids(player_hand_ids)
        else:
            self.player_hand.from_card_ids(self.player_deck.draw_n(3))

        if enemy_hand_ids is not None:
            self.enemy_hand.from_card_ids(enemy_hand_ids)
        else:
            self.enemy_hand.from_card_ids(self.enemy_deck.draw_n(3))

        self.turn = 1
        self.side_to_act: Literal["Y", "E"] = "Y"

    # ------------------------------------------------------------------ #
    # Turn mechanics
    # ------------------------------------------------------------------ #

    def draw_start_of_turn(self) -> None:
        """Side to act draws one card."""
        if self.side_to_act == "Y":
            card_id = self.player_deck.draw()
            self.player_hand.add_card(card_id)
        else:
            card_id = self.enemy_deck.draw()
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

        self.board.place_card(lane_name, col_number, card, self.effect_engine)

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

    def cleanup(self) -> None:
        """Placeholder for destruction/effect cleanup; currently just recomputes influence."""
        self.board.recompute_influence_from_deltas()

    def end_turn(self) -> None:
        self.side_to_act = "E" if self.side_to_act == "Y" else "Y"
        self.turn += 1

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

        clone.rng = random.Random()
        clone.rng.setstate(self.rng.getstate())

        return clone
