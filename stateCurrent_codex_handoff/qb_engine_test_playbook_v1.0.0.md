# Queen’s Blood Engine Test Playbook
### Version: v1.0.0  
_Comprehensive regression tests for Projection, Placement, Lane Scoring, HandState, and Lockout Detection._

This test suite is designed for use after applying:
- qb_rules_v2 patches  
- qb_engine_v2 patches  
- Patched JSON DB  
- Corrected visualization standards  

Each test is self-contained and includes:
- Test input  
- Expected output  
- Reasoning basis  
- Error signatures if failing  

---

# 1. ProjectionEngine Test Suite

Purpose: confirm correct Δrow/Δcol math and YOU vs ENEMY mapping.

Pattern tests assume the corrected coordinate system:

```

Columns: E(0) D(1) C(2) B(3) A(4)
Rows:    1(0) 2(1) 3(2) 4(3) 5(4)
Δcol = colIndex - 2
Δrow = rowIndex - 2

```

---

## 1.1 Test: Zu Basic Projection (YOU)

Card: **Zu**  
Pattern: `B2P, B4P, D2P, D4P`  
Pattern grid:

```

```
    E   D   C   B   A
```

1      .   .   .   .   .
2      .   P   .   P   .
3      .   .   W   .   .
4      .   P   .   P   .
5      .   .   .   .   .

```

Offsets:

- B2 → (row 1, col 3) → Δrow = -1, Δcol = +1  
- B4 → (row 3, col 3) → Δrow = +1, Δcol = +1  
- D2 → (row 1, col 1) → Δrow = -1, Δcol = -1  
- D4 → (row 3, col 1) → Δrow = +1, Δcol = -1

### **Test 1A — Zu @ BOT-2 (YOU)**

Input:
- root = `(lane=2, col=2)` = BOT-2

Expected projections (YOU → no mirror):

```

MID-3  (2 + -1, 2 + +1)
MID-1  (2 + -1, 2 + -1)
BOT-3  (2 + +1, 2 + +1)
BOT-1  (2 + +1, 2 + -1)

```

If the engine returns anything else → **projection math is incorrect**.

---

## 1.2 Test: Zu @ MID-2 (YOU)

Input:
- root = `(1,2)` = MID-2

Expected:

```

TOP-3
TOP-1
MID-3
MID-1

```

If engine returns MID-2 or invalid tiles → error in Δrow/Δcol.

---

## 1.3 Test: Archdragon Projection (YOU)

Pattern from DB:

```

grid:
. P . . .
. . W X .
. P . . .
. . . . .
. . . . .

```

Offsets:

- B3P → Δrow = -1, Δcol = +1  
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

# 8. Document Status

- Version: **1.0.0**  
- Intended as the regression suite used after applying all Phase 1 patches  
- Engine is considered stable only after 100% pass rate across all tests  

# END DOCUMENT