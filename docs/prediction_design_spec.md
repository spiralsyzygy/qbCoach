# **Phase E — Prediction Engine Design Specification (Epic E)**

**Version 0.1.0 — Deterministic Enemy Modeling & Threat Projection**

---

# **1. Purpose of Phase E**

Phase E introduces the first **non-observational**, **non-rule**, **non-simulation** layer in the engine:
It is not about rules or legality or effects — those already exist.

**Phase E is the “forward-looking reasoning engine”**, responsible for:

1. **Enemy Deck Inference**
2. **Enemy Hand Prediction**
3. **Enemy Next-Move Projection**
4. **Threat Map Construction**

This layer consumes deterministic state from:

* Simulation Layer (Phase C)
* Enemy Observation Layer (Phase D) 
* Scoring Layer (v3.0) 

and produces a structured, deterministic prediction model for the **Coaching Layer (Phase F)**.

**Phase E does not make coaching decisions.**
It only produces structured prediction output.

---

# **2. Architectural Position**

```
Rules → Engine Core → Simulation (Phase C) → Observation (Phase D) → Prediction (Phase E) → Coaching (Phase F)
```

Inputs:

* `GameState` (Phase C)
* `EnemyObservationState` (Phase D)
* `BoardState`, `EffectEngine`, `LegalityChecker`, `ProjectionEngine`
* JSON DB (card data)

Outputs:

* A data model containing:

  * Inferred deck pool (weighted)
  * Possible hand-states (+ probabilities)
  * Possible enemy moves per hand-state
  * Scored outcomes for each move
  * Aggregated threat map

Prediction results must be **stable, reproducible, deterministic**, given:

* Initial RNG seed (from Simulation Layer)
* Current GameState
* Current EnemyObservationState

---

# **3. Design Principles & Constraints**

1. **Deterministic**
   No randomness. All probabilities are *derived*, not sampled.

2. **Evidence-first**
   The prediction layer uses:

   * Observations from Phase D
   * Rules & legality
   * Simulations (Phase C)

3. **No hallucinated card data**
   All card info is hydrated from JSON DB.

4. **No coaching**
   No recommendations or human-readable explanations.
   Prediction only.

5. **Search-limited**
   Depth = 1 ply (enemy only), because Coaching Layer will handle multi-turn search.

6. **Clone-safe**
   Prediction may run thousands of GameState clones.
   Must not mutate upstream state.

---

# **4. Core Data Models**

Create these classes inside:

```
qb_engine/prediction.py
```

---

## **4.1 InferredEnemyDeck**

Probabilistic representation of the enemy’s remaining deck candidates.

```python
@dataclass
class InferredEnemyDeck:
    possible_decks: List[List[str]]         # each deck is a list of card IDs
    weights: List[float]                    # same length as possible_decks
```

### Semantics:

* Each deck is a **candidate 10-card deck** consistent with observations.
* Weights sum to **1.0**.
* In known-deck mode (Phase D), this becomes trivial:

  * `possible_decks = [full_deck_ids]`
  * `weights = [1.0]`

### Deck Candidate Generation Rules

A deck candidate is valid if:

1. It contains **all observed non-token enemy plays**.
2. It honors duplicate rules:

   * Max 3 copies per card ID.
3. It uses only cards from the global JSON DB.

Deck inference is **bounded** by:

* Maximum deck count threshold (default: 200 generated candidates)
* Pruning rules:

  * Prefer decks matching observed cost distribution
  * Prefer decks matching typical archetypes (optional future extension)

---

## **4.2 EnemyHandBelief**

Represents possible enemy hands at the current turn.

```python
@dataclass
class HandHypothesis:
    cards: List[str]            # card IDs in hand
    probability: float          # normalized weight

@dataclass
class EnemyHandBelief:
    hypotheses: List[HandHypothesis]
```

### Generation Steps

Given:

* InferredEnemyDeck
* EnemyObservationState.played_ids
* Turn number
* Known draw rules (Phase C)

Compute:

1. **Remaining deck cards** after removing all played_ids.
2. **Draw count**:

   * starting hand size = 5
   * 1 draw per turn at turn start
   * mulligan behavior defined in Phase C
3. **All combinations** of remaining deck cards consistent with the required hand size.
4. Weight each hand by:

```
Probability(hand | deck) = 
    1 / (number of possible hands for that deck)
weighted by deck weight
```

**Result:** list of `HandHypothesis` objects summing to probability 1.0.

---

## **4.3 EnemyMoveOutcome**

Represents results of simulating a specific move from a specific hand-hypothesis.

```python
@dataclass
class EnemyMoveOutcome:
    move: Tuple[str, int, int]  # (card_id, lane_index, col_index)
    resulting_score: float      # evaluation scalar after simulation
    match_score: MatchScore     # strict match score snapshot
    weight: float               # probability of this branch (hand prob * deck prob)
```

---

## **4.4 ThreatMap**

Aggregated from all move outcomes.

```python
@dataclass
class ThreatMap:
    outcomes: List[EnemyMoveOutcome]
    best_enemy_score: float              # worst-case score from your perspective
    expected_enemy_score: float          # probability-weighted average
    lane_pressure: Dict[int, float]      # per-lane weighted enemy pressure
    tile_pressure: Dict[Tuple[int,int], float]  # tile-level pressure graph
```

### Tile Pressure

For each tile (lane,col):

```
Sum(weight * resulting_score_delta_if_move_plays_on_or_affects_tile)
```

---

# **5. PredictionEngine API**

File: `qb_engine/prediction.py`

Create a class:

```python
class PredictionEngine:
    def __init__(self, card_db, legality_checker, projection_engine, effect_engine, scoring_engine):
        ...
```

The PredictionEngine shall expose the following methods:

---

## **5.1 infer_enemy_decks(observation: EnemyObservationState) -> InferredEnemyDeck**

### Behavior:

1. If known-deck mode → trivial.

2. Otherwise construct deck candidates:

   * Identify **required cards** = all observed non-token enemy card_ids.
   * Generate candidate decks of size 10 satisfying:

     * all required cards appear
     * duplicates <= 3
     * total cards = 10
   * Limit total candidates to threshold (default max 200)

     * If more → prune using cost distribution similarity to required cards.

3. Assign equal weights to remaining candidates.

---

## **5.2 infer_enemy_hand(state: GameState, observation: EnemyObservationState, inferred: InferredEnemyDeck) -> EnemyHandBelief**

### Behavior:

1. Compute draw count based on:

   * Turn number
   * Mulligan data (state.enemy_hand.mulligans_applied)
   * Draws per turn from Phase C

2. For each deck D in inferred.possible_decks:

   * Remaining = deck − observation.played_ids − destroyed tokens
   * Compute all combinations of size = `state.enemy_hand_size`
   * Each combination H becomes a HandHypothesis with:

     ```
     P(H | D) = (1 / number_of_combinations_for_D) * deck_weight
     ```

3. Normalize probabilities across all hand hypotheses.

Note: HandHypothesis must not exceed ~200 items; if >200, prune lowest-prob branches.

---

## **5.3 enumerate_enemy_moves(state: GameState, hand: HandHypothesis) -> List[(card_id, lane, col)]**

### Behavior:

* Use LegalityChecker to check every tile.
* For each card in hand.cards:

  * If legal, produce a move tuple.
* No sorting; ordering unimportant.

---

## **5.4 simulate_enemy_move(state: GameState, move) -> (GameState, MatchScore, evaluation_scalar)**

Steps:

1. Clone state (deep copy).
2. Apply play:

   * `state.play_card_from_hand("E", card_index, lane, col)`
3. Apply projections (ProjectionEngine)
4. Apply effects (EffectEngine)
5. Cleanup destruction (Phase C semantics)
6. Compute match score (rules-level) using scoring_engine
7. Compute evaluation_scalar (engine-level) using LanePowerEvaluator (v2.1) described in `qb_engine_v2.1.0.md` 
8. Return all.

---

## **5.5 compute_threat_map(state, observation, inferred_decks, hand_belief) -> ThreatMap**

Process:

1. For each HandHypothesis H:

   * Enumerate moves M
   * For each move:

     * outcome = simulate_enemy_move(…)
     * weight = H.probability

2. Aggregate:

```
best_enemy_score = max(outcome.resulting_score)
expected_enemy_score = sum(weight * resulting_score)
lane_pressure[L] = sum(weight * lane_delta)
tile_pressure[(L,C)] = sum(weight * tile_impact)
```

3. Return ThreatMap.

**Lane/tile delta semantics**:

* Use effective power differences to define:

  * lane_delta = enemy_power_change − your_power_change (per lane)
  * tile_impact = power or ownership changes on that tile

---

## **5.6 full_enemy_prediction(state, observation) -> ThreatMap**

Top-level method:

```
decks = infer_enemy_decks(observation)
hands  = infer_enemy_hand(state, observation, decks)
threat = compute_threat_map(state, observation, decks, hands)
return threat
```

Used by Phase F.

---

# **6. Integration with Existing Repo**

### Create new module:

```
qb_engine/prediction.py
```

### Update exports:

`qb_engine/__init__.py` should export:

* InferredEnemyDeck
* EnemyHandBelief
* HandHypothesis
* EnemyMoveOutcome
* ThreatMap
* PredictionEngine

### Do **not** modify:

* BoardState
* GameState (except docstrings)
* LegalityChecker
* ProjectionEngine
* EffectEngine
* ScoringEngine
* EnemyObservation

### Add docstring comments in:

* `GameState` to mention prediction layer is above observation.

---

# **7. Pytest Coverage — test_prediction.py**

Create:

```
qb_engine/test_prediction.py
```

with the following test groups.

---

## **7.1 Deck Inference Tests**

### **test_infer_enemy_decks_trivial_known_deck**

* Provide observation with full deck known.
* Expect exactly one deck with weight 1.0.

### **test_infer_enemy_decks_with_observed_cards**

* Observed enemy played: `["003", "020"]`
* Generate candidate decks.
* Assert every candidate contains these cards.
* Assert no candidate exceeds 10 cards or 3 copies of any ID.

### **test_infer_enemy_decks_pruned_under_cap**

* Provide many observed low-information plays.
* Ensure output does not exceed pruning threshold.

---

## **7.2 Hand Inference Tests**

### **test_infer_enemy_hand_simple_known_deck**

* Turn = 1, no plays yet, known deck of 10 cards.
* Hand size = 5.
* Expect `C(10,5)` equally weighted hypotheses.

### **test_infer_enemy_hand_after_plays**

* Observed enemy played cards reduce the remaining pool.
* Generated hands must exclude those card IDs.

---

## **7.3 Move Enumeration Tests**

### **test_enumerate_enemy_moves_respects_legality**

* If tile is not legal (enemy tile, neutral tile, occupied tile), move must not be included.
* If rank >= card.cost on YOU-owned tile, move included.

---

## **7.4 Simulation Tests**

### **test_simulate_enemy_move_does_not_mutate_original_state**

* Clone-safe behavior.

### **test_simulate_enemy_move_updates_scores_correctly**

* Use small board; verify match score after move.

---

## **7.5 Threat Map Tests**

### **test_compute_threat_map_basic**

* 1 hand hypothesis, 1 legal move.
* Expected:

  * lane_pressure identified correctly
  * tile_pressure correct for tiles affected by projection.

### **test_threat_map_expected_vs_best_case**

* Multiple hand hypotheses with weighted outcomes.
* Ensure:

  * expected_enemy_score = Σ w_i * score_i
  * best_enemy_score = max(score_i)

---

## **7.6 Full Pipeline Test**

### **test_full_enemy_prediction**

Minimal full cycle:

```
obs = EnemyObservation()
state = GameState(...)
engine = PredictionEngine(...)

threat = engine.full_enemy_prediction(state, obs)

assert isinstance(threat, ThreatMap)
assert threat.outcomes != []
```

---

# **8. Completion Criteria**

Phase E is complete when:

1. `qb_engine/prediction.py` exists with all models and methods.
2. `qb_engine/test_prediction.py` passes 100% under pytest.
3. All previous tests remain green.
4. Prediction results are:

   * Deterministic
   * Clone-safe
   * Correctly weighted
   * Compatible with Phase F

---

# **CODex-READY IMPLEMENTATION PROMPT**

Paste the following into VS Code to implement Phase E:

---

```text
You are Codex, editing the local deterministic qbCoach engine.

Use the authoritative Phase E spec in docs/prediction_design_spec.md.

Task:
Implement the entire Prediction Engine (Epic E).

Create:
    qb_engine/prediction.py

Implement the following data models:
    - InferredEnemyDeck
    - HandHypothesis
    - EnemyHandBelief
    - EnemyMoveOutcome
    - ThreatMap
    - PredictionEngine

PredictionEngine must implement:
    - infer_enemy_decks(...)
    - infer_enemy_hand(...)
    - enumerate_enemy_moves(...)
    - simulate_enemy_move(...)
    - compute_threat_map(...)
    - full_enemy_prediction(...)

Requirements:
    - Deterministic only (no RNG use)
    - Clone-safe (never mutate passed-in GameState)
    - Use LegalityChecker, ProjectionEngine, EffectEngine, ScoringEngine
    - Hydrate all card data from JSON DB
    - Enforce 10-card deck, <=3 copies per card
    - Limit candidate deck count to 200 using pruning rules
    - Use weighted probabilities for hand inference
    - Produce ThreatMap outputs as defined
    - Do NOT modify existing engine modules

Add new tests:
    qb_engine/test_prediction.py
Tests must cover deck inference, hand inference, move enumeration,
simulation integrity, and threat map aggregation.

Ensure all tests (old + new) pass.
```

---

# **Integration Guidance Summary**

* New file: `qb_engine/prediction.py`
* Update `qb_engine/__init__.py` exports
* Add `docs/prediction_design_spec.md` (this file)
* Add `qb_engine/test_prediction.py`
* No changes to Phase A–D modules
* PredictionEngine receives external instances:

  * legality_checker
  * projection_engine
  * effect_engine
  * scoring_engine