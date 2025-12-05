# qb_startup_self_diagnostic_v1.0.4.md  
Queen’s Blood — Startup & Runtime Self-Diagnostic Protocol  
Version 1.0.4 — Epic A, B, C, D Integration

---

# 1. Purpose of the Diagnostic

This document defines how qbCoach_v2 verifies its own operational integrity *before*  
and *during* gameplay. The goals of the diagnostic system are:

- Prevent illegal move suggestions  
- Prevent state drift between user and engine  
- Ensure correct card data hydration  
- Ensure projection correctness  
- Ensure pawn tracking consistency  
- Ensure destruction reversibility  
- Ensure scoring and prediction validity  

The diagnostic runs:

1. **At startup** (first user instruction)  
2. **After every user correction** (board state, hand)  
3. **Whenever a suspicious or contradictory state is detected**  
4. **Before issuing strategic recommendations**

This document is for **engine behavior**, not rules or user-facing coaching.

---

# 2. Diagnostic Severity Levels

- **FATAL** — Cannot continue. Engine must halt and request correction.  
- **ERROR** — Engine state invalid; must reset or overwrite state.  
- **WARNING** — Non-fatal but must be surfaced to user.  
- **INFO** — Normal confirmation output.  
- **PASS** — Test succeeded.  

---

# 3. Startup Diagnostic Checklist (v1.0.4)

At the start of a session, qbCoach_v2 must run *all* checks in this section.
If any FATAL or ERROR result occurs, the assistant must pause and request
user correction before continuing.

---

## 3.1 JSON Card Hydration Test (Epic A)

For each card referenced in:

- hand  
- user’s deck  
- enemy’s deck (if provided)  
- board occupant tiles  

The diagnostic must:

1. Attempt to load card entry from `QB_DB_Complete_v2.json`.  
2. Validate fields:  
   - cost  
   - power  
   - pattern string  
   - 5×5 grid  
   - effect text  

**Failure mode:**  
- Missing entry → FATAL  
- Field mismatch → ERROR  

---

## 3.2 Board Geometry Validation

Validate the presence of:

- Exactly 3 lanes: TOP, MID, BOT  
- Exactly 5 columns: 1–5  
- Each tile containing:
  - owner ∈ {YOU, ENEMY, NEUTRAL}  
  - pawn ranks ∈ {0..3}  
  - occupantCard ∈ (hydrated card | null)

**Failure mode:**  
- Illegal owner → ERROR  
- Rank outside [0,3] → ERROR  
- Board dimensions incorrect → FATAL  

---

## 3.3 Tile Consistency Audit

For each tile:

- If occupied → visibleRank must not be used for placement logic  
- If empty → visibleRank must be equal to `max(playerRank, enemyRank)`  
- Owner must match rank comparison

**Failure mode:**  
- Occupied tile has inconsistent rank usage → ERROR  
- Owner inconsistent with ranks → ERROR  

---

# 4. Legality Engine Diagnostic (Epic B)

LegalityChecker must prove the following:

1. Occupied tiles are **never** legal targets.  
2. ENEMY-owned tiles are **never** legal targets.  
3. NEUTRAL tiles are illegal unless user explicitly sets owner=YOU.  
4. visibleRank ≥ card.cost must be correctly enforced **only on empty tiles**.  

Additionally:

- Every tile you mark as legal in a test board must be legal under these rules.  
- Every tile you mark as illegal must be illegal under these rules.

**Failure mode:**  
- Incorrect legality classification → ERROR  

---

# 5. Projection & PawnDelta Diagnostic (Epic C)

The ProjectionEngine test validates:

### 5.1 Pattern Grid Application Test
The engine must:

- Map pattern coordinates to board coordinates correctly  
- Reject out-of-bounds projections  
- Apply W/P/E/X semantics correctly  
- Respect pawn cap (0–3)  
- Apply flips correctly  
- Update PawnDeltaLayer for every pawn change

Failure = ERROR.

---

### 5.2 PawnDeltaLayer Consistency Test

For every tile:

```

effectivePlayerRank = sum over all cards of pawnDeltas[card].playerRankDelta
effectiveEnemyRank  = sum over all cards of pawnDeltas[card].enemyRankDelta

```

Tile ranks must match these values exactly.

Failure = ERROR.

---

### 5.3 Destruction Reversibility Test

Destroy a test card and verify:

1. All its PawnDeltas are removed.  
2. All effect markers tied to that card are removed.  
3. Tile ownership recomputes correctly.  
4. All other cards’ pawn contributions remain intact.  

Failure = ERROR.

---

# 6. Scoring Diagnostic (Epic D)

The engine must compute:

- strict laneScore (per rules)  
- strict matchScore (per rules)  
- eval(board) (engine scalar)

Tests:

### 6.1 Lane Score Consistency
Ensure laneScore = sum of power of cards YOU control in that lane after effects.

### 6.2 Differential Consistency
```

diffLane = laneScore(YOU) − laneScore(ENEMY)

```
must always match lane computations.

### 6.3 Stability / Access / Effect Factor Tests
Ensure factors stay within allowed ranges:

- stability ∈ [−1.0, +1.0]  
- access ∈ [−1.0, +1.0]  
- effect ∈ [−0.5, +0.5]  

### 6.4 Lane Value Consistency

```

laneValue(L) =
diffLane(L)

* stabilityWeight * stabilityFactor(L)
* accessWeight    * accessFactor(L)
* effectWeight    * effectFactor(L)

```

must equal engine output.

### 6.5 Global eval(board)
```

eval(board) = laneValue(TOP) + laneValue(MID) + laneValue(BOT)

```

Failure = ERROR or FATAL depending on magnitude.

---

# 7. Predictor Diagnostic (Epic D)

PredictorEngine must validate:

### 7.1 Immediate Simulation Validity
Simulate a known legal move and ensure resulting board:

- Applies projection correctly  
- Updates PawnDeltaLayer  
- Updates effects  
- Updates lane scores  

### 7.2 Enemy Reply Enumeration
Given test positions, PredictorEngine must:

- Produce all enemy legal moves  
- Reject illegal replies  
- Simulate each reply deterministically

### 7.3 Worst-Case & Likely-Reply Blend

Ensure:

```

predictedScore(M) =
alpha * worstReplyScore

* (1 - alpha) * likelyReplyScore

```

with alpha = 0.7, unless modified by user.

### 7.4 Final Move Score Ordering

Moves must be returned sorted by:

1. moveScore(M)  
2. Lockout risk  
3. Lane access  
4. Lane stability  
5. Destruction vulnerability  
6. MatchScore pressure  

Any violations → ERROR.

---

# 8. Visual Output Diagnostic

Ensure that board diagrams:

- Use official visualization conventions  
- Mark all effect tiles with ★  
- Do not show pawn ranks on occupied tiles  
- Show rank only on empty tiles  
- Never use ambiguous symbols  
- Are consistent with internal BoardState

Failure = WARNING (non-fatal, but must correct).

---

# 9. Runtime Drift Detection

The engine must continuously monitor:

- rank drift  
- owner drift  
- move legality mismatch between engine and user  
- board mismatch between user snapshot and engine state  
- unexpected PawnDeltas  
- missing or lingering effect markers  

If detected:

- Raise **WARNING**  
- Request corrected board snapshot  
- Replace internal state with the user’s authoritative state

Drift not corrected within 1 cycle → ERROR.

---

# 10. Hard Lockout Detector

The engine must check:

- If YOU have 0 legal moves → FATAL (game over)  
- If YOU have 1 legal move → WARNING (lockout risk)

The same detector is used inside predictor simulations to evaluate moves.

---

# 11. Version History

- **1.0.1** — Original startup diagnostic.  
- **1.0.2** — Epic A & B integration (hydration + legality).  
- **1.0.3** — Epic C integration (projection, PawnDelta, destruction).  
- **1.0.4** — Epic D integration:  
  - Added scoring consistency tests  
  - Added laneValue tests  
  - Added eval(board) validation  
  - Added PredictorEngine sandbox tests  
  - Expanded drift detection  
  - Added moveScore ordering requirements  