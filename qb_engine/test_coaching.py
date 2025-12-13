from pathlib import Path

import pytest

from qb_engine.card_hydrator import CardHydrator
from qb_engine.coaching import (
    CoachingEngine,
    MoveCandidate,
    MoveEvaluation,
    ThreatMap,
)
from qb_engine.deck import Deck
from qb_engine.enemy_observation import EnemyObservation
from qb_engine.game_state import GameState
from qb_engine.prediction import PredictionEngine, EnemyMoveOutcome
from qb_engine.scoring import MatchScore, LaneScore
from qb_engine.effect_engine import EffectEngine


def _make_state(ids=None, seed=1):
    hydrator = CardHydrator()
    ids = ids or [str(i).zfill(3) for i in range(1, 16)]
    effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    return GameState(
        player_deck=Deck(ids, seed=seed),
        enemy_deck=Deck(ids, seed=seed + 1),
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=seed,
    )


class FakePrediction(PredictionEngine):
    def __init__(self, best: float, expected: float):
        self.best = best
        self.expected = expected

    def full_enemy_prediction(self, state, obs):
        return ThreatMap(
            outcomes=[
                EnemyMoveOutcome(move=("001", 0, 4), resulting_score=self.expected, match_score=MatchScore([], 0, 0, None, 0), weight=1.0)  # type: ignore[list-item]
            ],
            best_enemy_score=self.best,
            expected_enemy_score=self.expected,
            lane_pressure={},
            tile_pressure={},
        )


def test_enumerate_you_moves_respects_legality():
    state = _make_state(ids=["001"] * 15)
    engine = CoachingEngine()
    moves = engine.enumerate_you_moves(state)
    assert moves  # there should be legal moves on your column
    for m in moves:
        tile = state.board.tile_at(m.lane_index, m.col_index)
        assert tile.owner == "Y"
        assert tile.card_id is None


def test_evaluate_position_uses_scoring_engine():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()
    pos = engine.evaluate_position(state, obs)
    assert pos.match_score.total_you == 0
    assert pos.you_margin == 0


def test_evaluate_position_includes_prediction_margins():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine(prediction_engine=FakePrediction(best=2.0, expected=1.0))
    pos = engine.evaluate_position(state, obs)
    assert pos.enemy_best_margin == -2.0
    assert pos.enemy_expected_margin == -1.0


def test_evaluate_move_does_not_mutate_original_state():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()
    candidates = engine.enumerate_you_moves(state)
    move = candidates[0]
    tile_before = state.board.tile_at(move.lane_index, move.col_index).card_id
    _ = engine.evaluate_move(state, obs, move, use_enemy_prediction=False)
    assert state.board.tile_at(move.lane_index, move.col_index).card_id == tile_before


def test_evaluate_move_uses_prediction_engine():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine(prediction_engine=FakePrediction(best=2.0, expected=1.0))
    move = engine.enumerate_you_moves(state)[0]
    me = engine.evaluate_move(state, obs, move, use_enemy_prediction=True)
    assert me.you_margin_after_enemy_best <= me.you_margin_after_move
    assert me.you_margin_after_enemy_expected <= me.you_margin_after_move


def test_evaluate_move_generates_explanations():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()
    move = engine.enumerate_you_moves(state)[0]
    me = engine.evaluate_move(state, obs, move, use_enemy_prediction=False)
    assert isinstance(me.explanation_tags, list)
    assert isinstance(me.explanation_lines, list)


def test_rank_moves_sorts_by_expected_margin():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()

    # Patch evaluate_move to return deterministic margins
    def fake_eval_move(_, __, move, baseline_eval=None):
        return MoveEvaluation(
            move=move,
            you_margin_after_move=0,
            you_margin_after_enemy_best=-move.lane_index,
            you_margin_after_enemy_expected=-move.col_index,
            position_after_move=None,
            enemy_threat_after_move=None,
            explanation_tags=[],
            explanation_lines=[],
        )

    engine.evaluate_move = fake_eval_move  # type: ignore[assignment]

    moves = [
        MoveCandidate("001", 0, 0, 2),
        MoveCandidate("001", 1, 1, 1),
        MoveCandidate("001", 2, 2, 0),
    ]
    ranked = engine.rank_moves(state, obs, moves)
    assert ranked[0].move.col_index == 0  # highest expected (least negative)
    assert ranked[0].quality_rank == 1


def test_recommend_moves_returns_top_n():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()
    reco = engine.recommend_moves(state, obs, top_n=2)
    assert reco.top_n <= 2
    assert isinstance(reco.primary_message, str)


def test_recommend_moves_handles_no_legal_moves():
    state = _make_state(ids=["001"] * 15)
    # Fill your tiles to block plays
    for lane in range(3):
        state.board.tile_at(lane, 0).card_id = "001"
    obs = EnemyObservation()
    engine = CoachingEngine()
    reco = engine.recommend_moves(state, obs)
    assert reco.moves == []
    assert "No legal moves" in reco.primary_message


def test_recommend_moves_includes_pass_when_allowed():
    state = _make_state(ids=["001"] * 15)
    # Fill your tiles to block plays
    for lane in range(3):
        state.board.tile_at(lane, 0).card_id = "001"
    obs = EnemyObservation()
    engine = CoachingEngine()
    reco = engine.recommend_moves(state, obs, allow_pass=True)
    assert any(me.move.card_id == "_PASS_" for me in reco.moves)
    assert reco.moves[0].quality_rank == 1


def test_pass_ranks_above_worsening_move(monkeypatch):
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    engine = CoachingEngine()

    bad_move = MoveEvaluation(
        move=MoveCandidate("001", 0, 0, 0),
        you_margin_after_move=-5.0,
        you_margin_after_enemy_best=-5.0,
        you_margin_after_enemy_expected=-5.0,
        position_after_move=None,
        enemy_threat_after_move=None,
        quality_rank=0,
        quality_label="",
        explanation_tags=[],
        explanation_lines=[],
    )

    def fake_rank(state_param, obs_param, moves):
        return [bad_move]

    pass_eval = MoveEvaluation(
        move=MoveCandidate("_PASS_", -1, -1, -1),
        you_margin_after_move=0.0,
        you_margin_after_enemy_best=0.0,
        you_margin_after_enemy_expected=0.0,
        position_after_move=None,
        enemy_threat_after_move=None,
        quality_rank=0,
        quality_label="",
        explanation_tags=["pass"],
        explanation_lines=["pass"],
    )

    monkeypatch.setattr(engine, "rank_moves", fake_rank)
    monkeypatch.setattr(engine, "_evaluate_pass", lambda *args, **kwargs: pass_eval)

    reco = engine.recommend_moves(state, obs, allow_pass=True)
    assert reco.moves[0].move.card_id == "_PASS_"
    assert reco.moves[0].quality_label == "best"


def test_margin_tags_respect_expected_margin():
    state = _make_state(ids=["001"] * 15)
    obs = EnemyObservation()
    move = CoachingEngine().enumerate_you_moves(state)[0]

    engine_improve = CoachingEngine(prediction_engine=FakePrediction(best=0.0, expected=-0.5))
    me_improve = engine_improve.evaluate_move(state, obs, move, use_enemy_prediction=True)
    assert "improves_margin" in me_improve.explanation_tags
    assert "worsens_margin" not in me_improve.explanation_tags

    engine_worsen = CoachingEngine(prediction_engine=FakePrediction(best=0.0, expected=2.0))
    me_worsen = engine_worsen.evaluate_move(state, obs, move, use_enemy_prediction=True)
    assert "worsens_margin" in me_worsen.explanation_tags
    assert "improves_margin" not in me_worsen.explanation_tags
