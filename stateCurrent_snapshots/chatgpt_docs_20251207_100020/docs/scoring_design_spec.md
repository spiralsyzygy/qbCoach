# Scoring Design Specification — qbCoach Engine v3.0

Deterministic, read-only lane/match scoring used by simulation, prediction, and coaching. Aligned with `qb_rules_v2.2.4.md` and implemented in `qb_engine/scoring.py` + `qb_engine/effect_engine.py`.

---

## 1. Goals

- Use **effective power** (after all effects) to compute lane power for each side.
- Determine lane winner/draw.
- Assign base lane points: winner gets its lane power; draws give 0.
- Apply effect-based score modifiers (lane-win bonuses, lane_min_transfer) via EffectEngine.
- Aggregate lane points into match totals and margin.
- Pure functions; never mutate `BoardState`.

---

## 2. Data Models

### LaneScore
```
lane_index: 0/1/2 (TOP/MID/BOT)
power_you:   sum of effective power for YOU in lane
power_enemy: sum of effective power for ENEMY in lane
winner: "Y" | "E" | None
lane_points: winner’s lane power plus any effect bonuses (0 on draw)
```

### MatchScore
```
lanes: [LaneScore, LaneScore, LaneScore]
total_you:   sum lane_points for lanes YOU win
total_enemy: sum lane_points for lanes ENEMY win
winner: "Y" | "E" | None
margin: total_you - total_enemy
```

---

## 3. Scoring Pipeline

For each lane:
1) Compute `power_you` / `power_enemy` by summing `effect_engine.compute_effective_power(board, lane, col)` for occupied tiles.  
2) Determine `winner` (higher power; None on tie).  
3) Initialize `lane_points` = winner’s lane_power (0 on tie).  
4) After all lanes computed, call `effect_engine.apply_score_modifiers(board_state, lane_scores)` to adjust **lane_points only** (see §4).  
5) Aggregate lane_points into `MatchScore`. No board mutation occurs.

---

## 4. Effect-based Score Modifiers (v1.1)

Implemented in `EffectEngine.apply_score_modifiers` and validated by `test_effect_score_bonus.py`.

### 4.1 on_lane_win — flat bonuses
- Trigger: `on_lane_win`
- Scope: `lane_owner` (the side that won that lane)
- Op: `score_bonus amount=X`
- Behavior: In a lane with a winner, each **winner-side** card in that lane with this effect adds `amount` to that side’s `lane_points`. Losing-side effects do nothing. Multiple cards stack additively.

### 4.2 lane_min_transfer — on_round_end
- Trigger: `on_round_end`
- Scope: `lane_owner`
- Op: `score_bonus mode=lane_min_transfer`
- Behavior: For each lane with a winner, compute `lower = min(power_you, power_enemy)` (lane power, not points). Each **winner-side** card in that lane with this effect adds `lower` to that side’s `lane_points`. Draw lanes: no effect. Multiple cards stack (N cards → +N×lower).

---

## 5. Examples

1) Base scoring only: Lane power (Y=7, E=4) → winner Y, lane_points = 7.  
2) Lane-win bonus: Same lane, Y has two cards with on_lane_win+3 → lane_points = 7 + 3 + 3 = 13.  
3) lane_min_transfer: Lane power (Y=5, E=9), winner E, lower=5, one winner card with lane_min_transfer → lane_points = 9 + 5 = 14. Two such cards → 9 + 10 = 19.

---

## 6. Tests (ground truth)

- Core scoring: `qb_engine/test_scoring.py`
- Score modifiers: `qb_engine/test_effect_score_bonus.py`
- Effective power feeding scoring: `qb_engine/test_effect_*` (auras, scaling, spawn/replace/expand), `test_board_effective_power.py`

All tests currently pass (75/75).  
