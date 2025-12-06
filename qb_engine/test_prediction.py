from pathlib import Path
from itertools import combinations

from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.enemy_observation import EnemyObservation
from qb_engine.game_state import GameState
from qb_engine.prediction import (
    EnemyHandBelief,
    HandHypothesis,
    PredictionEngine,
    ThreatMap,
)
from qb_engine.effect_engine import EffectEngine
from qb_engine.scoring import compute_match_score


def _make_engine():
    hydrator = CardHydrator()
    effect_engine = EffectEngine(Path("data/qb_effects_v1.json"), hydrator)
    return hydrator, effect_engine


def _make_state_with_decks(ids):
    hydrator, effect_engine = _make_engine()
    return GameState(
        player_deck=Deck(ids, seed=1),
        enemy_deck=Deck(ids, seed=2),
        hydrator=hydrator,
        effect_engine=effect_engine,
        seed=3,
    )


def test_infer_enemy_decks_trivial_known_deck():
    ids = [str(i).zfill(3) for i in range(1, 16)]
    obs = EnemyObservation(known_enemy_deck_ids=ids)
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    assert inferred.possible_decks == [ids]
    assert inferred.weights == [1.0]


def test_infer_enemy_decks_with_observed_cards():
    obs = EnemyObservation()
    obs.register_enemy_play("003", 0, 4, turn=1)
    obs.register_enemy_play("020", 1, 4, turn=2)
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    for deck in inferred.possible_decks:
        assert "003" in deck and "020" in deck
        assert len(deck) == 15
        assert all(deck.count(cid) <= 3 for cid in set(deck))


def test_infer_enemy_hand_simple_known_deck():
    ids = [str(i).zfill(3) for i in range(1, 16)]
    state = _make_state_with_decks(ids)
    obs = EnemyObservation(known_enemy_deck_ids=ids)
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    belief = engine.infer_enemy_hand(state, obs.state, inferred)
    assert isinstance(belief, EnemyHandBelief)
    assert len(belief.hypotheses) == len(list(combinations(ids, 5)))
    probs = sum(h.probability for h in belief.hypotheses)
    assert abs(probs - 1.0) < 1e-6


def test_infer_enemy_hand_after_plays():
    ids = [str(i).zfill(3) for i in range(1, 16)]
    state = _make_state_with_decks(ids)
    obs = EnemyObservation(known_enemy_deck_ids=ids)
    obs.register_enemy_play("001", 0, 4, turn=1)
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    belief = engine.infer_enemy_hand(state, obs.state, inferred)
    for h in belief.hypotheses:
        assert "001" not in h.cards


def test_enumerate_enemy_moves_respects_legality():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    # enemy owns col 4 tiles; ensure rank sufficient
    hypo = HandHypothesis(cards=[ids[0]], probability=1.0)
    engine = PredictionEngine()
    moves = engine.enumerate_enemy_moves(state, hypo)
    # Should include three tiles at enemy home column (col=4)
    assert all(m[1] in (0, 1, 2) for m in moves)
    assert all(m[2] == 4 for m in moves)


def test_simulate_enemy_move_does_not_mutate_original_state():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    engine = PredictionEngine()
    move = ("001", 0, 4)
    original_tile = state.board.tile_at(0, 4).card_id
    clone, mscore, eval_scalar = engine.simulate_enemy_move(state, move)
    assert state.board.tile_at(0, 4).card_id == original_tile  # untouched
    assert clone.board.tile_at(0, 4).card_id == "001"
    assert isinstance(mscore, type(compute_match_score(state.board, state.effect_engine)))  # type: ignore
    assert isinstance(eval_scalar, float)


def test_simulate_enemy_move_updates_scores_correctly():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    engine = PredictionEngine()
    move = ("001", 1, 4)
    _, mscore, eval_scalar = engine.simulate_enemy_move(state, move)
    assert mscore.total_enemy > mscore.total_you
    assert eval_scalar == mscore.margin


def test_compute_threat_map_basic():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    obs = EnemyObservation()
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    hand_belief = EnemyHandBelief(hypotheses=[HandHypothesis(cards=["001"], probability=1.0)])
    threat = engine.compute_threat_map(state, obs.state, inferred, hand_belief)
    assert isinstance(threat, ThreatMap)
    assert threat.outcomes
    assert threat.best_enemy_score >= threat.expected_enemy_score


def test_threat_map_expected_vs_best_case():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    obs = EnemyObservation()
    engine = PredictionEngine()
    inferred = engine.infer_enemy_decks(obs.state)
    hand_belief = EnemyHandBelief(
        hypotheses=[
            HandHypothesis(cards=["001"], probability=0.6),
            HandHypothesis(cards=["001"], probability=0.4),
        ]
    )
    threat = engine.compute_threat_map(state, obs.state, inferred, hand_belief)
    assert threat.expected_enemy_score <= threat.best_enemy_score


def test_full_enemy_prediction():
    ids = ["001"] * 15
    state = _make_state_with_decks(ids)
    obs = EnemyObservation()
    engine = PredictionEngine()
    threat = engine.full_enemy_prediction(state, obs.state)
    assert isinstance(threat, ThreatMap)
    assert isinstance(threat.outcomes, list)
