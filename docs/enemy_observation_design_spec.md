# Enemy Observation Design Specification — Phase D

Factual tracking of enemy cards and deck usage, as implemented in `qb_engine/enemy_observation.py`. No predictions or probabilities; outputs feed Prediction (Phase E) and Coaching (Phase F). Tests 89/89 green (Last updated 2025-12-06).

---

## 1. Objectives

- Record enemy cards seen on board, their positions, and when they leave play.
- Optionally track remaining deck contents in known-deck mode.
- Maintain token provenance (origin/spawned_by captured on tiles).
- Provide deterministic, side-effect-free queries for higher layers.

---

## 2. Core Data (summary of `enemy_observation.py`)

- `ObservedCard`:
  - `card_id`, `side`, `origin` (`"deck"`, `"token"`, `"effect"`, `"unknown"`), `turn_observed`, `lane_index`, `col_index`, `destroyed_on_turn`.
- `EnemyDeckKnowledge`:
  - `full_deck_ids`, `played_ids`, `remaining_ids` (multiset semantics; meaningful only if full deck provided).
- `EnemyObservationState`:
  - `observations` (all sides), `enemy_observations` (enemy-only view), `enemy_deck_knowledge`, `last_updated_turn`.
- `EnemyObservation` orchestrates updates/queries; cloneable/resettable.

---

## 3. Updates

### 3.1 `update_from_game_state(state: GameState)`
- Reads `state.board` and `state.turn` only; never mutates the state.
- Ensures each enemy-occupied tile has an `ObservedCard` (origin set to `unknown` if not provided).
- Marks cards as destroyed if they were on board previously but are no longer present; stamps `destroyed_on_turn`, clears lane/col.
- Refreshes `enemy_observations` view and `last_updated_turn`.

### 3.2 `register_enemy_play(card_id, lane_index, col_index, turn, origin="deck")`
- Inserts a new enemy observation with provided origin and position.
- In known-deck mode and `origin == "deck"`, appends to `played_ids` and recomputes `remaining_ids`.
- Updates `last_updated_turn`.

---

## 4. Queries

- `get_enemy_board_cards()` → enemy observations still on board (not destroyed).
- `get_enemy_destroyed_cards()` → enemy observations with `destroyed_on_turn` set.
- `get_enemy_tokens()` → enemy observations where `origin == "token"`.
- `get_known_enemy_deck_remaining_ids()` → list copy of `remaining_ids` (empty/meaningless in unknown-deck mode).
- `get_all_enemy_observations()` → copy of all enemy observations for debugging/logging.

All queries are read-only and deterministic.

---

## 5. Interaction with Board/State

- EnemyObservation is maintained alongside `GameState` (not owned by it) so prediction/coaching can clone both.
- Token provenance (origin/spawned_by) is set on tiles by the effect engine; `update_from_game_state` preserves origin if supplied externally, otherwise defaults to `unknown`.
- Update cadence used in tests: after plays/destructions and/or once per turn via `update_from_game_state`.

---

## 6. Tests (ground truth)

- `qb_engine/test_enemy_observation.py`:
  - register/play creates observations; updates track presence; destroyed cards stamped with turn; remaining_ids shrink in known-deck mode; multiset behavior for duplicates; tokens classified by origin; deterministic for a given sequence.
- `qb_engine/test_enemy_projection.py`:
  - Ensures projections consume observation state for symmetry and threat marking.

---

## 7. Future Work (explicitly out of scope here)

- Probabilistic inference of unseen hand/deck contents.
- Threat maps or enemy move ranking.
- Narrative/UX surfacing of observations.

Those belong to Prediction/Coaching specs once implemented.  
