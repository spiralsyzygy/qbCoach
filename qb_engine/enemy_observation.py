from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from qb_engine.board_state import BoardState
from qb_engine.game_state import GameState


Origin = Literal["deck", "token", "effect", "unknown"]
Side = Literal["Y", "E"]


@dataclass
class ObservedCard:
    card_id: str
    side: Side
    origin: Origin
    turn_observed: int
    lane_index: Optional[int]
    col_index: Optional[int]
    destroyed_on_turn: Optional[int] = None


@dataclass
class EnemyDeckKnowledge:
    full_deck_ids: List[str] = field(default_factory=list)
    played_ids: List[str] = field(default_factory=list)
    remaining_ids: List[str] = field(default_factory=list)

    def recompute_remaining(self) -> None:
        if not self.full_deck_ids:
            self.remaining_ids = []
            return

        full_counts = Counter(self.full_deck_ids)
        played_counts = Counter(self.played_ids)
        remaining: List[str] = []
        for card_id, count in full_counts.items():
            leftover = count - played_counts.get(card_id, 0)
            if leftover > 0:
                remaining.extend([card_id] * leftover)
        self.remaining_ids = remaining


@dataclass
class EnemyObservationState:
    observations: List[ObservedCard] = field(default_factory=list)
    enemy_observations: List[ObservedCard] = field(default_factory=list)
    enemy_deck_knowledge: EnemyDeckKnowledge = field(default_factory=EnemyDeckKnowledge)
    last_updated_turn: int = 0


class EnemyObservation:
    """
    Tracks observed enemy cards, their positions, destruction turns, and (optionally)
    remaining known-deck contents.
    """

    def __init__(self, known_enemy_deck_ids: Optional[List[str]] = None):
        self._initial_known_deck = list(known_enemy_deck_ids or [])
        deck_knowledge = EnemyDeckKnowledge(
            full_deck_ids=list(self._initial_known_deck),
            played_ids=[],
            remaining_ids=list(self._initial_known_deck),
        )
        self.state = EnemyObservationState(
            observations=[],
            enemy_observations=[],
            enemy_deck_knowledge=deck_knowledge,
            last_updated_turn=0,
        )

    def reset(self) -> None:
        self.state.observations = []
        self.state.enemy_observations = self.state.observations
        self.state.enemy_deck_knowledge = EnemyDeckKnowledge(
            full_deck_ids=list(self._initial_known_deck),
            played_ids=[],
            remaining_ids=list(self._initial_known_deck),
        )
        self.state.last_updated_turn = 0

    # ------------------------------------------------------------------ #
    # Updates
    # ------------------------------------------------------------------ #

    def update_from_game_state(self, state: GameState) -> None:
        board: BoardState = state.board
        turn = state.turn

        current_positions: List[tuple[str, int, int]] = []
        for lane_idx, row in enumerate(board.tiles):
            for col_idx, tile in enumerate(row):
                if tile.card_id and tile.owner == "E":
                    current_positions.append((tile.card_id, lane_idx, col_idx))

        # Add or refresh observations for current enemy board cards
        for card_id, lane_idx, col_idx in current_positions:
            existing = self._find_observation(card_id, lane_idx, col_idx)
            if existing:
                existing.lane_index = lane_idx
                existing.col_index = col_idx
            else:
                obs = ObservedCard(
                    card_id=card_id,
                    side="E",
                    origin="unknown",
                    turn_observed=turn,
                    lane_index=lane_idx,
                    col_index=col_idx,
                )
                self.state.observations.append(obs)

        # Mark destroyed cards (were on board, now gone)
        current_set = {(c, l, col) for (c, l, col) in current_positions}
        for obs in self.state.observations:
            if (
                obs.side == "E"
                and obs.destroyed_on_turn is None
                and obs.lane_index is not None
                and obs.col_index is not None
                and (obs.card_id, obs.lane_index, obs.col_index) not in current_set
            ):
                obs.destroyed_on_turn = turn
                obs.lane_index = None
                obs.col_index = None

        self.state.enemy_observations = self.state.observations
        self.state.last_updated_turn = turn

    def register_enemy_play(
        self,
        card_id: str,
        lane_index: int,
        col_index: int,
        turn: int,
        origin: Origin = "deck",
    ) -> None:
        obs = ObservedCard(
            card_id=card_id,
            side="E",
            origin=origin,
            turn_observed=turn,
            lane_index=lane_index,
            col_index=col_index,
        )
        self.state.observations.append(obs)
        self.state.enemy_observations = self.state.observations

        if self.state.enemy_deck_knowledge.full_deck_ids and origin == "deck":
            self.state.enemy_deck_knowledge.played_ids.append(card_id)
            self.state.enemy_deck_knowledge.recompute_remaining()

        self.state.last_updated_turn = turn

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get_enemy_board_cards(self) -> List[ObservedCard]:
        return [
            obs
            for obs in self.state.observations
            if obs.side == "E"
            and obs.destroyed_on_turn is None
            and obs.lane_index is not None
            and obs.col_index is not None
        ]

    def get_enemy_destroyed_cards(self) -> List[ObservedCard]:
        return [
            obs
            for obs in self.state.observations
            if obs.side == "E" and obs.destroyed_on_turn is not None
        ]

    def get_enemy_tokens(self) -> List[ObservedCard]:
        return [
            obs
            for obs in self.state.observations
            if obs.side == "E" and obs.origin == "token"
        ]

    def get_known_enemy_deck_remaining_ids(self) -> List[str]:
        return list(self.state.enemy_deck_knowledge.remaining_ids)

    def get_all_enemy_observations(self) -> List[ObservedCard]:
        return list(self.state.enemy_observations)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _find_observation(
        self, card_id: str, lane_index: int, col_index: int
    ) -> Optional[ObservedCard]:
        for obs in self.state.observations:
            if (
                obs.card_id == card_id
                and obs.side == "E"
                and obs.destroyed_on_turn is None
                and obs.lane_index == lane_index
                and obs.col_index == col_index
            ):
                return obs
        return None

