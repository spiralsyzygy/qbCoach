# **qbCoach Roadmap (Refactored 2025-12-06; tests 89/89 green)**

*Authoritative Development Plan for the Deterministic Queen’s Blood Engine*

This roadmap defines the sequential development phases for the qbCoach deterministic engine.
It is the document Codex (or any coding LLM) should use to understand:

* what is finished
* what is in progress
* what comes next
* where boundaries exist between the rule-engine, simulation engine, opponent modeling, and coaching layer.

The engine must always remain **deterministic**, **testable**, **JSON-driven**, and **fully rule-accurate**.
LLMs may assist in writing code, but **no part of engine logic may live in an LLM**.

---

# **0. Current State Summary**

Engine v2.1.0 + Effects v1.1 are complete and fully tested (75/75). Key capabilities:

### ✅ Core & Simulation
* BoardState/GameState deterministic 3×5 model; seeded decks/hands; mulligan; turn flow; draw safety on empty decks.
* LegalityChecker (empty, owned, sufficient rank only).
* ProjectionEngine (W/P/E/X with side mirroring), pawn deltas, destruction cleanup.
* EffectEngine v1.1 (registry-driven on_play/while_in_play/on_destroy/on_card_destroyed/on_card_played/on_enfeebled/first_enhanced/first_enfeebled/threshold/on_spawned/on_lane_win/on_round_end; spawn_token/replace_ally/expand_positions; global/lane scopes; scoring hooks).
* Scoring: effective power–based lane power, lane points, effect score modifiers (lane_win bonuses, lane_min_transfer), match totals.
* Simulation/Prediction: deterministic cloning, 1-ply enemy projection, threat maps.
* Coaching: legal move enumeration, evaluation via scoring/prediction, deterministic ranking with explanations.
* Enemy Observation: factual tracking of enemy plays/tokens/destroyed, known-deck remaining IDs; consumed by prediction/projection tests.

### ✅ Tooling & Docs
* Engine walkthrough demo updated for v1.1 effects.
* Export script bundles GPT-layer/Phase G docs.
* Specs refreshed: `qb_engine_v2.1.0.md`, `qb_effects_v1.1_status.md`, `scoring_design_spec.md`, `enemy_observation_design_spec.md`, `qb_engine_test_playbook_v1.0.0.md`, Phase G/GPT-layer docs.

---

# **1. Phase A — Data & Rules Foundation (Complete)**

### 1.1 Card Database

* Strict hydration from QB_DB_Complete_v2.json
* No inference / hallucination permitted

### 1.2 Ruleset v2.2.4

* Official reference for projection, legality, scoring
* Engine logic must map 1:1 to this document

**Status:** Complete. Update only on real rule changes.

---

# **2. Phase B — Deterministic Engine Core (Complete)**
BoardState, legality, projection, pawn bookkeeping, destruction, base scoring established. Bugfix-only going forward.

---

# **3. Phase C — Simulation Layer (Complete)**
Deterministic turn loop with seeded decks/hands, mulligan, draw, play_card_from_hand, projections/effects, destruction, cleanup. Safe empty-deck draws. Cloneable GameState for prediction/simulation tests.

---

# **4. Phase D — Enemy Observation (Complete)**
Factual tracking of enemy plays/tokens/destroyed and known-deck remaining IDs. Deterministic updates from GameState; consumed by prediction/projection tests.

---

# **5. Phase E — Prediction Engine (Complete)**
Deterministic 1-ply enemy projection with threat maps; uses simulation clones and scoring. No probabilistic inference; follows implemented test coverage.

---

# **6. Phase F — Coaching Layer (Complete)**
Deterministic recommendation engine: enumerates legal moves, scores via prediction+scoring, ranks with explanations/tags. Respects legality and effect/scoring semantics; validated by `test_coaching.py`.

---

# **7. Phase G — GPT Layer & Tooling (In Progress)**
Parallel track building GPT-facing UX and self-play:
* Milestones in `phase_G_milestone_map.md` (core architecture, live coaching protocol, self-play, enemy profiles/memory, episode logging).
* GPT layer docs: `GPT_layer/chatGPT+Codex_dual_initialization`, `GPT_layer/gpt_effects_layer_note.md`, `gpt_layer_design_overview.md`.
* Export tooling includes GPT-layer docs (`tools/export_chatgpt_docs.py`).
* Visualization/debugger/board printer remain optional improvements.

---

# **8. Development Philosophy**

1. **Deterministic first, predictive second.**
2. **The JSON DB is the single source of truth.**
3. **Rules code is never approximate.**
4. **Simulation is not intelligence.**
5. **Coaching explanations come last.**

---

# **9. Test Strategy**

* Unit, integration, and regression suites live under `qb_engine/test_*.py`; current status 75/75 passing.
* Registry coverage ensures every `effect_id` in the DB has a registry entry and op types are known.
* New features require corresponding spec updates and tests.

Below is a clean **Phase G Roadmap Checkpoint Update** that fits directly into your existing `docs/roadmap.md` structure and maintains continuity with Phase G → Phase E handoff expectations.

It’s written to slot into a “Milestone Status / Checkpoint” section verbatim.

---

# ✅ **Phase G — Development Roadmap Checkpoint (v0.3 Completion)**

*(Ready to drop into `docs/roadmap.md` as a milestone update)*

## **Summary**

Phase G (Track A.5: Live Coaching UX + GPT Orchestration Layer) has reached a **stable v0.3 checkpoint**.
This phase’s purpose was to unify:

* Deterministic engine execution (rules, effects, scoring, projections, prediction)
* Manual-turn-loop GPT coaching behavior
* Human-facing UX in the CLI
* Snapshot formatting standards & visualization conventions

All core loop features and safety requirements have now been implemented, validated, and tested end-to-end.

Testing reports: **99/99 tests green**, including newly added UX & visualization tests.

---

# **1. What Has Been Completed (Phase G v0.3)**

### **1.1 Live Coaching Loop — Full Turn/Phase Control**

* Correct YOU/ENEMY turn gating
* Enforcement of draw-before-recommend/playing
* Full legality access (no longer tied to recommended moves)
* Correct turn increments + side_to_act resolution
* Turn boundary messages in CLI
* Accurate, stable snapshotting (SESSION, BOARD, YOU_HAND, ENGINE_OUTPUT)

### **1.2 Hand Management — Fully Stable**

* `draw` now **appends** instead of overwriting hand
* Added `set_hand` for manual desync recovery
* Deterministic updates in snapshots + logs
* Hand sync is now completely predictable and safe under load

### **1.3 Effect Overlay Visualization (ISSUE 9)**

* Engine snapshot now emits `effect_tiles` overlay
* Formatter adds `★` to any tile under active effects
* Works for:

  * empty effect tiles
  * occupied effect tiles
  * multi-effect tiles
* Documentation updated to reflect unified semantics:

  > `★` = tile is under one or more live effects (game-state actual)

### **1.4 Coaching Mode (strict / strategy)**

* Stored in LiveSessionEngineBridge
* Echoed in `[SESSION]` header + logs
* CLI prompts for mode and defaults to `strict`
* Tests confirm correct behavior for both modes
* Simplifies future UX work by separating:

  * deterministic engine narration
  * heuristic strategy overlays (non-mechanical)

### **1.5 Logging & Stability Improvements**

* Fix: timezone-aware datetime for snapshot/log filenames
* Log entries now include `coaching_mode`
* All turn, phase, and hand ops consistently logged
* JSONL logs validated against new schema

---

# **2. What Was Explicitly *Not* Modified (Safe Invariants)**

Phase G improvements did **not** touch:

* **Rules engine** (legality, pawn deltas, projections)
* **Scoring system**
* **Effect semantics** (modify_tile_ranks, power_delta, scale_delta, etc.)
* **Prediction mechanics** (E-mode, influence propagation)
* **Card DB or card hydration**
* **EnemyObservation inference logic**

This preserves the entire deterministic foundation for Phase E work.

---

# **3. Phase G Remaining (Low Priority / Backlog)**

These are *optional* polish items that may be incorporated later:

* More robust enemy-play parsing (natural language → structured)
* Replay log → episode artifact tooling (Track D)
* Potential richer debug output (BOARD_DEBUG with b/p/e decomposition)
* Additional CLI quality-of-life commands (undo, show_legality, show_effects, etc.)

None of these block Phase E.

---

# **4. Phase E — Prerequisites Now Fully Satisfied**

Phase E (Prediction Engine v2: probabilistic, multi-turn, shaped distributions) required several architectural guarantees:

### ✔ Reliable, machine-readable snapshots

### ✔ Correct turn-loop with enemy + player sequencing

### ✔ Perfect hand sync

### ✔ Correct effect-application visibility

### ✔ Ability for GPT layer to choose coaching_mode (strict vs strategy)

### ✔ Stabilized CLI + logs for training + debugging

All prerequisites are now met.

Phase E can begin without risk of needing major rework in Phase G foundations.

---

# **5. Phase E Preview — Next Steps (High Level)**

Phase E objectives include:

### **5.1 Prediction Model Upgrade**

* From single-turn “best response” to multi-turn projected state values
* Use influence maps, effect propagation, and probabilistic enemy responses
* Integrate lane-power volatility models

### **5.2 Threat Model Pipeline**

* Progressive enemy-move distribution
* Risk bands (safe, volatile, losing)
* Conditioned predictions based on current + hypothetical board states

### **5.3 Simulation Layer (Deterministic Core)**

* N-step lookahead path evaluator
* Local pruning strategies
* Soft constraints preserving deterministic engine sanctity

### **5.4 Data Structures**

* PredictionDelta
* ThreatClusters
* Multi-turn Monte-like evaluators (strictly deterministic evaluation per branch)

### **5.5 GPT Integration for UX (Track E.3)**

* How prediction should be narrated
* Interpretation rules: probability bands, risk classes
* Strict-mode vs strategy-mode prediction phrasing

The foundation Phase G provides—especially precise snapshotting and coaching-mode discipline—is essential for Phase E to succeed.

---

# **6. Phase G → Phase E Handoff Status**

### **STATUS: COMPLETE AND STABLE**

All critical path items for Phase G have been delivered and validated.

The system is ready for Phase E development, with no known blockers.

---

# **End of Phase G Roadmap Checkpoint (v0.3)**

---

# **10. Next Action Queue (2025-12-06)**

* Focus on Phase G (GPT layer) per `phase_G_milestone_map.md`:
  - Solidify GPT↔engine message grammar and turn-loop protocol.
  - Build self-play/episode logging on top of deterministic engine.
  - Extend coaching UX for GPT-facing interactions.
* Maintain engine determinism and test coverage; effect/rules changes are bugfix-only.  
