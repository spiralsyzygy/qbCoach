# **Phase E — Prediction Engine Development Kickoff Spec (v0.1)**

### *Foundational Design, Scope, Milestones, and Integration for Prediction Engine v2*

*Last updated: 2025-12-08 — prerequisites satisfied by Phase G v0.3*

---

# **0. Purpose**

Phase E upgrades the **Prediction Engine** from a simple “one-step, deterministic best-response evaluator” into a **multi-step, probabilistic threat model** that:

1. Anticipates **likely enemy moves**, not just the optimal one.
2. Evaluates **N-step future states** deterministically with controlled branching.
3. Produces structured **risk profiles**, **threat clusters**, and **margin volatility**.
4. Outputs a machine-readable data model that is stable, testable, and narrative-ready for the GPT coaching layer.

Phase E is **not** a search tree explosion.
It is a controlled, deterministic, explainable forecast system built on:

* The existing deterministic engine
* A probabilistic enemy-move distribution model
* A lane-pressure + tile-influence evaluation framework
* Lightweight multi-branch lookahead with pruning

Phase E is foundational for advanced coaching, automated analysis, and future reinforcement extensions in Phase F.

---

# **1. Goals of Phase E**

### **1.1 Expand prediction from “single-turn best enemy reply” → “multi-turn shaped threat model”**

The current engine computes:

* Best YOU move
* Best ENEMY reply
* Expected margin after one cycle

Phase E adds:

* **Multiple plausible enemy replies**, weighted
* Impact of those replies over **2–3 turns**
* **Volatility ranges** (best → median → worst threat-of-collapse)
* **Threat clusters** for lanes
* **Stabilized position delta** (how your move shapes the next several turns)

---

### **1.2 Determinism + Probability**

The prediction engine remains **deterministic** in computation but returns **probabilistic summaries** derived from:

* Move-quality heuristics
* EnemyObservation deck inference
* Weighted distribution of enemy tile pressures
* Current lane-power dynamics
* Tile-effect overlays (`★`)

No randomness is introduced; probabilities are shaped outputs, not random sampling.

---

### **1.3 Produce a machine-readable PredictionModel v2**

This structured model will include:

* **enemy_distribution**: list of candidate moves with weights
* **lane_threat**: per-lane pressure, collapse risk, stabilization likelihood
* **path_evals**: evaluation of 2–3 turn lookaheads with pruning
* **volatility_index**: how swingy the position is
* **next_turn_surface**: which tiles will matter most
* **state_rationale**: minimal trace for explanation

GPT will narrate this differently depending on **coaching_mode** (strict vs strategy).

---

# **2. Non-goals (What Phase E will NOT do)**

To avoid scope creep:

* No Monte Carlo rollouts
* No stochastic simulation
* No beam search beyond bounded pruning
* No deep learning components
* No changes to legality, effects, projections, or scoring
* No changes to deterministic engine core state representation
* No enemy hand inference beyond what EnemyObservation supports

Phase E only **reads** engine state; it does not modify it.

---

# **3. Architecture Overview**

Phase E introduces **three new modules**:

---

## **3.1 EnemyMoveDistribution (EMD)**

Input:

* Current board
* EnemyObservation state
* Legal enemy moves
* Card categories (Early, Midrange, Scaling, Closer)
* Lane-pressure signals
* Effect overlays

Output:

A deterministic list:

```json
[
  { "move": <Move>, "weight": 0.32, "tags": ["lane_pressure", "tempo_gain"] },
  { "move": <Move>, "weight": 0.27, "tags": ["swing_play"] },
  ...
]
```

Weights determined by:

* Historical lane preferences for this archetype
* Board-local tactical heuristics
* Engine-quality score for each move normalized into a distribution
* Influence from observed enemy plays (EnemyObservation)

Critical invariant:

> The sum of weights MUST equal 1.0, and the ranked ordering must be deterministic.

---

## **3.2 PathEvaluator (N-step deterministic lookahead)**

For each candidate enemy move (top K weighted):

1. Apply enemy move
2. Compute updated lane-power / score
3. Evaluate YOU’s best reply
4. Optionally evaluate enemy’s next reply (depth 2 or 3 total turns)
5. Compute margin deltas and volatility

This produces:

```json
{
  "path": ["E:moveA", "Y:moveB", "E:moveC?"],
  "final_margin": +7,
  "lane_status": { "top": "winning", "mid": "volatile", "bot": "losing" },
  "volatility": 0.43
}
```

Pruning strategy:

* Only consider:

  * Top K enemy moves (weighted)
  * Top M replies by YOU
* Abort early if margin becomes stable (convergence detection)
* Hard cap on total branches ≤ 20

---

## **3.3 PredictionSynthesizer**

Combines:

* Weighted enemy distributions
* N-step path evaluations
* Lane threat scores
* Effect overlays (★) and influence maps
* Existing v1 prediction outputs

Produces unified **PredictionModel v2**:

```json
{
  "expected_margin": +4,
  "median_margin": +2,
  "worst_threat": -3,
  "lane_threat": {
    "top": 0.18,
    "mid": 0.62,
    "bot": 0.44
  },
  "volatile_lanes": ["mid"],
  "enemy_top_lines": [...],
  "you_best_lines": [...],
  "danger_tiles": [(row,col), ...],
  "notes": ["mid lane likely contested next turn"]
}
```

---

# **4. Data Structures (Draft)**

## **4.1 `EnemyDistributionEntry`**

```python
@dataclass
class EnemyDistributionEntry:
    move: Move
    weight: float
    tags: list[str]
    projected_margin: int
```

---

## **4.2 `PathEval`**

```python
@dataclass
class PathEval:
    sequence: list[Move]
    final_margin: int
    lane_power: dict[str,int]
    volatility: float
```

---

## **4.3 `PredictionModelV2`**

```python
@dataclass
class PredictionModelV2:
    expected_margin: int
    median_margin: int
    worst_threat: int
    lane_threat: dict[str,float]
    volatile_lanes: list[str]
    enemy_distribution: list[EnemyDistributionEntry]
    path_evaluations: list[PathEval]
    danger_tiles: list[tuple[int,int]]
    notes: list[str]
```

---

# **5. Test Plan – `test_prediction_v2.py`**

## **5.1 EMD tests**

* Distribution sums to 1.0
* Deterministic under same input
* Weighted order stable
* Tags reflect correct lane-pressure reasons
* Unknown enemy archetype falls back to uniform priors

---

## **5.2 PathEvaluator tests**

* Applies moves correctly
* Honors pruning thresholds
* Depth-limited lookahead works
* Volatility metric deterministic
* Special-case tests:

  * All lanes stable
  * Highly volatile mid-lane
  * Strong effect-tile influence (★)

---

## **5.3 PredictionSynthesizer tests**

* Correct aggregation of margins
* Lane threats increase when enemy has weighted plays in that lane
* Danger tiles reflect overlapping threat maps
* Snapshot-to-prediction consistency verified across simple scenarios

---

# **6. Integration Points**

### **6.1 Engine Layer**

No change. Only read API calls:

* legal_enemy_moves
* apply_enemy_move (in sandbox copy of state)
* scoring.evaluator
* projection/ownership updates
* effect engine (★ overlay already available)

---

### **6.2 CLI**

No changes required.

---

### **6.3 GPT Layer**

Updates needed:

* Strict mode → narrate v2 prediction facts only
* Strategy mode → can discuss lane volatility, threat clusters, risk bands
* New prediction summary UI:

  * “Expected margin”
  * “Risk range”
  * “Enemy pressure distribution”
  * “Volatile lanes”
  * “Danger tiles (★)”
  * “Likely enemy focal point next turn”

---

# **7. Milestones / Development Plan**

## **Milestone E1 — EMD Prototype**

* Implement weight model
* Validate determinism + sum=1
* 10–15 tests

## **Milestone E2 — PathEvaluator**

* Depth-2 deterministic lookahead
* Branch pruning
* Volatility metric
* 20–30 tests

## **Milestone E3 — Synthesizer**

* Unified PredictionModel v2
* Convert v1 prediction + new signals
* CLI debug output (optional)
* 15 tests

## **Milestone E4 — GPT Integration**

* Update strict & strategy narration
* Update live coaching protocol (v0.4)
* Update qb_uxGPT_core_prompt to v1.2

## **Milestone E5 — Tuning & Validation**

* Scenario benchmarks
* Stress tests (board with high effect density)
* “Corner case” lane dynamics
* Final test suite: ~120–140 tests total

---

# **8. Completion Criteria**

Phase E is complete when:

✔ PredictionModel v2 implemented
✔ All modules deterministic
✔ All tests passing
✔ CLI + GPT integration validated
✔ Strict mode fully reliable
✔ Strategy mode narrative alignment verified
✔ No conflicts with Phase G architecture
✔ PredictionModel backward compatibility preserved

---

# **END OF Phase E Development Kickoff Spec v0.1**