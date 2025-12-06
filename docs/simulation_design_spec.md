# **Simulation Layer Design Specification — Phase C (v1.0.0)**

*Authoritative specification for Decks, Hands, GameState, and Turn Mechanics*
*qbCoach deterministic engine — 2025-12-05*

---

# **1. Purpose of Phase C**

The Simulation Layer introduces the first *stateful* subsystem in the qbCoach engine.
It enables:

* deterministic turn execution
* deck + hand modeling
* mulligans
* draw-phase mechanics
* play-from-hand actions
* integration of legality, projection, effects, destruction
* complete state transitions suitable for future prediction and coaching layers

This layer does **not** include:

* prediction
* coaching
* enemy modeling
* heuristics
* search or evaluation functions

Those belong to Phases D–F.

Phase C produces a clean, deterministic, reproducible **GameState machine**.

---

# **2. Architectural Position of Phase C**

The Simulation Layer sits between:

**Rules / Engine Core (Phases A–B)**
→ geometry, projection, effects, scoring

and

**Prediction & Coaching (Phases E–F)**
→ lookahead, recommendation logic

Phase C is the *bridge* that turns the static engine into a playable deterministic simulation.

It must align exactly with:

* board semantics from **qb_rules_v2.2.4.md**
* engine operations from **qb_engine_v2.1.0.md**
* scoring mechanics from **scoring_design_spec.md**
* the developer workflows in **qb_developer_notes_v1.0.0.md**

---

# **3. Deterministic RNG Requirements**

Phase C must use a **dedicated RNG object**, never global randomness.

### 3.1 RNG constraints

* RNG must be seeded via GameState constructor or Deck constructor.
* All random operations flow through this RNG.
* Seed must be stored inside GameState for reproducibility.

### 3.2 Why this matters

* Predictive simulation (Phase E) requires identical replay paths for debugging.
* Deterministic tests require stable sequences.

---

# **3A. Core Turn/Deck Constraints (Rules-Aligned)**

- Deck size: 15 cards per player.
- Opening hand: draw 5 cards; mulligan allowed once before each side's first turn (replace any subset, redraw to 5).
- Each side's first turn: skip the start-of-turn draw; draws begin on that side's second turn.
- Draw on empty deck: no crash, simply no card drawn.
- Game end: all 15 tiles occupied **or** two consecutive passes.
- Hand size: variable; no auto-end on empty deck.

---

# **4. Deck Model Specification**

### **4.1 Deck Responsibilities**

A `Deck`:

* owns a list of *card IDs* (strings referencing JSON DB)
* manages shuffle order (seeded)
* provides deterministic draw operations
* supports mulligans
* supports “card returned to deck” operations (rare, but future-proof)

### **4.2 Deck Initialization**

```python
deck = Deck(card_ids: List[str], seed: Optional[int] = None)
```

Rules:

1. `card_ids` must be exactly length-15 for standard QB decks.
2. No hydration occurs in the Deck.
3. Deck stores the seed and instantiates its own RNG.

### **4.3 Shuffling**

`deck.shuffle()` must:

* produce a deterministic permutation given seed
* never modify original card_ids list order outside the shuffle
* reset draw pointer to zero

### **4.4 Draw Semantics**

```python
card_id = deck.draw()      # Optional[str]; None if empty
card_ids = deck.draw_n(n)  # stops early if deck is empty
```

Rules:

* draw returns the next item in the shuffled sequence
* drawing beyond end of deck does **not** error; returns None
* draw_n returns list preserving order (may be shorter than n)

### **4.5 Mulligan Specification**

Mulligan input:

```python
indices_to_replace: List[int]
```

Process:

1. Extract cards at these indices from opening hand.
2. Put those card IDs back into the unshuffled deck pool.
3. Reshuffle the deck using the *same seed* (or derived seed).
4. Draw replacement cards equal to number of replaced cards.
5. Return the new opening hand.

**Deck must never hydrate card data.**

---

# **5. Hand Model Specification**

Hands contain **hydrated card objects**, not IDs.

### **5.1 Hand Responsibilities**

* Represent a list of hydrated card objects
* Support add / remove operations
* Mirror the true hand state for both YOU and ENEMY
* Maintain order (not required by rules but required for reproducibility)

### **5.2 API Specification**

```python
class Hand:
    def __init__(self, hydrator: CardHydrator)
    def from_card_ids(self, ids: List[str]) -> None
    def add_card(self, card_id: str) -> None
    def remove_index(self, idx: int) -> Card
    def as_card_ids(self) -> List[str]
    def sync_from_ids(self, ids: List[str]) -> None
```

### **5.3 Behavior Guarantees**

* remove_index removes **exactly one instance**
* add_card hydrates via passed-in hydrator
* sync_from_ids overwrites full hand state
* Hands must be cloneable via deep copy

### **5.4 Hand ↔ Deck Relationship**

* Deck provides IDs
* Hand hydrates cards
* GameState orchestrates draw/remove transitions

---

# **6. GameState Specification**

GameState is the authoritative state machine for simulation.

### **6.1 Responsibilities**

* own BoardState
* own PlayerHand & EnemyHand
* own PlayerDeck & EnemyDeck
* own turn number
* own side-to-act
* process turn phases
* ensure deterministic reproducibility
* provide deep cloning

### **6.2 Data Model**

```python
class GameState:
    board: BoardState
    player_hand: Hand
    enemy_hand: Hand
    player_deck: Deck
    enemy_deck: Deck
    turn: int
    side_to_act: Literal["Y", "E"]
    rng: Random  # for future operations if needed
```

### **6.3 Initialization**

Requirements:

* Must be created from:

  * two decks
  * optionally initial hands
* Must support opening-hand draw of **5** cards for each side
* Each side skips its own first start-of-turn draw; draws begin on that side's second turn
* Mulligan: before a side takes its first turn, it may replace any subset of the opening 5 cards once, drawing back to 5

### **6.4 Cloning**

```python
clone = state.clone()
```

Rules:

* Must deep-copy all nested components:

  * board
  * hands
  * decks
  * rng state (crucial)
* clone must be fully isolated (no shared references)

---

# **7. Turn Structure Specification**

Turn structure follows this exact sequence:

### **7.1 Start of Turn**

```python
state.draw_start_of_turn()
```

Rules:

* For each side, the first start-of-turn draw is skipped.
* From the second turn onward for that side, side-to-act draws 1 card from its deck.
* If the deck is empty, no card is drawn and play continues.
* Card is added to corresponding Hand.

### **7.2 Play Phase**

The external controller selects:

```python
(hand_index, lane, col)
```

The engine performs:

1. validate legality via LegalityChecker
2. remove card from hand
3. place card on board
4. apply projection
5. apply effects
6. resolve destruction
7. recompute pawn influence

This is encapsulated in:

```python
state.play_card_from_hand(side, hand_index, lane, col)
```

### **7.3 Cleanup Phase**

* Remove destroyed cards
* Remove invalidated effects
* Recompute aggregate pawn state
* Validate no illegal tiles remain in inconsistent state

### **7.4 End of Turn**

* Advance `side_to_act`
* Increment `turn`
* Track consecutive passes; two consecutive passes end the game
* Game also ends if all 15 tiles are occupied

---

# **8. Integration with Engine Core**

Phase C must call existing subsystems in this order:

### **8.1 Placement**

```python
board.place_card(...)
```

### **8.2 Projection**

* compute_projection_targets
* compute_projection_targets_for_enemy
* apply_pawns_for_you
* apply_pawns_for_enemy

### **8.3 Effects**

* apply_effects_for_you
* apply_effects_for_enemy
* effect_engine.compute_effective_power

### **8.4 Destruction**

* remove card from tile
* remove pawn contributions & effect markers
* apply onDestroy effects

### **8.5 Influence Recompute**

Always call:

```python
board.recompute_influence_from_deltas()
```

---

# **9. Error Handling Requirements**

Phase C must emit deterministic errors when:

* drawing past end of deck
* hand index is invalid
* placement on illegal tile
* projections refer to out-of-bounds tiles
* cloned state is mutated (test must catch this)

---

# **10. Test Specification**

New pytest file: `qb_engine/test_simulation.py`

### Must include:

#### **10.1 Deck Tests**

* seeded shuffle determinism
* mulligan behavior
* draw order consistency

#### **10.2 Hand Tests**

* removal of exactly one instance
* hydration correctness
* sync behavior

#### **10.3 GameState Tests**

* turn draw step
* play phase → projection correctness
* turn sequencing correctness
* deep clone invariants

#### **10.4 Integration Tests**

* multi-turn simulation
* destruction rollback correctness
* effective-power stability across turns

---

# **11. Success Criteria**

Phase C is complete when:

* all simulation tests pass
* all existing engine tests remain green
* GameState supports multi-turn reproducible simulation
* no mutation leaks across clones
* the simulation engine produces consistent logs for any seed

---

# **END OF DOCUMENT**
