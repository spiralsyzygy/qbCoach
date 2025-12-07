# Phase F — Coaching Layer Design Specification

**Version 1.0.0 — Deterministic Recommendation & Explanation Layer**

---

# 1. Purpose of Phase F

Phase F is the **coach** that sits on top of the deterministic engine.

It consumes:

* Rules-accurate simulation (Phase C)
* Factual enemy observations (Phase D)
* Enemy prediction / threat maps (Phase E)
* Scoring results (v3.0)

and produces:

* Evaluations of the current position
* Ranked move recommendations for YOU
* Human-readable explanations and teaching cues

Phase F **never changes rules or simulation**. It only **queries** lower layers and assembles coaching output.

---

# 2. Architectural Position

```
Rules → Engine Core → Simulation (Phase C) → Observation (Phase D) → Prediction (Phase E) → Coaching (Phase F)
```

Inputs:

* GameState (current deterministic snapshot)
* EnemyObservation (factual enemy data)
* PredictionEngine (Phase E interface)
* ScoringEngine (v3.0)

Outputs:

* State evaluation summary
* Ranked list of candidate moves for YOU
* Per-move evaluation and enemy-response analysis
* Human-readable explanation blocks (for UI / GPT layer)

Phase F must remain:

* **Deterministic** given its inputs
* **Side-aware** (coaching only YOU)
* **Non-mutating** to GameState/EnemyObservation

---

# 3. Design Principles

1. Deterministic first, narrative second.
2. All recommendations must be derivable from:

   * LegalityChecker
   * Simulation engine
   * ScoringEngine
   * PredictionEngine
3. No invented rules or card text.
4. No “hidden” randomness, heuristics must be explicit and testable.
5. Clear separation between:

   * **Numeric evaluation** (engine-facing)
   * **Explanation text** (user-facing)

---

# 4. Core Data Models

The coaching layer defines a small, explicit set of read-only data models.
These live in:

```python
qb_engine/coaching.py
```

and import only **public** types from existing modules (GameState, MatchScore, ThreatMap, etc.).

---

## 4.1 PositionEvaluation

Represents an engine-facing summary of the **current position** from YOUR perspective.

```python
@dataclass
class LaneStatus:
    lane_index: int
    you_power: int
    enemy_power: int
    winner: Optional[str]      # "YOU", "ENEMY", or None
    lane_points: int           # points awarded for this lane (rules v3.0)

@dataclass
class PositionEvaluation:
    match_score: MatchScore            # rules-level scores (v3.0)
    lanes: List[LaneStatus]           # per-lane snapshot
    you_margin: float                 # YOU total points - ENEMY total points
    enemy_best_margin: Optional[float]    # from ThreatMap.best_enemy_score (if available)
    enemy_expected_margin: Optional[float]# from ThreatMap.expected_enemy_score (if available)
    is_clearly_winning: bool
    is_clearly_losing: bool
    is_even: bool
```

Semantics:

* `you_margin` is **always** YOU points minus ENEMY points.
* `enemy_*_margin` is copied directly from PredictionEngine (Phase E) threat map,
  interpreted as a margin from the enemy's perspective.
* Flags (`is_clearly_*`) are derived from thresholds over `you_margin` and (optionally)
  predicted enemy margins. Thresholds are constants defined in `coaching.py`.

---

## 4.2 MoveCandidate

Represents a single **legal YOU move** in the current position.

```python
@dataclass
class MoveCandidate:
    card_id: str                 # ID from qb_DB_Complete_v2.json
    hand_index: int              # index in YOU hand at time of enumeration
    lane_index: int              # 0, 1, 2
    col_index: int               # 0..4
```

Semantics:

* `MoveCandidate` is a thin, deterministic description of "play THIS card HERE".
* It does **not** embed GameState; cloning and simulation are handled by the engine.

---

## 4.3 MoveEvaluation

Represents the evaluation of a move, including enemy responses.

```python
@dataclass
class MoveEvaluation:
    move: MoveCandidate
    you_margin_after_move: float           # points margin after YOUR move, before enemy reply
    you_margin_after_enemy_best: float     # margin after best enemy reply (from enemy POV → YOU POV)
    you_margin_after_enemy_expected: float # margin after expected enemy reply

    position_after_move: Optional[PositionEvaluation]  # optional: immediate post-move eval
    enemy_threat_after_move: Optional[ThreatMap]       # Phase E output for this branch

    quality_rank: int                    # 1 = best move, 2 = second, etc. (assigned later)
    quality_label: str                   # e.g. "best", "good", "playable", "risky", "losing"

    explanation_tags: List[str]          # machine-readable tags, e.g. ["wins_lane_1", "blocks_combo"]
    explanation_lines: List[str]         # short textual cues, e.g. "Secures top lane advantage"
```

Semantics:

* All margins are **from YOUR perspective** (YOU points - ENEMY points), even when
  derived from enemy-centric values in ThreatMap.
* `enemy_threat_after_move` is optional and may be omitted in heavily-pruned modes.
* `explanation_*` fields are **deterministically** generated from numeric and
  structural features (lane winners, margins, tile occupancy, etc.).
* The tag `wins_lane_X` is a **lane-local** signal: it may be present even if the
  overall margin worsens.
* The tag `improves_margin` MUST only be added if
  `you_margin_after_enemy_expected > baseline_you_margin + MARGIN_EPSILON` for this
  position.
* The tag `worsens_margin` MUST only be added if
  `you_margin_after_enemy_expected < baseline_you_margin - MARGIN_EPSILON` for this
  position.
* `baseline_you_margin` is the `you_margin` from `evaluate_position` computed on the
  original pre-move GameState. `MARGIN_EPSILON` is a small constant (e.g. 0.1) to
  avoid tagging noise from tiny numeric differences.

---

## 4.4 CoachingRecommendation

Top-level coaching output for a single position.

```python
@dataclass
class CoachingRecommendation:
    position: PositionEvaluation
    moves: List[MoveEvaluation]          # sorted by you_margin_after_enemy_expected desc
    top_n: int                           # how many moves are considered "top" for UI

    primary_message: str                 # one-sentence summary
    secondary_messages: List[str]        # additional teaching cues
```

Semantics:

* `moves` MUST be pre-sorted by `you_margin_after_enemy_expected` (descending).
* `top_n` is a display hint for UI / GPT layers ("highlight these"), not a new
  ranking.
* Messages are short, factual summaries built from the evaluation data.

---

# 5. CoachingEngine API

The coaching layer is implemented as a single class:

```python
class CoachingEngine:
    def __init__(
        self,
        card_db,
        legality_checker,
        projection_engine,
        effect_engine,
        scoring_engine,
        prediction_engine,
    ):
        ...
```

It must satisfy the following constraints:

* **Read-only** with respect to GameState and EnemyObservation.
* **Deterministic** for fixed inputs and injected engines.
* **YOU-side only**: it never coaches the enemy.

---

## 5.1 enumerate_you_moves(state: GameState) -> List[MoveCandidate]

Behavior:

* Iterate over YOU hand indices and all board tiles.
* For each card + tile, ask `LegalityChecker` (side = "YOU").
* If legal, yield `MoveCandidate(card_id, hand_index, lane_index, col_index)`.

Edge cases:

* If there are **no legal moves**, return an empty list.

---

## 5.2 evaluate_position(state: GameState, enemy_obs: EnemyObservation) -> PositionEvaluation

Behavior:

1. Call `scoring_engine.compute_match_score(state)` to get a `MatchScore`.
2. Derive lane-level data into `LaneStatus` objects.
3. Compute `you_margin` from the MatchScore.
4. Optionally call `prediction_engine.full_enemy_prediction(state, enemy_obs)`
   to obtain a `ThreatMap` and map its values into `enemy_best_margin` and
   `enemy_expected_margin` (converted to YOUR perspective as needed).
5. Set `is_clearly_winning`, `is_clearly_losing`, `is_even` based on thresholds.

This method **does not** enumerate or evaluate any of YOUR moves; it only
summarizes the current position.

---

## 5.3 evaluate_move(

```
self,
state: GameState,
enemy_obs: EnemyObservation,
move: MoveCandidate,
use_enemy_prediction: bool = True,
```

) -> MoveEvaluation

Behavior:

1. Clone the incoming `state` (deep copy).
2. Apply YOUR move using Phase C APIs (e.g. `play_card_from_hand("Y", ...)`).
3. Run projections, effects, and cleanup exactly as in normal turn flow.
4. Call `evaluate_position` on the **post-move** state to obtain
   `position_after_move` (with updated `you_margin`).
5. If `use_enemy_prediction` is True:

   * Ask `prediction_engine.full_enemy_prediction(post_move_state, enemy_obs)`
     to get a `ThreatMap`.
   * Convert ThreatMap scores into `you_margin_after_enemy_best` and
     `you_margin_after_enemy_expected`.
     Otherwise, set these fields equal to `you_margin_after_move`.
6. Compute `baseline_you_margin` by calling `evaluate_position` on the original
   state (if not already cached by the caller).
7. Generate `explanation_tags` and `explanation_lines` from differences between
   pre-move and post-move evaluation (e.g. lane winners changed, margin improved
   or worsened, key threats blocked), applying the `improves_margin` / `worsens_margin`
   rules defined in the MoveEvaluation semantics.

This method must **not** mutate the original `state` or `enemy_obs`.

---

## 5.4 rank_moves(

```
self,
state: GameState,
enemy_obs: EnemyObservation,
moves: List[MoveCandidate],
```

) -> List[MoveEvaluation]

Behavior:

1. For each candidate in `moves`, call `evaluate_move(...)`.
2. Sort resulting `MoveEvaluation` objects primarily by
   `you_margin_after_enemy_expected` (descending), then by
   `you_margin_after_enemy_best`, then by `you_margin_after_move` as tie-breakers.
3. Assign `quality_rank` as 1, 2, 3, ... according to sorted order.
4. Assign `quality_label` using deterministic thresholds on
   `you_margin_after_enemy_expected` relative to the **best** move, e.g.:

   * within 0.5 points of best → "best"
   * within 2 points → "good"
   * negative but not catastrophic → "risky"
   * strongly negative → "losing".

All thresholds and labels are simple constants at top of `coaching.py` so tests
can assert on them.

---

## 5.5 recommend_moves(

```
self,
state: GameState,
enemy_obs: EnemyObservation,
top_n: int = 3,
```

) -> CoachingRecommendation

Behavior:

1. Call `evaluate_position(state, enemy_obs)` → `position_eval`.
2. Call `enumerate_you_moves(state)` → `candidates`.
3. If `candidates` is empty:

   * Return a `CoachingRecommendation` with `moves = []` and a
     `primary_message` indicating "No legal moves available".
4. Otherwise, call `rank_moves(state, enemy_obs, candidates)`.
5. Take `top_n` from the front of the sorted list for highlighting.
6. Synthesize `primary_message` and `secondary_messages` from:

   * top move’s evaluation and explanation lines
   * global `position_eval` flags (winning/losing/even).

This method is the **main entry point** used by higher-level UIs or GPT layers.

---

# 6. Test Plan

Create `qb_engine/test_coaching.py` with the following groups.

---

## 6.1 Move Enumeration Tests

### test_enumerate_you_moves_respects_legality

* Use a small board where some tiles are legal for YOU and others are not.
* Assert that:

  * All returned `MoveCandidate` instances correspond to legal placements
    according to `LegalityChecker` (side = "YOU").
  * No move on ENEMY-owned or occupied tiles appears in the list.

---

## 6.2 Position Evaluation Tests

### test_evaluate_position_uses_scoring_engine

* Build a board with a known MatchScore.
* Call `evaluate_position`.
* Assert that `position.match_score` matches the scoring engine result and that
  `you_margin` is consistent with lane winners.

### test_evaluate_position_includes_prediction_margins

* Inject a fake `PredictionEngine` that returns a known `ThreatMap`.
* Assert that `enemy_best_margin` and `enemy_expected_margin` are correctly
  mapped into `PositionEvaluation` fields.

---

## 6.3 Move Evaluation Tests

### test_evaluate_move_does_not_mutate_original_state

* Clone a known GameState; call `evaluate_move`.
* Assert that the original state is unchanged.

### test_evaluate_move_uses_prediction_engine

* Inject a fake `PredictionEngine` and `ScoringEngine` that report distinct
  values for each move.
* Assert that `you_margin_after_enemy_best` and
  `you_margin_after_enemy_expected` reflect those values.

### test_evaluate_move_generates_explanations

* Use a simple scenario where playing a card clearly wins a lane.
* Assert that `explanation_tags` and `explanation_lines` include signals like
  "wins_lane_X" or equivalent.

---

## 6.4 Ranking and Recommendation Tests

### test_rank_moves_sorts_by_expected_margin

* Construct 3 fake `MoveEvaluation` objects with distinct
  `you_margin_after_enemy_expected` values.
* Pass them through `rank_moves` (bypassing simulation by patching
  `evaluate_move`).
* Assert that the order and `quality_rank` fields are correct.

### test_recommend_moves_returns_top_n

* Use a board with at least 4 legal moves.
* Call `recommend_moves(..., top_n=2)`.
* Assert that `len(reco.moves) >= 4` (all evaluated) but `top_n` is 2.

### test_recommend_moves_handles_no_legal_moves

* Use a state with no legal YOU moves.
* Assert that `moves` is empty and `primary_message` indicates no available
  plays.

---

# 7. Completion Criteria

Phase F is complete when:

* `qb_engine/coaching.py` implements the models and APIs defined here.
* `qb_engine/test_coaching.py` passes with full coverage of enumeration,
  evaluation, ranking, and recommendation logic.
* Phases A–E tests all remain green.
* For a fixed GameState + EnemyObservation + PredictionEngine,
  `CoachingEngine.recommend_moves` is deterministic and stable.

---

# 8. Codex-Ready Implementation Prompt

---

# 9. GPT / UI Integration Guidance (Informative)

This section does not add new engine behavior; it describes how a GPT or UI
layer should consume `CoachingRecommendation` deterministically.

## 9.1 Recommended call pattern

For a given board state and hands that you want to analyze:

1. Construct or obtain a `GameState` representing the current position.

2. Construct or obtain an `EnemyObservation` with all factual enemy data.

3. Instantiate a shared `PredictionEngine` and `CoachingEngine` (or mock them
   in tests / GPT workflows).

4. Call:

   ```python
   reco = coaching_engine.recommend_moves(state, enemy_obs, top_n=3)
   ```

5. Serialize `reco` to a JSON-like structure for the GPT / UI layer. At minimum:

   ```json
   {
     "position": {
       "you_margin": 0.0,
       "enemy_best_margin": 2.0,
       "enemy_expected_margin": -8.7,
       "is_clearly_winning": false,
       "is_clearly_losing": false,
       "is_even": true
     },
     "moves": [
       {
         "card_id": "009",
         "lane_index": 1,
         "col_index": 0,
         "you_margin_after_enemy_expected": 3.3,
         "quality_rank": 1,
         "quality_label": "best",
         "explanation_tags": ["wins_lane_1", "improves_margin"],
         "explanation_lines": [
           "Secures MID lane",
           "Improves overall margin"
         ]
       },
       ...
     ],
     "top_n": 3,
     "primary_message": "Top move improves margin",
     "secondary_messages": [
       "Secures MID lane",
       "Improves overall margin",
       "Position is even; small advantages matter."
     ]
   }
   ```

## 9.2 How a GPT should speak about recommendations

A GPT consuming this output should:

* Treat `quality_rank` and `quality_label` as the **authoritative ranking**.
* Base its natural language on:

  * lane winners, lane points, and `you_margin` from `position`;
  * `you_margin_after_enemy_expected` and tags from the top few moves.
* Never invent rules or card text; if a rule is not encoded in the engine,
  the GPT must not assert it.
* Use tags to drive language, for example:

  * `wins_lane_X` → "This move secures lane X."
  * `improves_margin` → "This move improves your overall position."
  * `worsens_margin` → "This move weakens your position overall, even if it
    wins the lane."

The GPT layer may add stylistic flourishes, but all factual claims about
position, margins, and lane status must be traceable back to
`CoachingRecommendation` fields.

---

# 10. Codex-Ready Implementation Prompt

```text
You are Codex, editing the local deterministic qbCoach engine.

Use the authoritative Phase F spec in docs/coaching_design_spec.md.

Task:
Implement the Coaching Layer (Epic F).

Create:
    qb_engine/coaching.py

Implement the following data models:
    - LaneStatus
    - PositionEvaluation
    - MoveCandidate
    - MoveEvaluation
    - CoachingRecommendation

Implement the CoachingEngine class with methods:
    - enumerate_you_moves(...)
    - evaluate_position(...)
    - evaluate_move(...)
    - rank_moves(...)
    - recommend_moves(...)

Requirements:
    - Deterministic only (no RNG use).
    - Clone-safe: never mutate the input GameState or EnemyObservation.
    - Use existing LegalityChecker, ProjectionEngine, EffectEngine,
      ScoringEngine, and PredictionEngine.
    - All numeric evaluations must be derived from MatchScore and ThreatMap
      values as described in this spec.
    - All explanation text must be generated from numeric and structural
      features, not from invented rules.

Add tests:
    qb_engine/test_coaching.py

Tests must cover:
    - Move enumeration legality.
    - Position evaluation.
    - Move evaluation and enemy prediction usage.
    - Ranking and recommendation behavior.

Ensure all tests (old + new) pass.
```
