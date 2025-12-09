# Queen’s Blood – Visualization Conventions (v1.0.0)

_This document defines standard notations and diagram styles for all Queen’s Blood explanations, engine specs, and strategy discussions._

---

## 1. Board Layout Conventions

The in-game board is a 3×5 grid:

- **Lanes (rows)**:  
  - `TOP`, `MID`, `BOT`
- **Columns**:  
  - `1, 2, 3, 4, 5` (left → right)

### 1.1 Tile Coordinates

Tiles are written as:

- `TOP-1`, `TOP-2`, …, `TOP-5`
- `MID-1` … `MID-5`
- `BOT-1` … `BOT-5`

When a compact numeric form is needed:

- `lane ∈ {0,1,2}` for `TOP, MID, BOT`  
- `col ∈ {1..5}` for columns

So:

- `TOP-1` ≡ `(lane=0, col=1)`
- `MID-3` ≡ `(lane=1, col=3)`
- `BOT-5` ≡ `(lane=2, col=5)`

### 1.2 Board Diagrams

Standard 3×5 board diagram:

```text
        1     2     3     4     5
      +-----+-----+-----+-----+-----+
TOP   |     |     |     |     |     |
MID   |     |     |     |     |     |
BOT   |     |     |     |     |     |
      +-----+-----+-----+-----+-----+
````

Cards, projections, and effects are layered on top of this grid using the conventions below.

---

## 2. Card Abbreviations

To keep diagrams readable, cards are represented by short uppercase abbreviations.

### 2.1 General Rules

* Abbreviations are typically **2–3 letters**:

  * `ZU` = Zu
  * `AD` = Archdragon
  * `GW` = Grasslands Wolf
  * `QB` = Queen Bee
  * `CPW` = Capparwire
  * `FT` = Flametrooper
* When multiple cards could share the same first letters, add one more character (`CPW`, `ELP`, `OGR`, etc.).

### 2.2 Legend Requirement

Every diagram that uses abbreviations **must include a small legend**, for example:

```text
Legend:
  ZU = Zu
  AD = Archdragon
  GW = Grasslands Wolf
```

This makes diagrams portable and self-explanatory.

---

## 3. Pattern Grid Conventions (5×5)

Each card has a **5×5 pattern grid** with a `W` (the card’s own tile) at the center.

### 3.1 Axes

* **Columns** (left → right): `E D C B A`
* **Rows** (top → bottom): `1 2 3 4 5`

Example layout:

```text
        E    D    C    B    A
      +----+----+----+----+----+
1     |    |    |    |    |    |
2     |    |    |    |    |    |
3     |    |    | W  |    |    |
4     |    |    |    |    |    |
5     |    |    |    |    |    |
      +----+----+----+----+----+
```

### 3.2 Pattern Symbols

Pattern cells use:

* `P` = pawn projection (rank/ownership influence)
* `E` = effect projection (buff/debuff/destroy/etc.)
* `X` = **both** pawn and effect
* `W` = center placement tile

Example (Zu):

```text
        E    D    C    B    A
      +----+----+----+----+----+
1     | .  | .  | .  | .  | .  |
2     | .  | P  | .  | P  | .  |
3     | .  | .  | W  | .  | .  |
4     | .  | P  | .  | P  | .  |
5     | .  | .  | .  | .  | .  |
      +----+----+----+----+----+
```

Pattern strings (e.g. `B2P,B4P,D2P,D4P`) are understood relative to this grid.

---

## 4. Effect & Projection Markers on the Board

When showing **which tiles are affected** by a card’s pattern on the 3×5 board, use **stars**:

* `★` → tile affected by the currently discussed card’s projection (`P`, `E`, or `X`).
  - In live coaching `[BOARD]` snapshots, a `★` inside the brackets also marks any tile currently under one or more active effects (auras/direct effects) that would modify power for a card on that tile.

Example: Zu @ BOT-2 (YOU), showing affected tiles only:

```text
        1     2     3     4     5
      +-----+-----+-----+-----+-----+
TOP   |     |     |     |     |     |
MID   | ★   |     | ★   |     |     |
BOT   |     | ZU  |     |     |     |
      +-----+-----+-----+-----+-----+

Legend:
  ZU = Zu
  ★  = tiles affected by Zu’s pattern
```

Do **not** use `X` visually on the board to mean “effect tile,” since `X` already has a defined meaning in the pattern grid.

---

## 5. Ownership, Rank, and Occupants (Notation)

When needed, tiles can be annotated textually as:

* `[Y2:AD(3)]` → You own the tile (`Y2` rank), card `AD` with power `3`.
* `[E1:FT(3)]` → Enemy owns the tile (`E1` rank), card `FT` with power `3`.
* `[Y1]` → tile you control at rank 1, but **no card**.
* `[E3]` → enemy-controlled tile at rank 3, but **no card**.
* `[N0]` → neutral tile with rank 0 (uncontrolled, empty).

On visual diagrams, these details can be kept in accompanying text or legends rather than drawn directly on the grid to avoid clutter.

---

## 6. Example: Full Board Snapshot

Example combined usage: midgame-position snapshot.

```text
        1         2         3         4         5
      +---------+---------+---------+---------+---------+
TOP   | QZ      |         |         |         |         |
MID   | GW      | AD      | FT★     | GW★     | CPW★    |
BOT   | GW      | AD      |         | GW★     | OGR     |
      +---------+---------+---------+---------+---------+

Legend:
  QZ  = Quetzalcoatl
  GW  = Grasslands Wolf
  AD  = Archdragon
  FT  = Flametrooper
  CPW = Capparwire
  OGR = Ogre
  ★   = tiles affected by the most recently played card’s pattern/effect
```

This style keeps the main board readable while the legend explains abbreviations and effect markers.

---

## 7. Intended Use

This document is meant to be referenced by:

* Rules documents (`qb_rules`),
* Engine specs (`qb_engine`),
* Strategy writeups,
* And any visual explanation of board states.

Any future diagrams or examples should adhere to these conventions to stay consistent and easy to parse.

## END DOCUMENT
