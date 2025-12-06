from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from qb_engine.card_hydrator import CardHydrator
from qb_engine.enemy_observation import EnemyObservation
from qb_engine.game_state import GameState
from qb_engine.legality import is_legal_placement
from qb_engine.prediction import PredictionEngine, ThreatMap
from qb_engine.scoring import MatchScore, compute_match_score

# Thresholds/constants for labeling
CLEAR_MARGIN = 5.0
BEST_LABEL_DELTA = 0.5
GOOD_LABEL_DELTA = 2.0
MARGIN_EPSILON = 0.1


@dataclass
class LaneStatus:
    lane_index: int
    you_power: int
    enemy_power: int
    winner: Optional[str]  # "YOU", "ENEMY", or None
    lane_points: int


@dataclass
class PositionEvaluation:
    match_score: MatchScore
    lanes: List[LaneStatus]
    you_margin: float
    enemy_best_margin: Optional[float]
    enemy_expected_margin: Optional[float]
    is_clearly_winning: bool
    is_clearly_losing: bool
    is_even: bool


@dataclass
class MoveCandidate:
    card_id: str
    hand_index: int
    lane_index: int
    col_index: int


@dataclass
class MoveEvaluation:
    move: MoveCandidate
    you_margin_after_move: float
    you_margin_after_enemy_best: float
    you_margin_after_enemy_expected: float
    position_after_move: Optional[PositionEvaluation]
    enemy_threat_after_move: Optional[ThreatMap]
    quality_rank: int = 0
    quality_label: str = ""
    explanation_tags: List[str] = None  # type: ignore[assignment]
    explanation_lines: List[str] = None  # type: ignore[assignment]


@dataclass
class CoachingRecommendation:
    position: PositionEvaluation
    moves: List[MoveEvaluation]
    top_n: int
    primary_message: str
    secondary_messages: List[str]


class CoachingEngine:
    def __init__(
        self,
        hydrator: Optional[CardHydrator] = None,
        prediction_engine: Optional[PredictionEngine] = None,
    ):
        self.hydrator = hydrator or CardHydrator()
        self.prediction_engine = prediction_engine or PredictionEngine(
            hydrator=self.hydrator
        )

    # ------------------------------------------------------------------ #
    # Move enumeration
    # ------------------------------------------------------------------ #
    def enumerate_you_moves(self, state: GameState) -> List[MoveCandidate]:
        moves: List[MoveCandidate] = []
        board = state.board
        for h_idx, card in enumerate(state.player_hand.cards):
            for lane in range(len(board.tiles)):
                for col in range(len(board.tiles[0])):
                    if is_legal_placement(board, lane, col, card):
                        moves.append(
                            MoveCandidate(
                                card_id=card.id,
                                hand_index=h_idx,
                                lane_index=lane,
                                col_index=col,
                            )
                        )
        return moves

    # ------------------------------------------------------------------ #
    # Position evaluation
    # ------------------------------------------------------------------ #
    def evaluate_position(
        self, state: GameState, enemy_obs: EnemyObservation
    ) -> PositionEvaluation:
        match_score = compute_match_score(state.board, state.effect_engine)
        lanes: List[LaneStatus] = []
        for lane_score in match_score.lanes:
            winner = None
            if lane_score.winner == "Y":
                winner = "YOU"
            elif lane_score.winner == "E":
                winner = "ENEMY"
            lanes.append(
                LaneStatus(
                    lane_index=lane_score.lane_index,
                    you_power=lane_score.power_you,
                    enemy_power=lane_score.power_enemy,
                    winner=winner,
                    lane_points=lane_score.lane_points,
                )
            )

        you_margin = float(match_score.total_you - match_score.total_enemy)

        enemy_best_margin: Optional[float] = None
        enemy_expected_margin: Optional[float] = None

        threat: Optional[ThreatMap] = None
        try:
            threat = self.prediction_engine.full_enemy_prediction(state, enemy_obs.state)
        except Exception:
            threat = None

        if threat is not None:
            # ThreatMap margins are enemy-centric; convert to your perspective
            enemy_best_margin = -float(threat.best_enemy_score)
            enemy_expected_margin = -float(threat.expected_enemy_score)

        is_clearly_winning = you_margin >= CLEAR_MARGIN
        is_clearly_losing = you_margin <= -CLEAR_MARGIN
        is_even = abs(you_margin) < 0.5

        return PositionEvaluation(
            match_score=match_score,
            lanes=lanes,
            you_margin=you_margin,
            enemy_best_margin=enemy_best_margin,
            enemy_expected_margin=enemy_expected_margin,
            is_clearly_winning=is_clearly_winning,
            is_clearly_losing=is_clearly_losing,
            is_even=is_even,
        )

    # ------------------------------------------------------------------ #
    # Move evaluation
    # ------------------------------------------------------------------ #
    def evaluate_move(
        self,
        state: GameState,
        enemy_obs: EnemyObservation,
        move: MoveCandidate,
        use_enemy_prediction: bool = True,
        baseline_eval: Optional[PositionEvaluation] = None,
    ) -> MoveEvaluation:
        # Pre-eval for explanations
        pre_eval = baseline_eval or self.evaluate_position(state, enemy_obs)
        baseline_you_margin = pre_eval.you_margin

        # Clone and apply
        clone = state.clone()
        card = self.hydrator.get_card(move.card_id)
        lane_name = list(state.board.LANE_NAME_TO_INDEX.keys()) if hasattr(state.board, "LANE_NAME_TO_INDEX") else ["TOP", "MID", "BOT"]  # type: ignore[attr-defined]
        clone.play_card_from_hand("Y", move.hand_index, move.lane_index, move.col_index)

        post_eval = self.evaluate_position(clone, enemy_obs)
        you_margin_after_move = post_eval.you_margin

        enemy_threat = None
        you_margin_after_enemy_best = you_margin_after_move
        you_margin_after_enemy_expected = you_margin_after_move

        if use_enemy_prediction:
            try:
                enemy_threat = self.prediction_engine.full_enemy_prediction(
                    clone, enemy_obs.state
                )
                you_margin_after_enemy_best = you_margin_after_move + (
                    -float(enemy_threat.best_enemy_score)
                )
                you_margin_after_enemy_expected = you_margin_after_move + (
                    -float(enemy_threat.expected_enemy_score)
                )
            except Exception:
                enemy_threat = None

        explanation_tags: List[str] = []
        explanation_lines: List[str] = []

        # Tag lane wins
        for before, after in zip(pre_eval.lanes, post_eval.lanes):
            if before.winner != "YOU" and after.winner == "YOU":
                explanation_tags.append(f"wins_lane_{after.lane_index}")
                explanation_lines.append(f"Secures {lane_name[after.lane_index]} lane")
            if before.winner == "YOU" and after.winner != "YOU":
                explanation_tags.append(f"loses_lane_{after.lane_index}")
                explanation_lines.append(
                    f"Loses {lane_name[after.lane_index]} lane advantage"
                )

        if you_margin_after_enemy_expected > baseline_you_margin + MARGIN_EPSILON:
            explanation_tags.append("improves_margin")
            explanation_lines.append("Improves overall margin (after enemy reply)")
        elif you_margin_after_enemy_expected < baseline_you_margin - MARGIN_EPSILON:
            explanation_tags.append("worsens_margin")
            explanation_lines.append("Worsens overall margin (after enemy reply)")

        return MoveEvaluation(
            move=move,
            you_margin_after_move=you_margin_after_move,
            you_margin_after_enemy_best=you_margin_after_enemy_best,
            you_margin_after_enemy_expected=you_margin_after_enemy_expected,
            position_after_move=post_eval,
            enemy_threat_after_move=enemy_threat,
            quality_rank=0,
            quality_label="",
            explanation_tags=explanation_tags,
            explanation_lines=explanation_lines,
        )

    # ------------------------------------------------------------------ #
    # Ranking
    # ------------------------------------------------------------------ #
    def rank_moves(
        self,
        state: GameState,
        enemy_obs: EnemyObservation,
        moves: List[MoveCandidate],
    ) -> List[MoveEvaluation]:
        baseline = self.evaluate_position(state, enemy_obs)
        evals = [self.evaluate_move(state, enemy_obs, m, baseline_eval=baseline) for m in moves]

        evals.sort(
            key=lambda m: (
                m.you_margin_after_enemy_expected,
                m.you_margin_after_enemy_best,
                m.you_margin_after_move,
            ),
            reverse=True,
        )

        best_expected = evals[0].you_margin_after_enemy_expected if evals else 0.0

        for idx, me in enumerate(evals, start=1):
            me.quality_rank = idx
            delta = best_expected - me.you_margin_after_enemy_expected
            if delta <= BEST_LABEL_DELTA:
                me.quality_label = "best"
            elif delta <= GOOD_LABEL_DELTA:
                me.quality_label = "good"
            elif me.you_margin_after_enemy_expected >= 0:
                me.quality_label = "playable"
            elif me.you_margin_after_enemy_expected > -CLEAR_MARGIN:
                me.quality_label = "risky"
            else:
                me.quality_label = "losing"

        return evals

    # ------------------------------------------------------------------ #
    # Recommend
    # ------------------------------------------------------------------ #
    def recommend_moves(
        self, state: GameState, enemy_obs: EnemyObservation, top_n: int = 3
    ) -> CoachingRecommendation:
        position_eval = self.evaluate_position(state, enemy_obs)
        candidates = self.enumerate_you_moves(state)

        if not candidates:
            return CoachingRecommendation(
                position=position_eval,
                moves=[],
                top_n=0,
                primary_message="No legal moves available.",
                secondary_messages=[],
            )

        evals = self.rank_moves(state, enemy_obs, candidates)
        primary = "Top move improves margin" if evals else "No moves evaluated"
        secondary: List[str] = []
        if evals and evals[0].explanation_lines:
            secondary.extend(evals[0].explanation_lines)
        if position_eval.is_clearly_winning:
            secondary.append("You are clearly winning; play safely.")
        elif position_eval.is_clearly_losing:
            secondary.append("You are behind; consider aggressive plays.")
        elif position_eval.is_even:
            secondary.append("Position is even; small advantages matter.")

        return CoachingRecommendation(
            position=position_eval,
            moves=evals,
            top_n=min(top_n, len(evals)),
            primary_message=primary,
            secondary_messages=secondary,
        )
