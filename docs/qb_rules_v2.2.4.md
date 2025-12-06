# qb_rules_v2.2.4.md  
Queen’s Blood Rules Reference  
Version 2.2.4 — Epic A, Epic B & Epic D Synthesis

---

# 1. Introduction

This document defines the authoritative rules of the Queen’s Blood card game as
implemented by qbCoach_v2.

Version 2.2.4 incorporates:

- Epic A: Card Data Hydration Requirements  
- Epic B: Canonical Tile Model & Placement Legality  
- Epic C: Projection Rules, Pawn Contribution & Destruction Semantics  
- Epic D: Strict Lane & Match Scoring Rules  

These rules govern all engine behavior and take precedence over any earlier
informal descriptions.

---

# 2. Board Structure

Queen’s Blood is played on a **3×5 grid**:

- Lanes: **TOP, MID, BOT**  
- Columns: **1–5** (left to right)

Each tile on the grid has:

- an owner (YOU / ENEMY / NEUTRAL)  
- pawn ranks for each side (0–3)  
- an optional card  
- optional effect markers  

---

# 3. Tile Ownership

Each tile is always in exactly one of these states:

- **YOU** — controlled by the player  
- **ENEMY** — controlled by the opponent  
- **NEUTRAL** — controlled by neither side  

Ownership is derived from pawn ranks on the tile (Section 4) and is used for
placement legality (Section 6).

---

# 4. Pawn Ranks

Each tile tracks pawn ranks for both sides:

- `playerRank ∈ {0,1,2,3}`  
- `enemyRank ∈ {0,1,2,3}`  

Projections may increase or decrease these values, but they must always remain
between 0 and 3 inclusive.

The **visible rank** of a tile is:

```text
visibleRank = max(playerRank, enemyRank)
````

Only empty tiles use visibleRank for placement legality.

---

# 5. Occupied Tiles

A tile is:

* **Occupied** if a card is present on that tile (`occupantCard != null`)
* **Empty** if no card is present (`occupantCard == null`)

Rules regarding occupation:

* An occupied tile can **never** be used to play a new card.
* Occupied tiles may still receive projections (P/E/X) and effects.
* Pawn ranks on occupied tiles do **not** factor into placement legality.

---

# 6. Playing Cards (Placement Legality)

A card may be played on a tile **if and only if** all of the following are true:

1. The tile is **empty** (`occupantCard == null`).
2. The tile is **owned by YOU**.
3. The tile’s **visible rank ≥ card.cost** (as per hydrated card data).

Legal placement does **not** depend on:

* whether the tile was previously higher rank
* effect markers on the tile
* enemy proximity
* any other geometric constraint

Occupied tiles are always illegal as placement targets.
ENEMY and NEUTRAL tiles are always illegal as placement targets.

---

# 7. Decks, Hands, and Turn Flow

- Deck size: **15** cards per player.
- Opening draw: each player draws **5** cards.
- Mulligan: before turn 1, each player may replace any subset of those 5 cards once, drawing back to 5.
- Turn order: P1 starts; turns alternate.
- Start-of-turn draw: draw **1 card**, except **skip on turn 1**. If the deck is empty, no card is drawn but the game continues.
- Hand size: variable; no hard cap and the game does not end on empty deck.
- Passing: a player may pass their turn; the game ends if both players pass consecutively.
- Game end: either all 15 tiles are occupied or there are two consecutive passes.

---

# 7. Card Data Rules (Epic A)

All card attributes used for gameplay must come directly from the official
JSON database: `QB_DB_Complete_v2.json`.

For each card:

* `cost`
* `power`
* `pattern`
* `grid`
* `effect` text

must be read from the JSON entry before the card is used.

The rules engine must **never**:

* infer card data
* approximate card attributes
* rely on memory
* use a card without hydrating its JSON definition

If a card’s JSON entry cannot be located, that card is treated as unknown until
its data is provided.

---

# 8. Projection Rules (Epic C)

This section defines how card patterns modify pawn ranks, ownership, and effect
tiles, and how those changes interact with destruction.

## 8.1 Pattern Grid

Each card has a 5×5 pattern grid relative to its placement tile:

* Columns: **E, D, C, B, A** (left → right, relative to the card)
* Rows: **1–5** (top → bottom)
* The placement tile **W** is always at grid coordinate **(C,3)**.

Pattern entries:

* `W` = placement tile (card’s own tile)
* `P` = pawn projection
* `E` = effect-only projection
* `X` = pawn + effect projection

## 8.2 Mapping to Board

If a card is placed on board tile `(lane, col)`, each pattern tile maps to a
board tile as follows:

Let `(pRow, pCol)` be a pattern coordinate, with C = row index 2 and column 3
= index 2. Then:

```text
  rowOffset = pRowIndex − 2   # numbers 1..5 (top→bottom) become offsets −2..+2 relative to W at row 3
  colOffset = pColIndex − 2   # letters E,D,C,B,A (left→right) become offsets −2..+2 with W at column C

  lane' = lane + rowOffset
  col'  = col  + colOffset
```

The projection applies only if `(lane', col')` lies within the 3×5 board.

**Coordinate disambiguation:** Pattern grid uses lettered columns (E→A) and numbered rows (1→5).
The game board uses lane names (TOP/MID/BOT) and numbered columns (1–5 left→right). Keep these
two systems distinct in code, logs, and docs to avoid numeric label collisions.

From a rules perspective, this mapping defines the relative positions of P/E/X
tiles around W. The engine may mirror or transform coordinates for enemy
perspective as long as these relationships are preserved.

## 8.3 Projection Types

* **W (Placement)**
  The card’s own placement tile:

  * A card is placed at W.
  * This tile becomes occupied by that card.
  * Ownership is set to the card’s controller (YOU / ENEMY).
  * W does not change pawn ranks or apply effects unless specified by the
    card’s effect text.

* **P (Pawn)**
  Applies the pawn rules (Section 8.4) to the target tile:

  * May increase or decrease pawn ranks.
  * May flip ownership.

* **E (Effect)**
  Applies an effect marker to the target tile:

  * No change to pawn ranks.
  * Effect duration is governed by Section 8.6.

* **X (Pawn + Effect)**
  Applies both:

  * P (pawn rules) then E (effect marker).

All projections must respect:

* rank caps (0–3 per side)
* ownership rules (Section 3 and 4)
* placement legality rules (Section 6)

## 8.4 Pawn Application Model (Rules-Level)

For each P or X tile, when **YOU** project onto:

* an **ENEMY-owned** tile:

```text
enemyRank  -= 1
playerRank += 1
if enemyRank < 0 → enemyRank = 0
if playerRank > 3 → playerRank = 3
if enemyRank = 0 and playerRank > 0 → tile flips to YOU
```

* a **YOU-owned** or **NEUTRAL** tile:

```text
playerRank += 1
if playerRank > 3 → playerRank = 3
```

For **ENEMY** P/X projections, the model is mirrored:

```text
playerRank -= 1
enemyRank  += 1
if playerRank < 0 → playerRank = 0
if enemyRank > 3 → enemyRank = 3
if playerRank = 0 and enemyRank > 0 → tile flips to ENEMY
```

After each pawn update:

* Clamp both `playerRank` and `enemyRank` into the range [0,3].
* Set `visibleRank = max(playerRank, enemyRank)`.
* Recompute `owner`:

  * YOU if `playerRank > enemyRank`
  * ENEMY if `enemyRank > playerRank`
  * NEUTRAL if both 0

Repeated projections across multiple turns accumulate according to these rules
and may flip tiles multiple times (“flip chains”).

## 8.5 Card Destruction and Pawn Contribution

Certain effects reduce a card’s power or explicitly state that the card is
destroyed.

When a card is destroyed:

1. The card is removed from its W tile (the tile becomes empty).
2. All **whileInPlay** effects originating from that card end, and any effect
   markers tied solely to that card are removed.
3. The pawn contributions made by that card’s projections are removed:

   * All pawn changes that originated from that card’s P/X projections (and any
     pawn-modifying effects in its script) are undone.
   * Pawn changes from **other cards** remain intact.
4. Ownership and visibleRank on affected tiles are recomputed from the
   remaining pawn ranks.
5. Any explicit `onDestroy` effect text on the card is then applied (which may
   further change pawn ranks or effects).

Intuitively:

> When a card leaves play, the pawns it generated are treated as if they never
> occurred, while all other cards’ contributions to pawn state persist.

## 8.6 Effect Lifetimes

Effect markers placed via E or X tiles:

* Exist only while the source card remains in play, unless its effect text
  specifies persistence.
* Are removed when the source card is destroyed or otherwise leaves the board.

Effects may modify power, rank, or other properties as described in the card’s
effect text, but they never override the basic pawn rules unless explicitly
stated.

## 8.7 Multi-Turn Behavior

Tiles may receive projections from multiple cards over multiple turns.

At all times:

* Pawn state on a tile is the aggregate of all pawn contributions from cards
  **still in play**.
* Destroying a card removes only that card’s contribution, and leaves other
  contributions untouched.
* Flip chains and multi-turn dynamics follow from sequential application of
  the pawn rules in Section 8.4, with destruction treated as removing that
  card’s pawn history from the aggregate.

---

# 9. Scoring (Epic D — Rules-Level)

This section defines how lane scores, lane winners, and the match winner are
determined. It is intentionally minimal and contains **no heuristics**.

## 9.1 Lane Score

For each lane (TOP, MID, BOT), each player has a **lane score**:

```text
laneScore(player, lane) =
    sum of the current power of that player’s cards in that lane,
    after all active effects have been applied.
```

Destroyed cards (or empty tiles) contribute nothing.

## 9.2 Lane Winner

For each lane:

* The player with the higher laneScore in that lane is the **lane winner**.
* If both players have equal laneScore in that lane, that lane has **no
  winner** and grants no points to either side.

## 9.3 Match Score

Each player’s **match score** is the sum of the lane scores from all lanes that
player wins:

```text
matchScore(player) =
    sum over all lanes L that player wins of laneScore(player, L).
```

Lanes that are tied (no winner) contribute nothing to either player’s
matchScore.

## 9.4 Match Winner

The **match winner** is the player with the higher matchScore after all lanes
have been resolved.

If both players have equal matchScore, the match is a tie.

This section does not describe any heuristic or strategic evaluation – it only
defines how the game’s scoring and winning conditions work.

---

# 10. Canonical Tile Semantics Appendix (Epic B)

This appendix clarifies the canonical semantics of tile state.

## 10.1 Empty vs Occupied

* `occupantCard == null` → tile is **empty**
* `occupantCard != null` → tile is **occupied**

Only empty YOU tiles may receive new card placements.

## 10.2 Ownership

* Ownership is derived from pawn ranks on the tile:

  * YOU if `playerRank > enemyRank`
  * ENEMY if `enemyRank > playerRank`
  * NEUTRAL if both 0
* For gameplay purposes, ownership is treated as fixed at the moment the user
  provides a board snapshot, until new projections resolve.

## 10.3 Ranks

* `playerRank` and `enemyRank` are always between 0 and 3.
* `visibleRank = max(playerRank, enemyRank)`.
* Ranks matter **only** on empty tiles for placement legality.

## 10.4 Placement Legality

A card may be played on a tile **if and only if**:

1. The tile is empty.
2. The tile is owned by YOU.
3. The tile’s visible rank is greater than or equal to the card’s cost.

Anything else is illegal without exception.

---

# 11. Version History

* **2.2.1** — Integrated Epic A patches.
* **2.2.2** — Added canonical tile semantics (Epic B), clarified legality
  requirements, and reorganized for consistency with engine v2.0.2.
* **2.2.3** — Integrated Epic C projection rules:

  * Formal pattern grid definition
  * P/E/X projection semantics
  * Pawn application model (rules-level)
  * Card destruction + pawn contribution removal
  * Effect lifetime behavior
  * Clarified multi-turn tile behavior
* **2.2.4** — Integrated Epic D strict scoring:

  * Defined laneScore, lane winner, matchScore, match winner
  * Removed any incorrect “2 lanes = win” implication
  * Kept scoring purely mechanical and heuristic-free
