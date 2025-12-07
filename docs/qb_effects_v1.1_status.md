# qb_effects_v1.1 — Status & Semantics

_Last updated: v1.1 runtime complete (effects engine Phases 1–3)._

This document summarizes what `qb_effects_v1.1` guarantees and how the runtime uses it.

---

## 1. Data & Coverage

**Registry:** `data/qb_effects_v1.1.json`  
**Card DB:** `data/qb_DB_Complete_v2.json`

Guarantees:

- Every `effect_id` used by a card in `qb_DB_Complete_v2.json` exists in `qb_effects_v1.1.json`.
- Every `operations[].type` in the registry is one of:

  - `modify_power`
  - `modify_power_scale`
  - `destroy_cards`
  - `replace_ally`
  - `add_to_hand`
  - `spawn_token`
  - `modify_tile_ranks`
  - `score_bonus`
  - `expand_positions`

- The registry is validated by `qb_engine/test_effect_registry_coverage.py`.

The engine never hardcodes card-specific behaviors. All semantics come from:
- Rules docs (`qb_rules_v2.2.4.md`, `scoring_design_spec.md`)
- Registry entries (`qb_effects_v1.1.json`)
- DB (`qb_DB_Complete_v2.json`)

---

## 2. Per-card runtime state

Per **BoardState.Tile** (or associated card state) we track:

- `base_power`: hydrated from the DB.
- `power_delta`: sum of all discrete `modify_power` operations applied to that card.
- `scale_delta`: persistent scaling from event-based `modify_power_scale` (on destroy / on play).
- `CardTriggerState`:
  - `first_enhanced_fired: bool`
  - `first_enfeebled_fired: bool`
  - `power_thresholds_fired: set[int]`
- `SpawnContext` (for tokens only):
  - `replaced_pawns: int` — pawn rank of the tile before the token was spawned.
- `origin`: `"deck"` or `"token"`.
- `spawned_by`: optional source card id for tokens.

**Classification:**

- A card is **enhanced** if `power_delta > 0`.
- A card is **enfeebled** if `power_delta < 0`.
- Otherwise it is neutral.

**Effective power** is:

```text
effective_power =
    base_power
  + power_delta
  + scale_delta           # from event-based modify_power_scale
  + while_in_play scaling # snapshot-based from board state
  + aura effects / projections
````

---

## 3. Triggers implemented

Engine dispatches these triggers:

* `on_play`
* `while_in_play`
* `on_destroy` (self “deathrattle”)
* `on_card_destroyed` (global watchers)
* `on_card_played` (global watchers)
* `on_enfeebled`
* `on_first_enfeebled`
* `on_first_enhanced`
* `on_power_threshold`
* `on_spawned`
* `on_lane_win` (scoring)
* `on_round_end` (lane_min_transfer scoring)

### 3.1 Enhanced / enfeebled triggers

* `on_enfeebled` fires **every time** a negative `modify_power` is applied to that card.
* `on_first_enhanced` fires when classification crosses from `<= 0` to `> 0` the first time.
* `on_first_enfeebled` fires when classification crosses from `>= 0` to `< 0` the first time.

### 3.2 Power threshold triggers

Effects may specify:

```json
"conditions": {
  "threshold": { "stat": "power", "value": K },
  "first_time": true
}
```

* After any change that can affect effective power, we compare `P_old` and `P_new`:

  * If `P_old < K` and `P_new >= K`, the threshold is crossed upward.
* If `first_time: true`, we fire once per card per threshold value.
* Downward crossings are ignored.

### 3.3 Destroy / destroyed ordering

When cards are destroyed in a batch:

1. Compute the set of cards to destroy.
2. For each card **C** in that set:

   * Run C’s `on_destroy` effects.
3. For each card **C** again:

   * Run all `on_card_destroyed` watchers whose `per` matches C (all/ally/enemy).
   * These usually update `scale_delta` via `modify_power_scale`.
4. Remove the destroyed cards from the board and apply pawn/state cleanup.

---

## 4. Scaling semantics (`modify_power_scale`)

Two patterns:

### 4.1 While-in-play (snapshot-based)

* Trigger: `while_in_play`
* Behavior:

  * Count cards on board matching the registry’s `per` (enhanced/enfeebled/all, etc.).
  * `delta = amount_per * count`.
  * This `delta` is **computed on the fly** for effective power; it does not modify `scale_delta`.

### 4.2 Event-based (stacking)

* Trigger: `on_card_destroyed` or `on_card_played`.
* Behavior:

  * Each time an event matches the `per` condition (destroyed/played ally/enemy/all), we:

    * Add `amount_per` to that card’s `scale_delta`.
  * `scale_delta` persists until end of game.

---

## 5. Board-level ops

### 5.1 spawn_token

* `apply_to: "empty_positions"`:

  * All tiles with no card and a positive pawn rank owned by the effect owner.
  * Neutral [N0] tiles are not eligible.

* For each eligible tile:

  * Let `rank_before = tile.rank`.
  * Spawn **one** token card:

    * `origin = "token"`
    * `spawned_by = source_card_id`
    * `SpawnContext.replaced_pawns = rank_before`
  * Place token on the tile (legality bypassed; effect-driven).
  * Fire `on_spawned` for that token (if any):

    * e.g. `on_spawned_replaced_pawns_gain` uses `replaced_pawns` to boost token power.

* No multiple tokens per tile; “per_pawns” is encoded in `replaced_pawns`, not multiplicity.

### 5.2 replace_ally

* When playing a card with `replace_ally`:

  1. Let T be the placement tile.
  2. If T holds an **ally**:

     * Compute `replaced_ally_power = effective_power(T.card)` before removal.
     * Destroy that ally via the normal destruction pipeline.
  3. Place the new card on T.
  4. Apply follow-up ops:

     * `mode: "neutral"`: no power changes.
     * `mode: "lower"` + `adjustment: "replaced_ally_power"`:

       * Use `modify_power` with `amount = -replaced_ally_power` on the op’s scope.
     * `mode: "raise"` + `adjustment: "replaced_ally_power"`:

       * Use `modify_power` with `amount = +replaced_ally_power`.

* If T is empty or enemy-occupied:

  * No ally destroyed, `replaced_ally_power = 0`, so follow-ups have no numeric effect.

### 5.3 expand_positions

* When `expand_positions` fires for card S at (lane L, col C):

  * For all 8 adjacent tiles (orthogonal + diagonal, within board bounds):

    * If tile is **neutral**:

      * Set owner = S.side, rank = 1.
    * If tile is owned by S.side:

      * Increase rank by 1, clamped to 3.
    * If tile is enemy-owned:

      * No change.

* No cards are moved or placed; only tile ownership/rank changes.

---

## 6. Scopes

Supported scopes include:

* Per-tile / affected:

  * (existing engine scopes; see `effect_engine.py`)

* **Global**:

  * `allies_global` → all allied cards on the board.
  * `enemies_global` → all enemy cards on the board.
  * `all_cards_global` → all cards on the board.

* **Lane**:

  * `allies_in_lane` → allied cards in a given lane.
  * `enemies_in_lane` → enemy cards in that lane.
  * `all_cards_in_lane` → all cards in that lane.

Lane is determined either from:

* The effect card’s lane (source position), or
* An explicit lane context (for scoring).

Implementation uses a central `resolve_scope` helper in `EffectEngine`.

---

## 7. Scoring hooks

Scoring pipeline:

1. Compute lane power (you vs enemy) and lane winner per lane.
2. Initialize lane_points:

   * Winner’s side gets their lane_power.
   * Draw → lane_points = 0.
3. Call `EffectEngine.apply_score_modifiers(board_state, lane_scores, game_state)` to adjust **lane_points** only.
4. Aggregate lane_points into match score.

### 7.1 on_lane_win — flat bonuses

* Pattern:

  * `trigger: "on_lane_win"`
  * `scope: "lane_owner"`
  * `operations: [{ "type": "score_bonus", "amount": X }]`

Behavior:

* For each lane with a winner:

  * For each card in that lane owned by the **winning side** with on_lane_win+score_bonus:

    * Add `amount` to that side’s lane_points for that lane.
* Multiple such cards stack additively.
* Losing side’s on_lane_win effects do nothing.

### 7.2 lane_min_transfer — on_round_end

* Pattern:

  * `trigger: "on_round_end"`
  * `scope: "lane_owner"`
  * `operations: [{ "type": "score_bonus", "mode": "lane_min_transfer" }]`

Behavior:

* For each lane with a winner:

  * Let `lower = min(power_you, power_enemy)` (lane power, not lane_points).
  * If the winning side has card(s) in that lane with lane_min_transfer:

    * For each such card:

      * Add `lower` to the winner’s lane_points for that lane.
* Draw lanes: no effect, even if such cards exist.
* Multiple winner cards with lane_min_transfer stack (2 cards → +2×lower, etc).

---

## 8. Tests

Core tests validating v1.1 behavior:

* Registry & coverage:

  * `qb_engine/test_effect_registry_coverage.py`

* Scaling & triggers:

  * `qb_engine/test_effect_scaling.py`
  * `qb_engine/test_effect_triggers.py`

* Spawn/replace/expand:

  * `qb_engine/test_effect_spawn_and_replace.py`
  * `qb_engine/test_effect_expand_positions.py`

* Scopes & scoring:

  * `qb_engine/test_effect_scopes.py`
  * `qb_engine/test_effect_score_bonus.py`

Full suite (at time of writing): **75/75 passing**.
