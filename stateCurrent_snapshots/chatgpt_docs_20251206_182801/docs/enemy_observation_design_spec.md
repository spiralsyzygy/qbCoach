## 1. Purpose of Phase D

The **Enemy Observation Layer** is a *purely factual* subsystem that tracks what is known about the enemy’s behavior and resources during a match.

It **does not**:

- predict future plays,
- assign probabilities to unseen cards,
- recommend moves.

Those belong to the **Prediction & Coaching** phases.

Instead, Phase D answers:

- What enemy cards have we *definitely* seen so far?
- Where and when were they played?
- Which board tiles and pawns currently belong to the enemy?
- Which enemy cards are still guaranteed to remain in their deck (in “known deck” mode)?
- What tokens or summoned units have appeared?

This layer is fed by **GameState** (Phase C) and feeds into **Prediction / Coaching** (Phases E/F).

---

## 2. Architectural Position

**Below Phase D:**

- Rules & engine core: `BoardState`, projection, effects, destruction, scoring.
- Simulation Layer (Phase C): `Deck`, `Hand`, `GameState`, turn structure.

**This Phase (D):**

- Adds an `ObservationState` that watches how `GameState` evolves over time.
- Maintains a historical + current view of enemy activity.

**Above Phase D:**

- Prediction Layer (Epic E) will:
  - Take observed facts from this layer.
  - Enumerate plausible futures.
- Coaching Layer (Epic F) will:
  - Use prediction and scoring to recommend plays.

The observation layer contains only **facts derivable from the current and past GameState**.  
No guesses, no heuristics.

---

## 3. Design Principles & Constraints

1. **Factual only**  
   - Store only what is *certain* from `GameState` (board, hands, decks, logs).
   - Do not invent or infer unseen cards.

2. **Deterministic & reproducible**  
   - Observation must be fully determined by:
     - The initial decks
     - The sequence of GameState transitions

3. **Read-only wrt GameState**  
   - Observation *reads* GameState but never mutates it.
   - Updates to observation are made via explicit calls (e.g., `update_from_game_state` or `register_enemy_play`).

4. **Side-agnostic core, enemy-focused API**  
   - Core types can work for either side.
   - Public API is convenience-wrapped around “enemy” for qbCoach usage.

5. **Compatible with cloning**  
   - Observation state must be cloneable alongside GameState for future search/prediction.

---

## 4. Core Data Models

### 4.1 ObservedCard

Represents a single card instance we have observed at some point in the match.

```python
from dataclasses import dataclass
from typing import Literal, Optional

Side = Literal["Y", "E"]

@dataclass
class ObservedCard:
    card_id: str
    side: Side
    origin: Literal["deck", "token", "effect", "unknown"]
    turn_observed: int
    lane_index: Optional[int]  # None if not on board (e.g., revealed in hand)
    col_index: Optional[int]
    destroyed_on_turn: Optional[int] = None
````

**Semantics:**

* `card_id`: maps to entry in `qb_DB_Complete_v2.json`.
* `side`: `"Y"` or `"E"` (which player the card belongs to).
* `origin`:

  * `"deck"`: came from the opponent’s normal deck.
  * `"token"`: created by a card/effect (not part of main deck).
  * `"effect"`: revealed only within an effect (if such cases exist later).
  * `"unknown"`: origin unclear.
* `turn_observed`: first turn where we could see this card as a *card instance*.
* `lane_index` / `col_index`:

  * Last known board position if currently on board.
  * `None` if only revealed in another way (e.g., hand reveal or effect).
* `destroyed_on_turn`:

  * `None` if still in play or unknown.
  * Turn number when the card left the board (if trackable).

---

### 4.2 EnemyDeckKnowledge

Represents what we know about the enemy deck in **known-deck mode**.

```python
from dataclasses import dataclass, field
from typing import List, Set

@dataclass
class EnemyDeckKnowledge:
    # Full known deck list (card IDs), if available.
    full_deck_ids: List[str] = field(default_factory=list)

    # Card IDs we have observed the enemy play (non-token).
    played_ids: List[str] = field(default_factory=list)

    # Derived sets for quick queries.
    remaining_ids: List[str] = field(default_factory=list)
```

**Modes:**

* When `full_deck_ids` is empty:

  * The engine is in **unknown deck mode**.
  * `remaining_ids` is not meaningful; we only track `played_ids`.
* When `full_deck_ids` is present:

  * The engine is in **known deck mode** (e.g., scripted battles, known lists).
  * `remaining_ids` = `full_deck_ids` minus `played_ids` (multiset semantics).

> Phase D only manages **facts** about remaining cards when the full deck is known.
> Phase E will use this for prediction.

---

### 4.3 EnemyObservationState

Central structure of Phase D.

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class EnemyObservationState:
    # All observed cards (both sides), for replay / debugging.
    observations: List[ObservedCard] = field(default_factory=list)

    # Convenience: filter of observations for enemy cards only.
    enemy_observations: List[ObservedCard] = field(default_factory=list)

    # Enemy deck knowledge (used when initial deck is known).
    enemy_deck_knowledge: EnemyDeckKnowledge = field(default_factory=EnemyDeckKnowledge)

    # Turn number of last update (for sanity checks).
    last_updated_turn: int = 0
```

Responsibilities:

* Maintain a chronological record of observed card events.
* Provide quick access to:

  * current enemy board cards,
  * destroyed enemy cards,
  * remaining enemy deck (in known-deck mode).

---

## 5. Public API

File target: `qb_engine/enemy_observation.py`

### 5.1 Construction and Reset

```python
class EnemyObservation:
    def __init__(self, known_enemy_deck_ids: Optional[List[str]] = None): ...
    def reset(self) -> None: ...
```

* `known_enemy_deck_ids`:

  * If provided → populates `enemy_deck_knowledge.full_deck_ids`.
  * If `None` → unknown-deck mode.

* `reset()`:

  * Clears all observations.
  * Resets `enemy_deck_knowledge` to initial known deck (if any).
  * Sets `last_updated_turn = 0`.

---

### 5.2 Updating from GameState

Observation should be updated from `GameState` at well-defined points, typically **once per turn** after all effects and destruction have resolved.

```python
from qb_engine.game_state import GameState

class EnemyObservation:
    def update_from_game_state(self, state: GameState) -> None: ...
```

**Behavior:**

1. Inspect `state.board`:

   * For each enemy card on the board, ensure there is a corresponding `ObservedCard` entry:

     * If new: add an observation with `origin="deck"` or `"token"` depending on the card’s JSON data (e.g., if `category == "Token"`).
     * If existing: update `lane_index` and `col_index`.

2. Detect destroyed enemy cards:

   * Compare active enemy cards on board vs previous observations.
   * For any `ObservedCard` that previously had a board position but is no longer on the board:

     * Set `destroyed_on_turn = state.turn`.

3. Update `last_updated_turn` to `state.turn`.

4. If in known-deck mode:

   * For any newly observed enemy card with `origin="deck"`:

     * Append to `enemy_deck_knowledge.played_ids`.
   * Recompute `enemy_deck_knowledge.remaining_ids` using multiset semantics.

**Important:**
`update_from_game_state` must be **purely observational** — it does not change `state` or any of its subcomponents.

---

### 5.3 Explicit Registration Helpers

In addition to `update_from_game_state`, provide explicit helper methods when the engine knows about an observation event at a specific time (e.g., when an enemy card is played):

```python
class EnemyObservation:
    def register_enemy_play(
        self,
        card_id: str,
        lane_index: int,
        col_index: int,
        turn: int,
        origin: Literal["deck", "token", "effect", "unknown"] = "deck",
    ) -> None: ...
```

Behavior:

* Add a new `ObservedCard` instance for enemy side.
* If in known-deck mode and `origin == "deck"`, update `played_ids` and `remaining_ids`.

This can be called from the code path handling enemy plays (e.g., inside `GameState.play_card_from_hand` when `side == "E"`).

---

### 5.4 Query API

Phase D should provide **simple, factual queries**:

```python
class EnemyObservation:
    def get_enemy_board_cards(self) -> List[ObservedCard]: ...
    def get_enemy_destroyed_cards(self) -> List[ObservedCard]: ...
    def get_enemy_tokens(self) -> List[ObservedCard]: ...
    def get_known_enemy_deck_remaining_ids(self) -> List[str]: ...
    def get_all_enemy_observations(self) -> List[ObservedCard]: ...
```

Semantics:

* `get_enemy_board_cards`:

  * Observed enemy cards with `destroyed_on_turn is None` and valid lane/col.
* `get_enemy_destroyed_cards`:

  * Observed enemy cards with `destroyed_on_turn is not None`.
* `get_enemy_tokens`:

  * Observed enemy cards with `origin == "token"`.
* `get_known_enemy_deck_remaining_ids`:

  * Returns `enemy_deck_knowledge.remaining_ids` (only meaningful in known-deck mode).
* `get_all_enemy_observations`:

  * Returns a copy of `enemy_observations` for debugging or future layers.

No probabilities, no ranking, no scoring — just raw factual output.

---

## 6. Integration with GameState and Simulation

Observation must be updated **synchronously** with simulation, but never drives it.

### 6.1 Update Timing

Recommended integration points:

* After each full turn (post-cleanup):

  * Call `enemy_observation.update_from_game_state(state)`.

* When the enemy plays a card:

  * At the point where `GameState.play_card_from_hand("E", ...)` succeeds:

    * Call `enemy_observation.register_enemy_play(...)`.

### 6.2 Storage and Cloning

`GameState` itself **does not own** EnemyObservation.
Instead, prediction/coaching layers will own a composite structure like:

```python
@dataclass
class AnnotatedState:
    state: GameState
    enemy_observation: EnemyObservation
```

This allows:

* Cloning both state and observation together for search.
* Clean separation of concerns.

For now, Phase D only defines `EnemyObservation` and its behavior; the ownership model for higher-level composites can be specified in the Prediction/Coaching spec.

---

## 7. Error Handling and Invariants

### 7.1 Invariants

* No `ObservedCard` for side `"E"` may exist without a corresponding `card_id` known to the JSON DB.
* In known-deck mode:

  * The multiset of `played_ids` + `remaining_ids` must always equal `full_deck_ids`.
* `last_updated_turn` must never decrease.

### 7.2 Error Conditions

Observation should raise explicit errors (or assertions in test mode) if:

* `register_enemy_play` receives a card_id not present in the JSON DB (unless explicitly allowed for future custom cards).
* Known-deck multiset invariants are violated (e.g., the enemy appears to have played more copies of a card than exist in the deck).

---

## 8. Test Specification (Phase D)

New test file: `qb_engine/test_enemy_observation.py`

### 8.1 Basic Observation Tests

1. **test_register_enemy_play_creates_observation**

   * Call `register_enemy_play` with a sample card ID and coordinates.
   * Assert that `enemy_observations` contains one entry with matching data.

2. **test_update_from_game_state_tracks_board_presence**

   * Prepare a GameState with an enemy card on the board.
   * Call `update_from_game_state`.
   * Assert that `enemy_board_cards` includes that card.

3. **test_destroyed_cards_are_marked_with_turn**

   * Set up a state where an enemy card is present.
   * Create a new state where that card is gone and `turn` is incremented.
   * Call `update_from_game_state` twice.
   * Assert that `destroyed_on_turn` was set correctly.

### 8.2 Known-Deck Mode Tests

4. **test_known_deck_remaining_ids_updates_as_enemy_plays**

   * Initialize `EnemyObservation` with a small known deck (e.g., 3 cards).
   * Register a sequence of enemy plays (non-tokens).
   * Assert that `remaining_ids` shrinks correctly and never goes negative.

5. **test_multiset_behavior_for_duplicate_cards**

   * Use a known deck with duplicates.
   * Play one copy.
   * Assert that `remaining_ids` still contains the correct number of copies.

### 8.3 Token Behavior

6. **test_tokens_are_classified_by_origin**

   * Ensure that tokens (identified by DB category or special flag) are registered with `origin="token"`.
   * Assert that they appear in `get_enemy_tokens`.

### 8.4 Determinism and Cloneability

7. **test_observation_is_deterministic_for_given_state_sequence**

   * Apply the same sequence of GameState transitions twice with a fresh EnemyObservation each time.
   * Assert that `enemy_observations` sequences are identical.

> Phase E/F tests will build on these by using `EnemyObservationState` as input to prediction/coaching logic.

---

## 9. Future Extensions (Out of Scope for Phase D)

The following are **explicitly postponed** to later design specs:

* Probabilistic hand/deck inference based on partial information.
* Threat maps (“which enemy cards flip lane X if drawn?”).
* Recommendations or ranking of enemy plays.
* Human-readable coaching narratives.

These will be defined in:

* `docs/prediction_design_spec.md`
* `docs/coaching_layer_design_spec.md`

Phase D must remain clean, factual, and stable to support those future layers.

---

## 10. Completion Criteria

Phase D is considered complete when:

1. `qb_engine/enemy_observation.py` implements the data models and APIs specified above.
2. `qb_engine/test_enemy_observation.py` exists and all tests pass.
3. All existing tests continue to pass.
4. Observation state is:

   * deterministic,
   * cloneable,
   * side-effect-free with respect to GameState.
5. Future layers can depend on `EnemyObservation` as a reliable factual source without needing to inspect raw GameState history themselves.