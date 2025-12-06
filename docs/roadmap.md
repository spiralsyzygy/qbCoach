# **qbCoach Roadmap (Refactored 2025-12-05)**

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

The following components are complete and validated:

### ✅ Core Architecture

* BoardState (3×5 canonical model)
* Tile state (owner, ranks, occupantCard, effect markers)
* CardHydrator (hydrates from QB_DB_Complete_v2.json)
* LegalityChecker (Epic B–accurate)
* ProjectionEngine (P/E/X, W tile, coordinate mapping, multi-turn, destruction semantics)
* Pawn model (Epic C)
* Effect lifecycle (whileInPlay, onPlay, onDestroy)
* ScoringEngine (Epic D laneScore & matchScore)
* Serialization routines for debugging & visualization
* Test Playbook (v1.0.0)

### ✅ Engine Walkthrough Script (developer quickstart)

* Working E2E demonstration of initialization → card placement → projection → scoring
* Prints board at all major steps

### Pending small fixes

* Security Officer suboptimal placement in walkthrough (strategy issue, not legality issue)
* Minor visualization additions (pawn deltas, effect markers)

---

# **1. Phase A — Data & Rules Foundation (Complete)**

### 1.1 Card Database

* Strict hydration from QB_DB_Complete_v2.json
* No inference / hallucination permitted

### 1.2 Ruleset v2.2.4

* Official reference for projection, legality, scoring
* Engine logic must map 1:1 to this document

**Status:** Complete.
**Next actions:** Only update when new in-game observations require rule amendments.

---

# **2. Phase B — Deterministic Engine Core (Complete)**

This phase produced:

* BoardState
* LegalityChecker
* ProjectionEngine
* PawnContribution bookkeeping
* EffectEngine behavior
* Destruction model
* ScoringEngine

**Status:** Complete & stable.
This foundation should remain unchanged except for bugfixes.

---

# **3. Phase C — Simulation Layer (IN PROGRESS, next major area)**

This phase teaches the engine to “play a turn,” not intelligently, but mechanically.

### 3.1 Turn Structure

* Draw step (player, enemy)
* Play step with legality enforcement
* Apply projections
* Resolve effects
* Cleanup phase (destroyed cards, effect expiry)

### 3.2 Hand Modeling

* Player hand already partially supported in walkthrough
* Enemy hand currently: **no model**

Required additions:

* A PlayerHand and EnemyHand model
* Mulligan support
* Draw counters
* Each placement must decrement hand state and increase graveyard/destruction log

### 3.3 Deck Modeling

The engine must support deterministic or seeded-random deck generation.

Requirements:

* Represent 10-card decks (player & enemy)
* Shuffle (seeded RNG)
* Draw order tracking
* Mulligan rules
* Replacement after destruction (token creation, transform effects)

### 3.4 Hand → Board Interface

Currently the user provides placements via API call; engine must gain:

* `playCardFromHand(handIndex, tile)`
* Validation wrapper around LegalityChecker
* Automatic hydration of card data from DB
* Updates to history logs

**Status:** 40% complete.

This is our **next task once Option D restructuring is complete.**

---

# **4. Phase D — Enemy Observation Model (Upcoming)**

This is not prediction — it is a passive observation system.

### Required capabilities:

* Track what the enemy has already played
* Track visible tiles (enemy projections, effect markers)
* Infer enemy card identities **only when deterministic** (e.g., via token summons or unique patterns)
* Maintain an “observation state” separate from “prediction state”

### Observation Data Stored:

* Enemy board occupancy
* Pawn ranks & ownership
* Effect markers
* Known enemy cards revealed through gameplay (e.g. spawning tokens)
* Turn order of enemy actions

**Status:** Not started.
This becomes the foundation for prediction but must remain purely factual.

---

# **5. Phase E — Prediction Engine (Epic E)**

This is the phase you originally identified as “much bigger than A–D,” and that’s correct.
Epic E introduces the computational reasoning required for coaching.

### Three layers:

#### **5.1 Enemy Deck Inference (probabilistic, not guaranteed)**

* Based on early plays, tokens, cost distribution, patterns
* Weighted likelihoods
* Multiple plausible deck models

#### **5.2 Enemy Hand Prediction**

* Based on inferred deck + observed draws
* Bayesian updating each turn
* Must maintain a set of possible hand-states, not a single guess

#### **5.3 Enemy Next-Move Projection**

For each plausible enemy hand:

* enumerate all legal placements
* simulate resulting board states
* score them
* produce a probability-weighted threat map

This gives the coaching layer something to evaluate against.

**Status:** Not started.
Epic E should not be attempted until Phase C is fully complete.

---

# **6. Phase F — Coaching Layer (Final Phase)**

This is the “AlphaGo-turned-Coach” layer that sits **on top of the deterministic engine**.

### Requirements:

#### **6.1 State Evaluation**

* Identify winning vs losing positions
* Evaluate tempo advantage
* Evaluate lane pressure
* Evaluate scoring threats
* Rate the strength of future enemy moves
* Provide a clear explanation for each evaluation

#### **6.2 Recommendation Engine**

Using full deterministic logic:

* Enumerate all legal player moves
* For each move, simulate enemy responses (from Epic E)
* Provide best move recommendations
* Offer readable strategy explanations
* NEVER violate deterministic engine rules

#### **6.3 User Coaching UX**

* Turn-by-turn analysis
* Highlight tiles
* Explain legality failures
* Explain why enemy plays were effective
* Help users improve deckbuilding understanding

**Status:** Planned.
Must come ***after*** Phases C, D, and E.

---

# **7. Phase G — Visualization & Tooling (Parallel Track)**

(This is optional but recommended.)

Includes:

* Board printer v2 (with pawn deltas, effect markers, lane power, scoring preview)
* Interactive replay debugger
* Log visualizations
* Notation standard (already partially defined in qb_visualization_conventions_v1.0.0.md)

This phase can run alongside C–F.

---

# **8. Development Philosophy**

1. **Deterministic first, predictive second.**
2. **The JSON DB is the single source of truth.**
3. **Rules code is never approximate.**
4. **Simulation is not intelligence.**
5. **Coaching explanations come last.**

---

# **9. Test Strategy**

### Unit Tests

* Projection tests for every J-pattern class
* Pawn math tests (flip chains, multi-turn sequences)
* Effect lifetime tests (whileInPlay, onDestroy, spawn effects)
* Legality enforcement tests
* Scoring tests across randomized board states

### Integration Tests

* Simulation tests for full turns
* Deck + draw sequence tests
* Token generation tests
* High-complexity pattern boards

### Regression Tests

* Must run after every patch to rules or engine

---

# **10. Next Action Queue (2025-12-05)**

*This is exactly what we do next, in order.*

### **A. Completed (Option D) — Repo/Project Folder Restructure**

The ChatGPT Project folder is now in optimal condition for fast access.

### **B. Start Phase C (Simulation Layer)** **← We begin this next**

Specifically:

1. Implement PlayerHand & EnemyHand models
2. Implement Deck model + seeded RNG
3. Add mulligan logic
4. Add draw-phase logic
5. Add playCardFromHand() canonical interface

Once this is done, we move to Observation Model → Prediction → Coaching Layer.