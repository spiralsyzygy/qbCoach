# qb_devMap_v1.0.0.md  
Queen’s Blood Engine — Development Map & Issue Taxonomy  
Version 1.0.0 (Post Epics A–E)

---

# 0. Purpose

This document defines:

- The overall architecture of qbCoach  
- The canonical development roadmap  
- All Epics (A–E) and their scope  
- The issue taxonomy used for structured bug reporting  
- Guidelines for writing delta patches  
- Versioning standards for rules, engine, prompt, diagnostics  
- Future Epic placeholders  

The purpose is to stabilize the engineering process, reduce drift,
and ensure that future upgrades build cleanly on qbCoach_v2.1.

---

# 1. Architecture Summary

qbCoach_v2 consists of the following major systems:

### 1.1 Rules Layer (source of truth)
`qb_rules_v2.x`

Defines strict, mechanical rules:

- tile state model  
- pawn ranks  
- ownership  
- placement legality  
- projection mapping  
- scoring (laneScore, matchScore)  
- destruction semantics  

Rules layer contains **no heuristics** and no recommendations.

---

### 1.2 Engine Layer (implementation logic)
`qb_engine_v2.x`

Defines:

- CardHydrator  
- BoardState structure  
- LegalityChecker  
- ProjectionEngine + PawnDeltaLayer  
- CardDestructionEngine  
- Scoring evaluator (LanePowerEvaluator)  
- PredictorEngine (v1 and upcoming v2)  
- MoveRanker  
- Diagnostic hooks  

This is the “execution” layer.

---

### 1.3 Core System Prompt
`qbCoach_v2 core-system prompt v1.x`

Defines runtime behavior:

- identity  
- responsibilities  
- what to output  
- what not to output  
- visual conventions  
- coaching heuristics  
- user-interaction contract  

Must match rules & engine versions.

---

### 1.4 Diagnostic Layer
`qb_startup_self_diagnostic_v1.x`

Runs integrity tests:

- hydration  
- tile geometry  
- projection validity  
- PawnDelta reversibility  
- scoring consistency  
- prediction consistency  
- drift detection  

---

### 1.5 Support Docs
- `qb_visualization_conventions_v1.x`  
- Opponent profiles (`qb_opponent_profile_*`)  
- Deck profiles (`*_deck_profile.md`)  
- Development map (this document)

---

# 2. Epic Summary (A–E)

Each Epic represents a major subsystem.

---

## **Epic A — Card Hydration**

**Status:** COMPLETE  
**Version:** Implemented in engine ≥ v2.0.1

Defines how the engine retrieves authoritative card data from JSON DB:

- cost  
- power  
- pattern  
- grid  
- effect text  

Engine must never infer or hardcode card attributes.

---

## **Epic B — Tile Model & Legality**

**Status:** COMPLETE  
**Version:** Implemented in engine ≥ v2.0.2

Defines:

- canonical tile model  
- empty vs occupied semantics  
- visibleRank rules  
- legal placement conditions  

Ensures no illegal move suggestions.

---

## **Epic C — Projection Engine**

**Status:** COMPLETE  
**Version:** Implemented in engine ≥ v2.0.3

Adds:

- P/E/X projection rules  
- pattern-grid mapping  
- PawnDeltaLayer (per-card pawn deltas)  
- destruction reversibility  
- effect lifetimes  

Introduced the correct flip-chain model and fixed all prior drift issues.

---

## **Epic D — Scoring & Predictor Engine**

**Status:** COMPLETE  
**Version:** Implemented in engine ≥ v2.1.0

Adds:

- strict scoring (rules-level)  
- LanePowerEvaluator v2.1  
- PredictorEngine v1 (1-ply enemy reply)  
- deterministic move ranking  

This is the first version of qbCoach that produces *strong* coaching.

---

## **Epic E — Deck & Opponent Modeling**

**Status:** APPROVED  
**Version:** To be implemented in engine v2.2.x

Will add:

- PlayerDeckModel  
- OpponentDeckModel  
- Threat modeling  
- Probabilistic predictor  
- Anticipatory trap detection  

Large Epic; staged rollout recommended.

---

# 3. Issue Taxonomy (How qbCoach Should Classify Bugs)

When qbCoach generates issue logs, it must categorize problems into:

---

## **Category A — Hydration & Card Data**

Examples:

- Incorrect cost/power/pattern  
- Missing JSON entry  
- Hydration not triggered on card reference  
- Stale cached card data  

---

## **Category B — Tile Model / Legality**

Examples:

- Suggesting a move on an occupied tile  
- Misreading visibleRank  
- Allowing play onto ENEMY tiles  
- Incorrect owner assignment  
- Neutral tile treated as playable  

---

## **Category C — Projection / PawnDelta**

Examples:

- Pattern mapped incorrectly  
- X tile not applying effect  
- PawnDelta not removed on destruction  
- Ranks exceeding max 3  
- Tile ownership not recalculated  

---

## **Category D — Scoring / Predictor**

Examples:

- laneScore mismatch  
- predictor ignoring enemy replies  
- incorrect laneValue weighting  
- unexpected move ordering  
- ignoring effect-based power changes  

---

## **Category E — Deck Modeling (Epic E)**

For future issues, such as:

- Incorrect opponent deck inference  
- Draw probability errors  
- Incorrect threat modeling  
- Predicting cards that cannot exist  

---

## **Category F — Visualization**

Examples:

- Missing ★ markers  
- Showing pawn ranks on occupied tiles  
- Incorrect board layout  
- Abbreviation errors  

---

## **Category G — Diagnostic / Drift Detection**

Examples:

- Engine diverges from user-reported board  
- PawnDelta sums mismatch tile state  
- Legality reports inconsistent with rules  

---

# 4. Versioning Rules

Each KB doc follows semantic versioning:

```

MAJOR.MINOR.PATCH

```

### 4.1 Rules Doc  
- **MINOR** bumps for new rule clarifications  
- **PATCH** for corrections  
- **MAJOR** only if game mechanics change (rare)

### 4.2 Engine Doc  
- **MINOR** for new features (C → D → E)  
- **MAJOR** for architecture redesign  
- **PATCH** for fixes

### 4.3 Core Prompt  
- Parallel minor bump when engine changes behavior  
- Patch bump for wording fixes  
- Major bump only for complete rebuild

---

# 5. Patch Workflow

Each engineering cycle must follow:

1. Draft Epic spec  
2. Produce patch deltas for affected docs  
3. User reviews and approves  
4. Emit full version-bumped documents  
5. Integrate into the KB  
6. Run a regression test (startup diagnostic)  
7. Collect issue logs from real matches  

---

# 6. Future Epics (Reserved)

These are future expansion areas:

- **Epic F — Multi-Turn Planning** (2–3 ply tree)  
- **Epic G — Effect-Specific Simulators** (e.g., persistent auras, conditional triggers)  
- **Epic H — Adaptive Coaching Styles** (aggro, control, default)  
- **Epic I — UI/UX Visualization Upgrade** (advanced diagrams)  

Epic E must complete before F/H are feasible.

---

# 7. Developer Notes

- Issue logs should reference categories A–G.  
- Patches should be minimal and modular.  
- Always separate rules from heuristics.  
- When user provides board state, engine state must overwrite itself immediately.  
- Destruction must always remove PawnDelta contributions.  
- Predictor heuristics must remain deterministic.

---

# 8. Version History

**1.0.0** — Initial dev map created (post Epics A–E).  