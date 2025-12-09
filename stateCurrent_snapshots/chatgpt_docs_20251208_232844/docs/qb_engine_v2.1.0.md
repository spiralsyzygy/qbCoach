# qb_engine_v2.1.0.md  
Queen’s Blood Engine Specification  
Engine v2.1.0 • Effects v1.1 • Tests 99/99 green (Last updated 2025-12-08)

---

# 1. Purpose & Scope

This document summarizes the deterministic Python engine as implemented in `qb_engine/` at v2.1.0. It describes the runtime modules, how they interact, and how the v1.1 effect layer is integrated. Rules details live in `docs/qb_rules_v2.2.4.md`; this file focuses on the engine architecture and wiring.

See also:
- `docs/qb_rules_v2.2.4.md` (authoritative rules)
- `docs/qb_effects_v1.1_status.md` (effect semantics)
- `docs/scoring_design_spec.md` (lane/match scoring and effect hooks)
- `docs/enemy_observation_design_spec.md`
- `docs/qb_engine_test_playbook_v1.0.0.md`

---

# 2. Core Data Models

## 2.1 CardHydrator
- Loads card definitions from `data/qb_DB_Complete_v2.json`.
- Provides cached `Card` objects (id, name, category, cost, power, pattern, grid, effect fields).

## 2.2 BoardState / Tile
- 3×5 grid; each `Tile` stores `owner` (Y/E/N), `rank` (0..3), `card_id`, `origin`, `spawned_by`, `power_delta`, `scale_delta`, `trigger_state`, `spawn_context`.
- Helper methods for printing, tile access, and effective power lookup via EffectEngine.

## 2.3 GameState
- Holds `BoardState`, `Deck`/`Hand` for both sides, RNG seed, and manages turn flow (draw, mulligan, play, end turn, pass).
- Plays cards via `play_card_from_hand`, applying projection, effects, and destruction resolution deterministically.

## 2.4 Deck / Hand / PawnDelta
- `Deck`: deterministic draw with seed, 15-card decks, opening hand of 5, single mulligan to 5, first-turn draw skipped for each side.
- `Hand`: convenience for card collections with stable ordering.
- Pawn deltas are represented on tiles (rank changes) and cleared when a card leaves play.

---

# 3. Legality & Projection

## 3.1 LegalityChecker (`qb_engine/legality.py`)
- A placement is legal iff: tile empty, tile owned by the player (Y), and tile.rank ≥ card.cost. Enemy/neutral tiles are illegal.
- Occupied tiles are always illegal; no special-case overrides.

## 3.2 Projection (`qb_engine/projection.py`)
- Applies the card’s 5×5 grid relative to placement:
  - `W`: place the card.
  - `P`: increase rank (pawns) on affected tiles (ownership rules enforced).
  - `E`: add an effect aura to the tile.
  - `X`: apply both pawn change and effect aura.
- Uses side-aware projection (mirrors for ENEMY).

---

# 4. Effect Engine (v1.1 registry)

Implemented in `qb_engine/effect_engine.py` and driven by `data/qb_effects_v1.1.json` (loaded via `effect_registry_utils.py`). Applies registry-defined operations; no card-specific hardcoding. Key points:

- Per-card state: `power_delta`, `scale_delta`, `CardTriggerState`, `origin`, `spawned_by`, `SpawnContext` (tokens).
- Triggers supported: `on_play`, `while_in_play`, `on_destroy`, `on_card_destroyed`, `on_card_played`, `on_enfeebled`, `on_first_enfeebled`, `on_first_enhanced`, `on_power_threshold`, `on_spawned`, `on_lane_win`, `on_round_end`.
- Scopes supported: per-tile scopes plus global (`allies_global`, `enemies_global`, `all_cards_global`) and lane (`allies_in_lane`, `enemies_in_lane`, `all_cards_in_lane`, `lane_owner`).
- Operations implemented:
  - `modify_power` (updates power_delta)
  - `modify_power_scale` (snapshot for while_in_play; persistent scale_delta for on_card_played/on_card_destroyed)
  - `destroy_cards`
  - `replace_ally`
  - `add_to_hand`
  - `spawn_token` (board placement, origin/spawn metadata, on_spawned trigger)
  - `modify_tile_ranks`
  - `expand_positions`
  - `score_bonus` (lane-win bonuses, lane_min_transfer)
- Destruction ordering: `on_destroy` of each target first, then `on_card_destroyed` watchers, then removal/cleanup.
- Effective power: base_power + power_delta + scale_delta + direct/aura deltas + snapshot scaling.

See `docs/qb_effects_v1.1_status.md` for detailed semantics.

---

# 5. Scoring

`qb_engine/scoring.py` provides pure functions:
- `compute_lane_power(board, effect_engine, lane_index) -> LaneScore`
- `compute_match_score(board, effect_engine) -> MatchScore`

Behavior:
- Uses `EffectEngine.compute_effective_power` for lane power.
- Lane winner: higher power (draw → None). Lane points = winner’s lane power (0 on draw).
- Before totals are aggregated, `effect_engine.apply_score_modifiers` applies:
  - `on_lane_win` score_bonus (flat, winner-only, stacks per card).
  - `on_round_end` lane_min_transfer (winner-only, adds min(power_you, power_enemy) per winner card with the effect).
- Returns match totals without mutating BoardState.

---

# 6. Enemy Observation & Prediction

## 6.1 EnemyObservation (`qb_engine/enemy_observation.py`)
- Tracks seen/known enemy cards, destroyed markers, tokens (origin/spawned_by), and reconstructs remaining deck/hand possibilities.
- Updated on every play/destroy and via GameState snapshots; supports symmetric behaviors for YOU/ENEMY.

## 6.2 Prediction (`qb_engine/prediction.py`)
- Deterministic 1-ply enemy projection using Simulation; computes threat maps and expected/worst margins.
- Consumed by Coaching to score moves against likely enemy replies.

## 6.3 Simulation (`qb_engine/simulation.py`)
- Clones GameState/BoardState, applies moves deterministically (no randomness), preserves RNG state for reproducibility.

---

# 7. Coaching (`qb_engine/coaching.py`)

High-level wrapper that:
- Enumerates legal moves for the active side.
- Uses PredictionEngine to evaluate expected margins per move.
- Ranks moves deterministically, returning top-N with explanations/tags.
- Relies on EffectEngine + Scoring for all power/score calculations; does not bypass rules.

---

# 8. Turn & Flow Notes

- Decks: 15 cards; opening hand 5; mulligan once to redraw to 5.
- First start-of-turn draw is skipped for each side; later draws are safe on empty deck.
- Game ends on full board or two consecutive passes.
- `BoardState` remains authoritative; all projections, effects, and scoring read from it.

---

# 9. Testing

Key engine tests (non-exhaustive):
- Board/legality/projection: `test_board.py`, `test_legality.py`, `test_projection_apply.py`, `test_projection_debug.py`
- Effects: `test_effect_engine.py`, `test_effect_on_play.py`, `test_effect_auras.py`, `test_effect_scaling.py`, `test_effect_triggers.py`, `test_effect_spawn_and_replace.py`, `test_effect_expand_positions.py`, `test_effect_scopes.py`, `test_effect_score_bonus.py`, `test_effect_registry_coverage.py`
- Enemy observation/prediction/coaching: `test_enemy_observation.py`, `test_enemy_projection.py`, `test_prediction.py`, `test_coaching.py`
- Scoring/simulation: `test_scoring.py`, `test_simulation.py`

All tests currently pass (75/75).

---

# 10. Version History

- **2.0.x** — Baseline hydration, legality, projection, destruction, scoring hooks.
- **2.1.0** — Full integration of Prediction/Coaching with v1.1 effect engine, scoring modifiers, token origin tracking, replace/spawn/expand semantics, global/lane scopes. All tests green.  
