from __future__ import annotations

import itertools
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from qb_engine.card_hydrator import CardHydrator
from qb_engine.board_state import LANE_NAME_TO_INDEX
from qb_engine.effect_engine import EffectEngine
from qb_engine.enemy_observation import EnemyObservationState
from qb_engine.game_state import GameState
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    apply_effects_for_enemy,
    apply_pawns_for_enemy,
    compute_projection_targets_for_enemy,
)
from qb_engine.scoring import MatchScore, compute_match_score

Origin = Literal["deck", "token", "effect", "unknown"]
LANE_INDEX_TO_NAME = {v: k for k, v in LANE_NAME_TO_INDEX.items()}


@dataclass
class InferredEnemyDeck:
    possible_decks: List[List[str]]
    weights: List[float]


@dataclass
class HandHypothesis:
    cards: List[str]
    probability: float


@dataclass
class EnemyHandBelief:
    hypotheses: List[HandHypothesis]


@dataclass
class EnemyMoveOutcome:
    move: Tuple[str, int, int]  # (card_id, lane_index, col_index)
    resulting_score: float
    match_score: MatchScore
    weight: float


@dataclass
class ThreatMap:
    outcomes: List[EnemyMoveOutcome]
    best_enemy_score: float
    expected_enemy_score: float
    lane_pressure: Dict[int, float]
    tile_pressure: Dict[Tuple[int, int], float]


class PredictionEngine:
    def __init__(
        self,
        hydrator: Optional[CardHydrator] = None,
        effect_engine: Optional[EffectEngine] = None,
        max_decks: int = 200,
        max_hands: int = 5000,
    ):
        self.hydrator = hydrator or CardHydrator()
        self.effect_engine = effect_engine or EffectEngine(
            Path("data/qb_effects_v1.1.json"), self.hydrator
        )  # type: ignore[name-defined]
        self.max_decks = max_decks
        self.max_hands = max_hands

    # ------------------------------------------------------------------ #
    # Deck inference
    # ------------------------------------------------------------------ #
    def infer_enemy_decks(self, observation: EnemyObservationState) -> InferredEnemyDeck:
        full_known = observation.enemy_deck_knowledge.full_deck_ids
        if full_known:
            return InferredEnemyDeck(possible_decks=[list(full_known)], weights=[1.0])

        required: List[str] = []
        for obs in observation.enemy_observations:
            if obs.side == "E" and obs.origin != "token":
                required.append(obs.card_id)

        # Build a single candidate deck consistent with required cards, padded deterministically.
        all_ids = sorted(cid for cid in self.hydrator.index.keys() if cid != "_meta")
        candidate: List[str] = []
        counts: Dict[str, int] = {}
        for cid in required:
            if counts.get(cid, 0) < 3:
                candidate.append(cid)
                counts[cid] = counts.get(cid, 0) + 1
        for cid in all_ids:
            if len(candidate) >= 15:
                break
            if counts.get(cid, 0) >= 3:
                continue
            candidate.append(cid)
            counts[cid] = counts.get(cid, 0) + 1

        return InferredEnemyDeck(possible_decks=[candidate], weights=[1.0])

    # ------------------------------------------------------------------ #
    # Hand inference
    # ------------------------------------------------------------------ #
    def infer_enemy_hand(
        self,
        state: GameState,
        observation: EnemyObservationState,
        inferred: InferredEnemyDeck,
    ) -> EnemyHandBelief:
        played = list(observation.enemy_deck_knowledge.played_ids)
        hand_size = len(state.enemy_hand.cards)

        hypotheses: List[HandHypothesis] = []
        for deck, weight in zip(inferred.possible_decks, inferred.weights):
            remaining = list(deck)
            for pid in played:
                if pid in remaining:
                    remaining.remove(pid)
            # Generate combinations deterministically
            combs = list(itertools.combinations(remaining, min(hand_size, len(remaining))))
            if not combs:
                continue
            # prune if too many
            if len(combs) > self.max_hands:
                combs = combs[: self.max_hands]
            prob_per = weight / len(combs)
            for c in combs:
                hypotheses.append(HandHypothesis(cards=list(c), probability=prob_per))

        # normalize
        total = sum(h.probability for h in hypotheses)
        if total > 0:
            for h in hypotheses:
                h.probability /= total
        return EnemyHandBelief(hypotheses=hypotheses)

    # ------------------------------------------------------------------ #
    # Move enumeration
    # ------------------------------------------------------------------ #
    def enumerate_enemy_moves(self, state: GameState, hand: HandHypothesis) -> List[Tuple[str, int, int]]:
        moves: List[Tuple[str, int, int]] = []
        board = state.board
        for card_id in hand.cards:
            card = self.hydrator.get_card(card_id)
            for lane in range(len(board.tiles)):
                for col in range(len(board.tiles[0])):
                    tile = board.tile_at(lane, col)
                    if tile.card_id is not None:
                        continue
                    if tile.owner != "E":
                        continue
                    if tile.rank < card.cost:
                        continue
                    moves.append((card_id, lane, col))
        return moves

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #
    def simulate_enemy_move(
        self,
        state: GameState,
        move: Tuple[str, int, int],
    ) -> Tuple[GameState, MatchScore, float]:
        card_id, lane, col = move
        clone = state.clone()
        card = self.hydrator.get_card(card_id)
        tile = clone.board.tile_at(lane, col)
        if tile.card_id is not None or tile.owner != "E" or tile.rank < card.cost:
            return clone, compute_match_score(clone.board, clone.effect_engine), 0.0  # type: ignore[arg-type]

        lane_name = LANE_INDEX_TO_NAME[lane]
        clone.board.place_card(lane_name, col + 1, card, placed_by="E", effect_engine=clone.effect_engine)
        proj = compute_projection_targets_for_enemy(lane, col, card)
        apply_pawns_for_enemy(clone.board, proj, card)
        apply_effects_for_enemy(clone.board, proj, card)
        clone.board.recompute_influence_from_deltas()

        match_score = compute_match_score(clone.board, clone.effect_engine)  # type: ignore[arg-type]
        resulting_score: float = float(match_score.margin)
        return clone, match_score, resulting_score

    # ------------------------------------------------------------------ #
    # Threat map
    # ------------------------------------------------------------------ #
    def compute_threat_map(
        self,
        state: GameState,
        observation: EnemyObservationState,
        inferred_decks: InferredEnemyDeck,
        hand_belief: EnemyHandBelief,
    ) -> ThreatMap:
        base_score = compute_match_score(state.board, state.effect_engine)
        base_margin = base_score.margin

        outcomes: List[EnemyMoveOutcome] = []
        lane_pressure: Dict[int, float] = {}
        tile_pressure: Dict[Tuple[int, int], float] = {}

        for hand in hand_belief.hypotheses:
            moves = self.enumerate_enemy_moves(state, hand)
            for move in moves:
                clone, mscore, eval_scalar = self.simulate_enemy_move(state, move)
                weight = hand.probability
                outcomes.append(
                    EnemyMoveOutcome(
                        move=move,
                        resulting_score=eval_scalar,
                        match_score=mscore,
                        weight=weight,
                    )
                )
                # lane pressure as margin delta
                delta = eval_scalar - base_margin
                lane = move[1]
                lane_pressure[lane] = lane_pressure.get(lane, 0.0) + weight * delta
                tile = (move[1], move[2])
                tile_pressure[tile] = tile_pressure.get(tile, 0.0) + weight * delta

        best_enemy_score = max((o.resulting_score for o in outcomes), default=base_margin)
        expected_enemy_score = sum(o.weight * o.resulting_score for o in outcomes)

        return ThreatMap(
            outcomes=outcomes,
            best_enemy_score=best_enemy_score,
            expected_enemy_score=expected_enemy_score,
            lane_pressure=lane_pressure,
            tile_pressure=tile_pressure,
        )

    # ------------------------------------------------------------------ #
    # Full pipeline
    # ------------------------------------------------------------------ #
    def full_enemy_prediction(self, state: GameState, observation: EnemyObservationState) -> ThreatMap:
        inferred = self.infer_enemy_decks(observation)
        hands = self.infer_enemy_hand(state, observation, inferred)
        return self.compute_threat_map(state, observation, inferred, hands)
