# Queen’s Blood Engine Test Playbook
### Version: v1.0.0  
_Map of automated tests that keep qbCoach deterministic and aligned with specs._

All tests live under `qb_engine/test_*.py`. Current status: **75/75 passing** (Engine v2.1.0 + Effects v1.1).

---

## 1. Coverage Overview

- **Board & Hydration**
  - `test_board.py`, `test_hydration.py`, `test_board_effective_power.py`
  - Validates BoardState layout, tile ownership/ranks, card hydration integrity.

- **Legality & Placement**
  - `test_legality.py`, `test_place_card.py`
  - Ensures only empty, owned, sufficient-rank tiles are legal; enemy/neutral illegal.

- **Projection & Effective Power**
  - `test_projection_apply.py`, `test_projection_debug.py`
  - Applies W/P/E/X patterns correctly (YOU vs ENEMY mirroring) and keeps pawn deltas/aura markers consistent.

- **Effects v1.1**
  - Registry coverage: `test_effect_registry_coverage.py`
  - On-play/while-in-play basics: `test_effect_engine.py`, `test_effect_on_play.py`, `test_effect_auras.py`
  - Scaling & triggers: `test_effect_scaling.py`, `test_effect_triggers.py`
  - Board ops: `test_effect_spawn_and_replace.py`, `test_effect_expand_positions.py`
  - Scopes & scoring hooks: `test_effect_scopes.py`, `test_effect_score_bonus.py`

- **Scoring**
  - `test_scoring.py`, plus score-modifier coverage in `test_effect_score_bonus.py`
  - Confirms lane power computation, draws, and effect-driven lane_win/lane_min_transfer bonuses.

- **Enemy Observation & Projection**
  - `test_enemy_observation.py` (observations, destroyed markers, tokens, known-deck remaining IDs)
  - `test_enemy_projection.py` (projection symmetry, pawn influence, effect marking in threat maps)

- **Simulation & Prediction**
  - `test_simulation.py` (deterministic draw/play/clone/turn flow)
  - `test_prediction.py` (enemy deck/hand inference within current implementation, move simulation purity, threat map correctness)

- **Coaching**
  - `test_coaching.py` (legal move enumeration, evaluation, ranking, explanations; integrates scoring/prediction outputs)

---

## 2. Links to Specs

- Rules & Engine: `docs/qb_rules_v2.2.4.md`, `docs/qb_engine_v2.1.0.md`
- Effects semantics: `docs/qb_effects_v1.1_status.md`
- Scoring: `docs/scoring_design_spec.md`
- Enemy Observation: `docs/enemy_observation_design_spec.md`
- Simulation/Prediction: `docs/simulation_design_spec.md`, `docs/prediction_design_spec_phase_E.md`
- Coaching: `docs/coaching_design_spec.md`

---

## 3. Key Invariants the Suite Enforces

- Every `effect_id` in the DB exists in the registry; every op type is known.
- Effective power includes base + power_delta + scale_delta + snapshot scaling + auras.
- Destroy ordering: `on_destroy` fires before `on_card_destroyed` watchers; cleanup removes deltas/auras.
- spawn_token/replace_ally/expand_positions behave per v1.1 semantics (owned empty tiles, replaced power, 8-way adjacency).
- Scoring uses effective power, draws give 0, and only effect hooks adjust lane_points.
- Enemy observations are deterministic for a given state sequence and classify tokens by origin.
- Simulation and prediction are pure/non-mutating; cloning preserves RNG; coaching respects legality and scoring outputs.

---

Use this playbook to quickly locate which tests back a behavior before making changes.  
- D2P → Δrow = -? (ignored if absent)  
- C3W → Δrow = 0, Δcol = 0  
- etc. (engine must derive from DB)

### **Expected Behavior (Conceptual)**

- X tile yields **P + E**
- E reduces enemy power by **3** on affected tiles

### Test Input:
AD @ MID-2 (YOU)

Expected:
- Pattern hits: MID-3, TOP-3, BOT-3  
- AD sits in MID-2

If X is placed in wrong direction → horizontal mirroring is being misapplied.

---

# 2. Tile Ownership & Rank Tests

Purpose: ensure P projections change pawn counts correctly.

---

## 2.1 Test: Single P Projection Claiming a Neutral Tile

Board:
```

MID-3 = [N0]

```

Play:
- Place a card whose pattern hits MID-3 with `P`.

Expected:
- Tile becomes owned by YOU with rank = 1
- No card occupies MID-3 (unless pattern = W location)

Failure if:
- Tile stays neutral  
- Rank ≠ 1  
- Tile becomes occupied  

---

## 2.2 Test: Pawn Stacking

Tile initially:
- `[Y1]`

Apply another `P` projection:

Expected:
- `[Y2]`

Apply another:

Expected:
- `[Y3]` (cap at 3)

If the engine increases past 3 or allows enemy to push to `E4` → error.

---

# 3. Move Legality Test Suite

Confirms that the corrected LegalityChecker is used.

---

## 3.1 Test: Cannot Play on Neutral Tile

Input:
- tile.owner = NEUTRAL
- rank ≥ cost

Expected:
- **illegal**

---

## 3.2 Test: Cannot Play on Enemy Tile

Input:
- tile.owner = ENEMY

Expected:
- **illegal**

---

## 3.3 Test: Cannot Play on Tile With Insufficient Rank

Input:
- tile.owner = YOU
- rank = 1
- card.cost = 2

Expected:
- **illegal**

---

## 3.4 Test: Cannot Play on Occupied Tile

Input:
- tile.cardId = "015" (any)

Expected:
- **illegal**

---

## 3.5 Test: Legal Play with Correct Ownership + Rank + Empty

Input:
- tile.owner = YOU
- rank = 2
- tile empty
- card cost = 2

Expected:
- **legal**

---

# 4. Lane Scoring Test Suite

Purpose: ensure lane power = **sum of card.power values**, never ranks.

---

## 4.1 Test: Empty Lane

Lane:
- TOP has no cards

Expected:
- yourLanePower = 0  
- enemyLanePower = 0

---

## 4.2 Test: Mixed Ranks, No Cards

Tiles:
- `[Y3]`, `[Y2]`, `[Y1]`, `[N0]`, `[E3]`

Expected lane power:
- both players = 0

If engine reports any non-zero → rank/pawn confusion.

---

## 4.3 Test: Simple Lane with Cards

Lane tiles:
- `[Y1:GW(2)]`
- `[Y2:ZU(2)]`
- `[E3:FT(3)]`

Expected:
- yourLanePower = 4  
- enemyLanePower = 3

---

## 4.4 Test: Multi-Lane Victory Calculation

TOP:
- You: 3, Enemy: 0 → you win TOP, +3 to your score

MID:
- You: 5, Enemy: 8 → enemy wins MID, +8 to their score

BOT:
- You: 5, Enemy: 7 → enemy wins BOT, +7 to their score

Expected totals:
- You: 3  
- Enemy: 15

Tie-breaker: higher total wins.

---

## Scoring Tests (v3.0)

Playbook coverage mirroring `qb_engine/test_scoring.py`.

### Test S1: Simple Lane, No Effects
- Setup: One lane where YOU have a single card with known power; ENEMY has none. Effect engine returns base power (no buffs/debuffs).
- Expected: `LaneScore.power_you` = card effective power, `power_enemy` = 0, `winner` = "Y", `lane_points` = power_you. `MatchScore.total_you` = lane_points, `total_enemy` = 0, `winner` = "Y", `margin` = total_you.

### Test S2: Effects Change Lane Winner
- Setup: Same lane holds a weaker YOU card and stronger ENEMY card; effect engine buffs/debuffs so YOU wins on effective power.
- Expected: Lane winner determined by **effective** power. Lane totals reflect buffed/debuffed values; MatchScore aligns with that lane outcome.

### Test S3: Draw Lane → Zero Points
- Setup: Both sides have equal effective power in a lane.
- Expected: `LaneScore.winner` = None, `lane_points` = 0. MatchScore adds 0 to both totals for this lane.

### Test S4: Multi-Lane Match Aggregation
- Setup: 3 lanes with mixed outcomes (YOU wins one, ENEMY wins one, third breaks the tie).
- Expected: Each LaneScore matches constructed effective powers; `total_you` sums lane_points where winner == "Y"; `total_enemy` sums lane_points where winner == "E"; MatchScore winner and margin match those totals.

### Test S5: Scoring is Pure and Non-Mutating
- Setup: BoardState with cards placed; deep copy taken before scoring.
- Expected: After `compute_match_score`, board equals the copy; no tiles/pawns/projections change. Confirms scoring layer is read-only.

---

# 5. HandState Test Suite

---

## 5.1 Test: On Play Removes Exactly One Copy

Hand:
```

[GW, GW, AD]

```

Play:
```

GW

```

Expected:
```

[GW, AD]

```

If it removes both → error.  
If it removes none → error.

---

## 5.2 Test: On Draw Appends

Hand:
```

[AD]

```

Draw ZU

Expected:
```

[AD, ZU]

```

---

## 5.3 Test: Mulligan Replacement

Hand:
```

[A, B, C]

```

Replace:
- A and C
With:
- D and E

Expected:
```

[B, D, E]

```

Order-insensitive unless engine requires sorting.

---

## 5.4 Test: Authoritative Sync

Engine hand:
```

[AD, ZU, GW]

```

User reports:
```

[GW, QB]

```

After sync:

Expected:
```

[GW, QB]

```

---

# 6. Lockout Detection Test Suite

---

## 6.1 Test: No Legal Moves → Locked Out

If `generateLegalMoves` returns zero:

Expected:
- engine.correctiveAction = passTurn  
- engine.warnLockedOut = true

---

## 6.2 Test: Exactly One Legal Move → Warning

If only one tile exists where cost ≤ rank:

Expected:
- engine.warnLowMoveCount = true

---

## 6.3 Test: Move That Consumes Last Legal Tile

If playing the recommended card would make `generateLegalMoves()` drop to zero on next turn:

Expected:
- engine MUST warn:
  > “This move may cause self-lockout.”

---

# 7. Composite Integration Tests

These simulate real game sequences.

---

## 7.1 Test: Red XIII MID-3 Sequence

Simulate:

```

Red:
CPW @ MID-5
GW  @ MID-4
FT  @ MID-3

```

Expected:
- Engine recognizes MID-3 crisis
- Engine prioritizes counterplay:
  - ZU @ BOT-2 or
  - AD @ MID-2

If the engine suggests TOP-1 → GW as priority → error.

---

## 7.2 Test: Column-2 Overfill Prevention

Your board:
```

Tiles available:
MID-2 = Y2 (empty)
BOT-2 = Y1 (empty)

```

Engine should warn if:
- You place **heavy finisher** in MID-2 and block ZU

Expected:
- engine.warnGeometryRisk = true

---

## 7.3 Test: Correct Lane Power Under Full Mixed Board

Board snapshot (from previous match):

```

TOP: [Y3:QZ(3)] [ ] [ ] [ ] [ ]
MID: [Y3:GW(2)] [Y2:AD(3)] [E1:FT(3)] [E3:GW(2)] [E1:CPW(3)]
BOT: [Y2:GW(2)] [Y1:AD(3)] [ ] [E1:GW(2)] [E2:OGRE(5)]

```

Expected lane powers:
- TOP: you=3, enemy=0  
- MID: you=5, enemy=8  
- BOT: you=5, enemy=7  

If engine outputs anything else → lane scoring bug.

---

# 8. Turn/Deck Flow (Rules-aligned quick checks)

- Deck size = 15; opening hand = 5 for each side; mulligan once before each side's first turn to redraw to 5.
- Start-of-turn draw is skipped on each side's first turn; empty deck draws do not crash (no card drawn).
- Pass mechanic: two consecutive passes end the game; any successful play resets the pass chain.

---

# 9. Document Status

- Version: **1.0.0**  
- Intended as the regression suite used after applying all Phase 1 patches  
- Engine is considered stable only after 100% pass rate across all tests  

# END DOCUMENT
