# Scoring Design Specification — qbCoach Engine v3.0

This document defines the deterministic scoring subsystem that evaluates board states at end-of-game or during simulations.

---

## 1. Goals

- Compute lane power for both sides using **effective power** (after buffs/debuffs).
- Determine lane winner:
  - "Y" if you win
  - "E" if enemy wins
  - None for draw
- Assign lane points:
  - winner's lane power
  - 0 for draws
- Aggregate totals across all lanes
- Determine match winner + margin
- Pure function: does **not** mutate BoardState

---

## 2. Data Models

### LaneScore
```python
@dataclass
class LaneScore:
    lane_index: int
    power_you: int
    power_enemy: int
    winner: Optional[Literal["Y","E"]]
    lane_points: int
```

### MatchScore
```python
@dataclass
class MatchScore:
    lanes: List[LaneScore]
    total_you: int
    total_enemy: int
    winner: Optional[Literal["Y","E"]]
    margin: int
```

---

## 3. Lane Power Computation

For each lane `L`:

1. For each column in lane:
   - If no card → skip
   - Determine side via `board.get_card_side(card_id)`
   - Compute effective power via:
     ```python
     eff = effect_engine.compute_effective_power(board, L, col)
     ```
   - Add to `power_you` or `power_enemy`

2. Determine winner:
   - if power_you > power_enemy → "Y"
   - if power_enemy > power_you → "E"
   - else → None (draw)

3. Determine lane points:
   - winner's lane power
   - 0 for draws

---

## 4. Match Scoring

`compute_match_score(board, effect_engine)`:

- Iterate lanes 0–2
- Compute each LaneScore
- Aggregate:
  ```python
  total_you += lane_score.lane_points if lane_score.winner == "Y"
  total_enemy += lane_score.lane_points if lane_score.winner == "E"
  ```
- Determine match winner → side with higher total
- margin = total_you − total_enemy

---

## 5. Pytest Coverage

### Tests to include:
1. **Simple scenario (no effects)**
2. **Effects altering lane outcomes**
3. **Draw lane → zero points**
4. **Mixed sides + neutral tiles**
5. **Non-mutating behavior**

---

## 6. Integration Notes

- Scoring is **read-only**.
- Does not modify:
  - PawnDelta
  - EffectAura
  - direct_effects
  - board tiles
- Works at any point in gameplay:
  - mid-turn evaluation
  - end-of-game resolution
- Required for prediction and AI coaching layers.

