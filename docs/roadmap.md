# qbCoach Deterministic Engine Roadmap (v2.2)
Last updated: 2025-12-05

This roadmap tracks the development of the deterministic Python engine that powers qbCoach (Queen’s Blood).

---

## ✔️ Completed Milestones

### **Core Foundations**
- JSON card database (validated)
- CardHydrator (deterministic, cached)
- BoardState model (tiles, influence, placement)
- PawnDelta influence model
- Projection system (Y-side)
- Legality checks
- EffectAura system + ★ visualization
- Effective power computation (EffectEngine v0.1)
- JSON-based effect registry (v1)
- On-play effects (EffectEngine v0.2)
- Enemy-side projection (geometry)
- apply_pawns_for_enemy / apply_effects_for_enemy
- EffectEngine fully side-aware
- pytest test suite across all subsystems

---

## 🧭 Current Phase — **Scoring Layer (v3.0)**

### What scoring must handle:
1. Compute lane power for both sides:
   - Using **effective power**, not base.
2. Determine:
   - Lane winner (Y/E/None)
   - Lane points (winner’s lane power)
3. Aggregate lane points into:
   - total_you
   - total_enemy
   - match winner
   - margin
4. Output results in a structured, deterministic way.

### Next tasks:
- Implement `qb_engine/scoring.py`
- Add models:
  - `LaneScore`
  - `MatchScore`
- Implement:
  - `compute_lane_power(board, effect_engine, lane_index)`
  - `compute_match_score(board, effect_engine)`
- Add pytest coverage:
  - Simple no-effect scenario
  - Effects that flip lane results
  - Draw lanes (0 points)
- Integrate scoring into future coach simulations

---

## 🔮 Upcoming Phases

### **Simulation Layer (v4.0)**
- Enumerate legal moves
- Predict board outcomes
- Compute expected value via scoring
- Build a move-ranking heuristic

### **Coach Layer (v5.0)**
- Explain recommended moves
- Highlight tactical opportunities
- Show hypothetical board states

---

## 📌 Rules
- No invented rules or card data.
- All logic must reflect:
  - `data/qb_DB_Complete_v2.json`
  - `docs/qb_rules*.md`
  - deterministic behavior only.
