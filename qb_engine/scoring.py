"""
Scoring utilities for computing lane and match outcomes based on effective power.

Follows the deterministic rules in docs/scoring_design_spec.md and
docs/qb_rules_v2.2.4.md. These functions are pure: they do not mutate the
BoardState or EffectEngine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Protocol, TYPE_CHECKING

from qb_engine.board_state import BoardState

if TYPE_CHECKING:
    from qb_engine.effect_engine import EffectEngine


class _EffectEngineProtocol(Protocol):
    def compute_effective_power(self, board: BoardState, lane: int, col: int) -> int:
        ...


@dataclass
class LaneScore:
    """
    Per-lane scoring snapshot derived from effective power totals.
    """

    lane_index: int
    power_you: int
    power_enemy: int
    winner: Optional[Literal["Y", "E"]]
    lane_points: int


@dataclass
class MatchScore:
    """
    Aggregate scoring summary across all lanes.
    """

    lanes: List[LaneScore]
    total_you: int
    total_enemy: int
    winner: Optional[Literal["Y", "E"]]
    margin: int


def compute_lane_power(
    board: BoardState,
    effect_engine: _EffectEngineProtocol,
    lane_index: int,
) -> LaneScore:
    """
    Compute LaneScore for a single lane using effective power values.
    """
    power_you = 0
    power_enemy = 0

    num_cols = len(board.tiles[lane_index]) if board.tiles else 0

    for col_index in range(num_cols):
        tile = board.tile_at(lane_index, col_index)
        if tile.card_id is None:
            continue

        side = board.get_card_side(tile.card_id)
        if side not in {"Y", "E"}:
            continue

        effective_power = effect_engine.compute_effective_power(
            board,
            lane_index,
            col_index,
        )

        if side == "Y":
            power_you += effective_power
        else:
            power_enemy += effective_power

    if power_you > power_enemy:
        winner: Optional[Literal["Y", "E"]] = "Y"
        lane_points = power_you
    elif power_enemy > power_you:
        winner = "E"
        lane_points = power_enemy
    else:
        winner = None
        lane_points = 0

    return LaneScore(
        lane_index=lane_index,
        power_you=power_you,
        power_enemy=power_enemy,
        winner=winner,
        lane_points=lane_points,
    )


def compute_match_score(
    board: BoardState,
    effect_engine: _EffectEngineProtocol,
) -> MatchScore:
    """
    Compute MatchScore across all lanes using lane-level scoring.
    """
    num_lanes = len(board.tiles)
    lanes: List[LaneScore] = []

    for lane_index in range(num_lanes):
        lane_score = compute_lane_power(board, effect_engine, lane_index)
        lanes.append(lane_score)

    # Apply scoring modifiers (lane-win bonuses, lane_min_transfer) if supported.
    if hasattr(effect_engine, "apply_score_modifiers"):
        try:
            effect_engine.apply_score_modifiers(board, lanes)  # type: ignore[attr-defined]
        except Exception:
            # Scoring modifiers are best-effort; fall back to base scoring on error.
            pass

    total_you = sum(lane.lane_points for lane in lanes if lane.winner == "Y")
    total_enemy = sum(lane.lane_points for lane in lanes if lane.winner == "E")

    if total_you > total_enemy:
        winner: Optional[Literal["Y", "E"]] = "Y"
    elif total_enemy > total_you:
        winner = "E"
    else:
        winner = None

    margin = total_you - total_enemy

    return MatchScore(
        lanes=lanes,
        total_you=total_you,
        total_enemy=total_enemy,
        winner=winner,
        margin=margin,
    )


def calculate_territory_score(board: BoardState) -> tuple[float, float]:
    """
    Heuristic, non-rules scoring for board control:
      - Only counts empty tiles owned by a side (no occupants).
      - Lane must not be full (5 occupied tiles) to contribute.
      - Rank weighting:
          rank 1 -> +1.0
          rank 2 -> +3.0
          rank 3+ -> +4.0

    Returns:
      (you_territory_score, enemy_territory_score)
    """

    def _rank_value(rank: int) -> float:
        if rank <= 0:
            return 0.0
        if rank == 1:
            return 1.0
        if rank == 2:
            return 3.0
        return 4.0

    you_score = 0.0
    enemy_score = 0.0

    for lane_tiles in board.tiles:
        lane_full = all(tile.card_id is not None for tile in lane_tiles)
        if lane_full:
            continue

        for tile in lane_tiles:
            if tile.card_id is not None:
                continue
            if tile.owner == "Y":
                you_score += _rank_value(tile.rank)
            elif tile.owner == "E":
                enemy_score += _rank_value(tile.rank)

    return you_score, enemy_score
