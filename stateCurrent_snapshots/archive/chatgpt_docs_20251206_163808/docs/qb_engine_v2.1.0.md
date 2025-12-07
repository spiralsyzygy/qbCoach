# qb_engine_v2.1.0.md  
Queen’s Blood Engine Specification  
Version 2.1.0 — Epic A, B, C, D Integrated

---

# 1. Introduction

This document defines how qbCoach_v2 evaluates board states, applies projections,
simulates moves, and ranks recommendations. Version 2.1.0 upgrades the engine with:

- Epic A: JSON Card Hydration Protocol  
- Epic B: Canonical Tile Model & LegalityChecker overhaul  
- Epic C: Full Projection Engine + PawnDeltaLog  
- Epic D: LanePowerEvaluator v2.1 + Predictor Model (1-ply enemy reply)  

This document contains *engine logic only*.  
Rules-level scoring mechanics (laneScore, matchScore) are defined in
`qb_rules_v2.2.x.md` and must not be duplicated here.

---

# 2. Engine Architecture Overview

The engine consists of the following functional modules:

1. **CardHydrator** — loads authoritative card data from JSON DB (Epic A).  
2. **BoardState** — maintains tile state, ownership, ranks, occupants, effect markers.  
3. **LegalityChecker** — determines legal placements according to Epic B rules.  
4. **ProjectionEngine** — applies P/E/X pattern tiles (Epic C).  
5. **PawnDeltaLayer** — stores per-card pawn contributions, enabling correct removal on destruction.  
6. **CardDestructionEngine** — removes cards, reverses pawn deltas, cleans effects.  
7. **LanePowerEvaluator v2.1** — computes strict lane/match scores and heuristic lane value.  
8. **PredictorEngine (Epic D)** — evaluates a move by simulating the enemy’s best reply.  
9. **MoveRanker** — returns the top recommended moves with a deterministic ranking.

All modules must operate deterministically and must honor the strict rules defined in `qb_rules`.

**Core turn/hand/deck rules (alignment note):**
- Deck size 15 per side; opening hand 5 cards; mulligan once before turn 1 to redraw to 5.
- Each side skips its own first start-of-turn draw; draws begin on that side's second turn. Empty-deck draws do not crash (no card drawn).
- Game end: all tiles filled or two consecutive passes.

---

# 3. JSON Card Hydration (Epic A)

Before using any card (for legality, projection, move evaluation), the engine must
load its full JSON definition:

- cost  
- power  
- pattern string  
- 5×5 grid (W/P/E/X pattern)  
- effect text (if any)

## 3.1 Hydration Requirements

- **Do not infer card data.**
- **Do not use memory** of previous conversations.
- Must perform lookup **every time** a card is referenced unless already cached this session.
- Cached card entries must exactly match JSON DB fields.

## 3.2 Hydration Failure

If a card’s JSON entry cannot be found, the engine must:

1. Pause evaluation.
2. Request user confirmation or JSON snippet.  
3. Not simulate or recommend moves involving that card.

---

# 4. BoardState Model (Epic B & C)

Each tile in the 3×5 grid stores:

```

owner        ∈ {YOU, ENEMY, NEUTRAL}
playerRank   ∈ {0..3}
enemyRank    ∈ {0..3}
visibleRank  = max(playerRank, enemyRank)
occupantCard ∈ Card | null
effectSources = list of cards that currently apply effects to this tile
pawnDeltas    = { cardName → {playerRankDelta, enemyRankDelta} }

```

### Tile Types

- Empty tile → `occupantCard = null`  
- Occupied tile → `occupantCard != null`

Occupied tiles ignore rank for legality.

---

# 5. LegalityChecker v2 (Epic B)

A card may be played on a tile **iff** all conditions are met:

1. Tile is **empty**.  
2. Tile is **owned by YOU** (playerRank > enemyRank OR both 0 and tile designated as YOU).  
3. `visibleRank ≥ card.cost`.

Additional rules:

- Occupied tiles are always illegal.  
- ENEMY tiles are always illegal.  
- NEUTRAL tiles are illegal unless user has set owner=YOU explicitly for that tile.

---

# 6. ProjectionEngine v2 (Epic C)

ProjectionEngine applies pattern-grid coordinates relative to board placement.

## 6.1 Pattern Coordinates

Pattern grid is indexed as:

```

Cols:    E, D, C, B, A  (left → right)
Rows:    1, 2, 3, 4, 5  (top → bottom)
Card W:  at (C,3)  // column C, row 3

```

Mapping to board described in Rules §8.2.

**Coordinate disambiguation:** Pattern grid uses lettered columns (E→A) and numbered rows (1→5).
The game board uses lane names (TOP/MID/BOT) and numbered columns (1–5 left→right). Always
refer to pattern coordinates as `COLROW` (e.g., C2) and board positions as `LANE-COL` (e.g., TOP-1).

## 6.2 Projection Types

- **W** — place card on tile.  
- **P** — pawn update via PawnDeltaLayer.  
- **E** — apply effect marker.  
- **X** — apply P then E.

## 6.3 PawnDeltaLayer (New in Epic C)

Each time a card applies a pawn update to a tile, store:

```

pawnDeltas[cardID].playerRankDelta
pawnDeltas[cardID].enemyRankDelta

```

PawnDeltaLayer ensures:

- Pawn increments/decrements caused by a specific card can be removed when that card dies.
- Aggregate state = sum of pawnDeltas from all cards presently in play.

---

# 7. CardDestructionEngine v2 (Epic C)

When a card is destroyed:

1. Remove the card from its tile.  
2. Remove all **effectSources** tied to this card from all tiles.  
3. Remove all pawn deltas associated with that card:  
```

For each tile:
subtract pawnDeltas[cardID]
clamp ranks to 0..3
recompute owner

```
4. Apply any `onDestroy` effect text.  
5. Update BoardState accordingly.

This ensures correct real-game behavior:  
> The pawn changes of a destroyed card vanish; pawn changes from other cards persist.

---

## Scoring Layer (v3.0)

Purpose: pure, read-only scoring that converts a fully resolved `BoardState` plus `EffectEngine` into lane-level and match-level results without mutating any engine state. Scoring uses **effective power** only; it never reads raw base power directly.

### Data Models

```python
@dataclass
class LaneScore:
    lane_index: int
    power_you: int
    power_enemy: int
    winner: Optional[Literal["Y", "E"]]
    lane_points: int

@dataclass
class MatchScore:
    lanes: List[LaneScore]
    total_you: int
    total_enemy: int
    winner: Optional[Literal["Y", "E"]]
    margin: int
```

- `lane_index`: 0/1/2 for top/mid/bot (engine lane indices).  
- `power_you` / `power_enemy`: sum of **effective** power for each side’s cards in that lane.  
- `winner` (lane): `"Y"` if you lead, `"E"` if enemy leads, `None` if tied.  
- `lane_points`: winner’s lane power; `0` on draws.  
- `total_you` / `total_enemy`: sum of `lane_points` for lanes won by that side.  
- `winner` (match): `"Y"`, `"E"`, or `None` for a full match tie.  
- `margin`: `total_you - total_enemy`.

### API

```python
def compute_lane_power(board: BoardState, effect_engine, lane_index: int) -> LaneScore: ...
def compute_match_score(board: BoardState, effect_engine) -> MatchScore: ...
```

- Both functions are **pure** and **read-only**.  
- They rely on `EffectEngine.compute_effective_power` to obtain per-tile effective power.  
- They do **not** mutate `BoardState`, `PawnDelta`, tiles, pawns, projections, or effects.

### Relationship to Ruleset

Aligned with `docs/qb_rules_v2.2.4.md` and `docs/scoring_design_spec.md`:

- Lane power = sum of **effective** power in that lane.  
- Lane winner = side with higher lane power; draws have no winner.  
- Lane points = winner’s lane power; draws give 0.  
- Match score = sum of lane points for lanes each side wins.  
- Match winner/margin derived from `total_you` vs `total_enemy`.

---

# 8. LanePowerEvaluator v2.1 (Epic D)

LanePowerEvaluator produces:

1. Strict lane scores (per rules doc)  
2. Heuristic lane values (engine-only)  
3. Overall evaluation scalar used by PredictorEngine

## 8.1 Strict Lane Score (Rules-level)

Computed exactly as defined in `qb_rules_v2.2.x`:

```

laneScore(player, lane) =
sum of power of player’s cards in that lane after effects

```

## 8.2 Lane Differential

```

diffLane(L) = laneScore(YOU) − laneScore(ENEMY)

```

## 8.3 Stability Heuristic

Measures how resistant a lane is to immediate counterplay:

- tile accessibility for YOU/ENEMY  
- occupancy distribution  
- risk of imminent destruction  
- structural fragility of lane score  
- ability to reinforce next turn  
- geometric resilience  

Amplitude:

```

stabilityFactor(L) ∈ [−1.0, +1.0]
stabilityWeight = 2.0

```

## 8.4 Accessibility Factor

Determines whether YOU can continue projecting or playing into the lane:

- open tiles belonging to YOU  
- ENEMY accessibility threats  
- long-term lane entry points  

Amplitude:

```

accessFactor(L) ∈ [−1.0, +1.0]
accessWeight = 1.5

```

## 8.5 Effect Factor

Contribution of effect tiles to future potential:

```

effectFactor(L) ∈ [−0.5, +0.5]
effectWeight = 1.0

```

## 8.6 Combined Lane Valuation

```

laneValue(L) =
diffLane(L)

* stabilityWeight * stabilityFactor(L)
* accessWeight    * accessFactor(L)
* effectWeight    * effectFactor(L)

```

## 8.7 Board Evaluation Scalar

The final evaluation scalar is:

```

eval(board) = laneValue(TOP) + laneValue(MID) + laneValue(BOT)

```

Positive → YOU favored.  
Negative → ENEMY favored.

---

# 9. PredictorEngine v1.0 (Epic D)

PredictorEngine evaluates a candidate move M by:

- Simulating M  
- Calculating immediate evaluation  
- Simulating all enemy replies  
- Calculating predicted evaluation  
- Blending the result into a final move score

## 9.1 Immediate Evaluation

```

board_M = simulate(board, M)
score_M = eval(board_M)

```

## 9.2 Enemy Reply Search

Enumerate all enemy-legal moves `{E_i}` from `board_M`.

For each reply:

```

board_Ei = simulate(board_M, E_i)
score_Ei = eval(board_Ei)

```

## 9.3 Worst-Case + Likely Reply Blend

Worst-case reply:

```

worstReplyScore(M) = min(score_Ei)

```

Likely reply uses a filtered subset of moves:

- highest-effect moves  
- moves contesting your lane leads  
- moves opening new projections  
- moves stabilizing enemy lanes

Then compute weighted average over that subset.

Blend:

```

alpha = 0.7  // conservative
predictedScore(M) =
alpha * worstReplyScore(M)

* (1 - alpha) * likelyReplyScore(M)

```

## 9.4 Final Move Score

```

moveScore(M) =
immediateWeight * score_M

* predictiveWeight * predictedScore(M)

```

Defaults:

```

immediateWeight  = 1.0
predictiveWeight = 1.5

```

## 9.5 Move Ranking

Moves sorted by descending moveScore.  
Tie-breakers in order:

1. Lower lockout risk  
2. Higher accessibility  
3. Greater lane stability  
4. Lower destruction vulnerability  
5. Higher total matchScore threat

The final answer returned to the user is:

- Best move (rank 1)  
- Alternates (rank 2–3)  
- Visualized board after best move  
- Lane score summary  
- Effect tiles ★ marked  

---

# 10. Move Simulation (Epic C + D)

Simulation is deterministic:

```

simulate(board, move):
1. Place card (if legal)
2. Apply W tile
3. Apply all P/E/X projections with PawnDeltaLayer
4. Apply onPlay effects
5. Apply destruction resolution
6. Recompute lane scores + eval

```

Simulation has no randomness and respects all pawn caps and ownership rules.

---

# 11. Startup Diagnostic Integration (Epic D)

Startup tests include:

1. JSON hydration test for all cards mentioned in session  
2. PawnDeltaLayer consistency test  
3. Tile ownership integrity test  
4. Scoring consistency test (strict)  
5. LanePowerEvaluator functional test  
6. PredictorEngine sandbox simulation (1-ply)  
7. MoveRanker deterministic ordering test  

Any diagnostic failure requires self-correction before gameplay begins.

---

# 12. Version History

- **2.0.1** — Baseline engine specification  
- **2.0.2** — Epic B integration (canonical tile model, legality corrections)  
- **2.0.3** — Epic C integration (Projection, PawnDelta, destruction engine)  
- **2.1.0** — Epic D integration:
  - Added strict scoring interface  
  - Added LanePowerEvaluator v2.1  
  - Added PredictorEngine (1-ply reply simulation)  
  - Added tie-breaker scoring  
  - Added new diagnostics for scoring and prediction  
