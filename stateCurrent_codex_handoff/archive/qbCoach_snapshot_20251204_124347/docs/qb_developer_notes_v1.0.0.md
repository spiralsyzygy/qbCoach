Here is the **official Developer Notes** document for your Queen’s Blood engine + knowledge base system.
It is designed to support long-term maintainability, reproducibility, and onboarding for any future AI instance or human collaborator.

Save as:

**`qb_developer_notes_v1.0.0.md`**

---

```md
# Queen’s Blood – Developer Notes
### Version: v1.0.0
_This document explains the architecture, design decisions, patch flow, and maintenance expectations for the Queen’s Blood Coaching Engine & Knowledge Base._

---

# 1. Purpose of This Document

The `developer_notes` file exists to:

- Describe how the system is structured (rules, engine, DB, visualization)
- Explain why certain design decisions were made  
- Provide a working mental model for future maintenance  
- Outline patching workflow so ChatGPT or a human dev can reliably apply updates  
- Summarize key cross-file dependencies  
- Establish conventions for diagrams, projections, and card data  
- Provide debugging guidance and error signature recognition  

This is the “meta manual” for the entire project.

---

# 2. System Architecture Overview

The Queen’s Blood toolset consists of **five major modules**:

1. **Rules Module**  
   - Defines the authoritative game rules.  
   - Includes: board geometry, pawn logic, pattern grid, projection, scoring.

2. **Engine Module**  
   - Implements a coaching logic stack:
     - ProjectionEngine  
     - LegalityChecker  
     - Tile/Rank model  
     - HandStateEngine  
     - LanePowerEvaluator  
     - LegalMoveCounter / LockoutDetector  
     - Coaching loop (simulation + heuristics)

3. **Card Database Module (JSON DB)**  
   - Stores all card definitions:
     - id  
     - name  
     - cost  
     - power  
     - pattern string  
     - effect text  
   - Must match the in-game canonical data.

4. **Visualization Module**  
   - Defines the standardized symbols & conventions used in:
     - Pattern grids  
     - Board diagrams  
     - Legends  
     - Effect markers  

5. **Opponent Profiles Module**  
   - Optional module for opponent-specific heuristics.  
   - Example: Red XIII Behavior Profile.

---

# 3. File System Structure (Recommended)

```

qb/
├─ rules/
│   ├─ qb_rules_v2.1.3.md
│   ├─ qb_rules_patch_p1.md
│   └─ qb_visualization_conventions_v1.0.0.md
│
├─ engine/
│   ├─ qb_engine_v2.0.0.md
│   ├─ qb_engine_patch_p2.md
│   └─ qb_engine_test_playbook_v1.0.0.md
│
├─ data/
│   ├─ QB_DB_Complete_v2.json
│   └─ qb_db_patch_delta_p3.md
│
├─ opponents/
│   └─ qb_opponent_profile_red_xiii_v1.0.0.md
│
└─ meta/
└─ qb_developer_notes_v1.0.0.md

```

This structure minimizes cross-file ambiguity and simplifies patch deployment.

---

# 4. Patch Workflow

The system uses a clean patch flow designed for usage with ChatGPT or a human maintainer.

### **4.1 Patch Creation Phases**

Each major patch falls into one of three categories:

- **Rules Patch (P1)**  
  - Updates coordinate systems, legality rules, projection math.

- **Engine Patch (P2)**  
  - Updates logic, pseudocode, and subsystem APIs.

- **Database Patch (P3)**  
  - Updates JSON entries (names, power values, patterns, effects).

### **4.2 Delta Patch Format Requirements**

Every patch uses the “AI delta patch” format:

```

FIND THIS BLOCK: <anchor lines>

DELETE UNTIL: <end anchor>

REPLACE WITH: <new block>

```

No ambiguous instructions should appear.

### **4.3 Patch Application Steps**

1. Provide the target file to ChatGPT.  
2. Provide the delta patch.  
3. Ask:
   > “Apply this patch to the provided file.”  
4. ChatGPT produces a fully patched file.  
5. Copy/paste into local version.  
6. Run the **Test Playbook**.

If all tests pass → patch is accepted.

---

# 5. Cross-Module Dependencies

Some modules depend on others:

### **5.1 Engine → Rules**
- Engine projection, tile logic, legality rules derive entirely from `qb_rules`.
- Rules must always be updated **before** engine patches.

### **5.2 Engine → JSON DB**
- Pattern and card power values come directly from DB.
- If DB is stale, engine logic mis-evaluates board state.

### **5.3 Visualization → Rules**
- Board/pattern diagrams must follow the same coordinate system and offsets.

### **5.4 Opponent Profiles → Engine**
- Profiles assume engine logic is stable and accurate.
- Profiles should never define new rules or override engine logic.
- They are purely heuristic guidance.

---

# 6. Debugging Reference (Error Signatures)

These are the canonical signs something is wrong.

---

## 6.1 Projection Errors

**Symptoms:**
- Zu fails to hit MID-3 from BOT-2  
- AD’s X tile applied in wrong direction  
- Projections appear mirrored incorrectly  

**Likely causes:**
- Δcol miscomputed  
- YOU/ENEMY mirror inverted  
- Wrong pattern coordinates (E, D, C, B, A misordered)

Remedy:
- Re-run the ProjectionEngine section in Test Playbook.

---

## 6.2 Lane Power Errors

**Symptoms:**
- Lane power uses ranks instead of card power  
- Empty tiles appear to add power  
- Power totals don’t match visible cards

**Likely causes:**
- Tile.rank confused with Tile.card.power  
- Card DB power values out of sync

Remedy:
- Re-run Lane Scoring tests.

---

## 6.3 HandState Drift

**Symptoms:**
- Cards that were played remain in hand  
- Phantom duplicates  
- Recommendations mention cards you do not possess  

**Likely causes:**
- Play action not removing exact card instance  
- Draw action not handled  
- Sync-from-user not applied  

Remedy:
- Use the HandState test suite.

---

## 6.4 Illegal Move Suggestions

**Symptoms:**
- Suggested move tries to place a card on an occupied tile  
- Suggested move tries to place on Neutral tile  
- Suggested move ignores rank cost

**Likely Causes:**
- Missing occupancy check in LegalityChecker  
- Tile owner not validated  
- Rank incorrectly sourced  

Remedy:
- Run Move Legality test suite.

---

## 6.5 Geometry Lockout

**Symptoms:**
- Engine doesn’t warn when column 2 becomes full  
- Engine suggests move that consumes the last playable tile  
- Self-lock happens unexpectedly

**Likely cause:**
- LegalMoveCounter not implemented  
- LockoutDetector not invoked  

Remedy:
- Run Lockout Detection tests.

---

# 7. Engine Quality Gates

The engine must pass these checkpoints before being used for live match coaching.

### **Gate A: Projection**
- Zu @ BOT-2 hits MID-3  
- AD X-tile hits correct lane/column

### **Gate B: Legality**
- Cannot play on occupied or neutral tiles  
- Cannot play with insufficient rank  
- Rank ≥ cost always enforced

### **Gate C: Lane Scoring**
- Rank never affects lane power  
- Only W-tile occupants count

### **Gate D: HandState**
- Play removes exactly one copy  
- Draw appends  
- Sync overwrites

### **Gate E: Lockout**
- Detects 0-legal-move state  
- Warns on 1-legal-move state  
- Warns on self-lock sequences

Only after all gates are green is the engine considered “match-ready.”

---

# 8. Versioning Philosophy

We maintain a simple versioning scheme:

### **Major Version (X.0.0)**
- Major rule/engine overhauls  
- New mental models  
- Cross-module synchronization required  

### **Minor Version (X.Y.0)**
- Feature additions  
- New test cases  
- Non-breaking improvements  

### **Patch Version (X.Y.Z)**
- Bug fixes  
- Documentation corrections  
- DB patches  

Current stable versions:

```

rules:   v2.1.3 (+ Patch P1)
engine:  v2.0.0 (+ Patch P2)
db:      v2.0.0 (patched JSON)
visual:  v1.0.0
tests:   v1.0.0
opponents: v1.0.0
developer notes: v1.0.0

```

---

# 9. Extending the System (Future Work)

The system is built to accommodate:

- Additional opponent profiles  
- Deck simulation engines  
- Monte Carlo match prediction  
- Automated strategy tree exploration  
- Tournament-tier play patterns  
- Deeper heuristics (lane value, board tension, tempo lines)

Future version may introduce:

- “Geometry pressure” metrics  
- Predictive lockout modeling  
- Full turn-based enemy simulation  
- Expanded UI diagrams for visual summaries

---

# 10. Maintenance Checklist

Before committing any new update:

- [ ] Apply delta patch  
- [ ] Run the Test Playbook  
- [ ] Validate JSON DB using sample cards  
- [ ] Re-run projection tests  
- [ ] Recalculate lane powers on multiple examples  
- [ ] Confirm coaching outputs match corrected rules  
- [ ] Update version headers  
- [ ] Update Developer Notes

Once all tests pass, increment version appropriately.

---

# 11. Summary

The Queen’s Blood Coaching Engine is now a well-structured, rules-accurate, geometry-aware system.  
These developer notes ensure:

- Consistency over time  
- Reproducibility across ChatGPT instances  
- Easy debugging  
- Long-term maintainability  
- Reliable match coaching  

This document must accompany the rules, engine, and DB for every future major update.

---

# 12. Document Status

- Version: **1.0.0**  
- Fully stable  
- Completes Phase 1 of the Bug Squash & Engine Hardening cycle  

# END DOCUMENT