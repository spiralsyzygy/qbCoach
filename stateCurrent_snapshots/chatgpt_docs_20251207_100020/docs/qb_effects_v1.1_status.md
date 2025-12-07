# qb_effects_v1.1 — Status & Semantics

_Engine v2.1.0 + Effects v1.1; all tests passing._

This is the canonical reference for what the v1.1 effect runtime does today. It reflects `qb_engine/effect_engine.py`, `game_state.py`, `scoring.py`, and the corresponding tests.

---

## 1. Data & Coverage

**Registry:** `data/qb_effects_v1.1.json`  
**Card DB:** `data/qb_DB_Complete_v2.json`

Guarantees:
- Every `effect_id` in the DB is present in the registry (validated by `test_effect_registry_coverage.py`).
- Supported op types: `modify_power`, `modify_power_scale`, `destroy_cards`, `replace_ally`, `add_to_hand`, `spawn_token`, `modify_tile_ranks`, `score_bonus`, `expand_positions`.
- Engine behavior is registry-driven; no card-specific hardcoding.

---

## 2. Per-card runtime state (per tile)

- `base_power` (from DB)
- `power_delta` (sum of discrete `modify_power`)
- `scale_delta` (event-based `modify_power_scale` stack)
- `CardTriggerState`:
  - `first_enhanced_fired`
  - `first_enfeebled_fired`
  - `power_thresholds_fired: set[int]`
- `SpawnContext` (tokens):
  - `replaced_pawns` = tile rank before spawn
- `origin` (`"deck"` or `"token"`)
- `spawned_by` (source card id, for tokens)

**Classification:** enhanced if `power_delta > 0`; enfeebled if `power_delta < 0`; neutral otherwise.

**Effective power:** base_power + power_delta + scale_delta + aura/direct deltas + snapshot scaling.

---

## 3. Triggers supported

- `on_play`
- `while_in_play`
- `on_destroy` (self)
- `on_card_destroyed` (watchers)
- `on_card_played` (watchers)
- `on_enfeebled`
- `on_first_enfeebled`
- `on_first_enhanced`
- `on_power_threshold`
- `on_spawned`
- `on_lane_win` (scoring)
- `on_round_end` (lane_min_transfer scoring)

### Enhanced/enfeebled triggers
- `on_enfeebled`: every negative `modify_power` applied to that card.
- `on_first_enhanced`: crosses from `<= 0` to `> 0` once.
- `on_first_enfeebled`: crosses from `>= 0` to `< 0` once.

### Power threshold
- Fires on upward crossing of `threshold.value` after any power change.
- `first_time: true` fires once per threshold value; downward crossings ignored.

### Destroy ordering
1) For each card in the destroy set: run its `on_destroy`.  
2) For each destroyed card: run all matching `on_card_destroyed` watchers (per=all/ally/enemy), often updating `scale_delta`.  
3) Remove cards and cleanup state/auras/deltas.

---

## 4. Scaling (`modify_power_scale`)

### While-in-play (snapshot)
- Trigger: `while_in_play`.
- Count matching cards on board per the `per` filter (enhanced/enfeebled variants).
- `delta = amount_per * count` added on the fly to effective power (no scale_delta change).

### Event-based (stacking)
- Triggers: `on_card_destroyed`, `on_card_played`.
- When event matches `per` (destroyed/played ally/enemy/all), add `amount_per` to `scale_delta`. Persistent for the card.

---

## 5. Board-level operations

### spawn_token
- Eligible tiles: owned, empty, rank > 0 (no neutral [N0]).
- For each eligible tile:
  - Spawn exactly one token, set `origin="token"`, `spawned_by=source_card_id`, `SpawnContext.replaced_pawns=tile.rank before spawn`.
  - Place token bypassing legality; then fire its `on_spawned` (e.g., power gain based on `replaced_pawns`).
- `per_pawns` is encoded in `replaced_pawns`, not multiple tokens.

### replace_ally
- Target: the allied card on the placement tile (if any).
- If allied occupant exists: compute `replaced_ally_power` using current effective power, destroy via normal pipeline, then place the new card.
- Follow-ups:
  - `mode: "neutral"` → no power change.
  - `mode: "lower"/"raise"` + `adjustment: "replaced_ally_power"` → apply `modify_power` with ±replaced_ally_power to the op scope.
- If tile empty or enemy-occupied: `replaced_ally_power = 0`, no numeric effect.

### expand_positions
- 8-way adjacency around the source card:
  - Neutral → owner rank 1
  - Owner → rank +1 (clamp 3)
  - Enemy → unchanged
- No cards placed; only ownership/ranks change.

---

## 6. Scopes

- Global: `allies_global`, `enemies_global`, `all_cards_global`
- Lane: `allies_in_lane`, `enemies_in_lane`, `all_cards_in_lane` (source lane or explicit lane context)
- Scoring context: `lane_owner` (winner of that lane by power)

Implemented via `EffectEngine.resolve_scope`.

---

## 7. Scoring hooks

Scoring flow: compute lane power/winner → initialize lane_points → call `effect_engine.apply_score_modifiers` → aggregate.

### on_lane_win (flat bonus)
- Trigger `on_lane_win`, scope `lane_owner`, op `score_bonus amount=X`.
- Winner-only; each winner-side card with the effect in that lane adds `amount` (stacks).

### lane_min_transfer
- Trigger `on_round_end`, scope `lane_owner`, op `score_bonus mode=lane_min_transfer`.
- For lanes with a winner: compute `lower = min(power_you, power_enemy)`; each winner-side card with this effect adds `lower` to lane_points (stacks). Draws: no effect.

---

## 8. Tests (ground truth)

- Registry/coverage: `test_effect_registry_coverage.py`
- Scaling/triggers: `test_effect_scaling.py`, `test_effect_triggers.py`
- Spawn/replace/expand: `test_effect_spawn_and_replace.py`, `test_effect_expand_positions.py`
- Scopes/scoring: `test_effect_scopes.py`, `test_effect_score_bonus.py`
- Auras/on_play basics: `test_effect_engine.py`, `test_effect_on_play.py`, `test_effect_auras.py`

Full suite currently passes (75/75).  
