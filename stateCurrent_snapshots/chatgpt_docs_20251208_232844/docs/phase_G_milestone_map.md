# Phase G Milestone Map
qbCoach – GPT Layer Development  
Engine v2.1.0 • Effects v1.1 • All 75 tests passing

This document defines the complete milestone sequence for Phase G.  
Phase G builds the entire GPT-facing architecture on top of the fully deterministic Python engine.

The GPT Layer does:
- High-level reasoning, explanation, planning  
- UX & interaction  
- Self-play  
- Enemy modeling  
- Episode logging  
- Querying the engine  
- Codex prompt construction  

It does *not* perform game mechanics, legality checks, projections, scoring, or effects.

---

# 📍 **Milestone G0 — GPT Layer Foundations (Completed Pre-Phase)**

**Deliverables:**
- GPT initialization prompt  
- Codex initialization prompt  
- GPT↔Codex collaboration protocol  
- Dev workflow summary  
- Engine + effects fully tested & deterministic

**Status:** ✔ Done

---

# 📍 **Milestone G1 — GPT Layer Core Architecture**

**Goal:** Establish the scaffold for all GPT-layer functionality.

### G1.1 — GPT Layer Roles & Boundaries
- Distinguish GPT reasoning vs deterministic engine duties  
- Define:  
  - high-level strategy  
  - UX  
  - turn-loop reasoning  
  - Codex prompt generation  

### G1.2 — GPT ↔ Engine Message Grammar
Define deterministic serialization formats for:
- BoardState  
- Hand  
- AvailableMoves  
- Projection outputs  
- Scoring outputs  
- EnemyObservation snapshots  
- CoachingRecommendation structure  

### G1.3 — GPT Layer Internal State Model
Define in-GPT structures for:
- Current turn context  
- Planned actions  
- Enemy profile references  
- Active episode log  
- Running explanation model (“why we choose X”)

**Deliverables:**  
- `gpt_api_bridge_spec.md`  
- Messaging grammar  
- GPT state model  
- Clarified GPT/engine pipeline

---

# 📍 **Milestone G2 — Live Coaching Protocol**

**Goal:** Build the protocol for real-time, turn-by-turn coaching.

### G2.1 — Input/Output Conventions
- Human input grammar  
- Engine API request format  
- Board visualization rules  
- GPT turn summaries  

### G2.2 — Deterministic Turn Loop
- How GPT requests engine projections  
- How GPT selects or ranks candidate plays  
- How GPT provides final “Recommended Action”

### G2.3 — Explanatory Layer
- Why this move works  
- Threat analysis (via engine outputs)  
- Lane-by-lane reasoning  
- Power + effect context  
- Safety checks (“explicitly legal move selection”)

### G2.4 — Error Recovery
- Invalid human input  
- Engine errors  
- Ambiguous states  
- Branch repair  

**Deliverables:**  
- `gpt_live_play_spec.md`  
- Turn-loop diagrams  
- Play recommendation schema  
- Engine-explanation integration rules

---

# 📍 **Milestone G3 — Self-Play Mode**

**Goal:** Construct GPT-driven self-play to explore games, generate training logs, and benchmark heuristics.

### G3.1 — Self-Play Loop
- Deterministic alternating calls  
- Engine → GPT → Engine feedback loop  
- Branching evaluation  

### G3.2 — Variation / Diversity Controls
- Move temperature  
- Exploration depth  
- Stop conditions (round end / lane resolution)  

### G3.3 — Teacher Mode
- Annotated reasoning  
- Mistake detection  
- “What-if” variations  

### G3.4 — Summaries
- Final game reports  
- Decision review  
- Effect usage analytics  

**Deliverables:**  
- `gpt_self_play_spec.md`  
- Self-play orchestration rules  
- Variation heuristics  

---

# 📍 **Milestone G4 — Enemy Profiles & Memory**

**Goal:** Integrate the deterministic **EnemyObservation** engine with GPT’s long-range reasoning.

### G4.1 — Observation Ingestion
- Convert EnemyObservation into human-readable descriptors  
- Distinguish between:  
  - card_seen  
  - tile_seen  
  - pawn_delta_seen  
  - enemy_play_patterns  
  - board-based inference  

### G4.2 — Deck Profile Model
- Enemy card spectrum  
- Play sequencing tendencies  
- Effect usage fingerprints  
- Lane preferences  

### G4.3 — Behavioral Tags
- Aggressive lane-pushing  
- Token-spam  
- Replacement-based engines  
- High-rank control  
- Scaling effects patterns  

### G4.4 — Memory Storage
- Persistence schema  
- Update rules after each game  
- Long-term profile drift  

**Deliverables:**  
- `gpt_enemy_profiles_spec.md`  
- Profile schema  
- Update logic  
- Tag ontology  

---

# 📍 **Milestone G5 — Episode Logging**

**Goal:** Create a durable record of games for replay, training, analysis, and memory.

### G5.1 — Log Schema
- One record per turn  
- One record per decision  
- Board snapshots  
- Hand snapshots  
- EnemyObservation snapshots  
- CoachingRecommendations  
- Outcome metrics  

### G5.2 — Serializers & Deserializers
- JSON or msgpack format  
- Versioning scheme  
- Compact storage  

### G5.3 — Automated Summaries
- Lane histories  
- Swing moments  
- Mistake clusters  
- Effect usage timelines  
- Enemy pattern extraction  

**Deliverables:**  
- `gpt_episode_logging_spec.md`  
- Log schema v1  
- Replay format rules  

---

# 📍 **Milestone G6 — UX & Interaction Model**

**Goal:** Design a clean, expressive, user-friendly interaction layer.

### G6.1 — Visualization Conventions
- Board state diagrams  
- Hand formatting  
- Effect summaries  
- Threat maps  

### G6.2 — Conversation Protocol
- Short vs long-mode explanations  
- Asking for user input  
- Safety prompts  
- Live-play pacing  

### G6.3 — Coach Persona
- Calm, precise, deterministic  
- Accuracy > confidence  
- Avoid all hallucinations  
- Ask for clarification when unsure  

**Deliverables:**  
- UX reference  
- Visualization examples  
- Persona guidelines  

---

# 📍 **Milestone G7 — Integration & Finalization**

**Goal:** Stitch all subsystems into one cohesive GPT Layer.

### G7.1 — Orchestration Layer
- Unified API  
- Mode switching (Live / Self-play / Analysis / Replay)  
- Session state machine  

### G7.2 — Documentation
- All `/docs/gpt_*.md` complete  
- Codex prompts finalized  
- Tool wrappers available  

### G7.3 — Release Candidate (GPT Layer v1.0)
- Full feature checklist  
- Internal tests (conversation simulations)  
- Freeze  
- Tag release  

**Deliverables:**  
- Complete GPT Layer documentation  
- Stable GPT initialization prompt  
- Stable Codex initialization prompt  
- Release notes  

---

# 📍 **Phase G Exit Criteria**

- All Milestones G1–G7 complete  
- GPT Layer operational across:
  - Live Coaching  
  - Self-Play  
  - Enemy Profiling  
  - Episode Logging  
  - Engine Interface  
  - UX Visualization  
- Codex tooling stable  
- All Python tests pass (≥75)  
- No rule or DB inconsistencies  
- GPT safely constrained to deterministic sources  

---

# 📘 End of Phase G Milestone Map
