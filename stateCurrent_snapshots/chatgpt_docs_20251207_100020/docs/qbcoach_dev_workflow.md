# qbCoach Development Workflow (One-Page Summary)

This document describes the full development workflow for the qbCoach project, covering GPT/LangChain-style orchestration, Codex-driven implementation, deterministic Python engine evolution, and safe iteration on new features.

Version: Engine v2.1.0 + Effects v1.1 + 75/75 tests green  
Layer: GPT (Phase G) + Codex Integration

---

## 1. System Layers

### **Layer 0 — Data**
- Card DB: `data/qb_DB_Complete_v2.json`
- Effect Registry: `data/qb_effects_v1.1.json`

### **Layer 1 — Deterministic Engine**
Implements **rules, effects, legality, projection, scoring**, enemy observation, and test suite.
Files under:
- `qb_engine/`
- `docs/qb_rules_v2.2.4.md`
- `docs/scoring_design_spec.md`
- `docs/enemy_observation_design_spec.md`
- Tests: `qb_engine/test_*.py`

### **Layer 2 — GPT Layer (Phase G)**
High-level reasoning, UX, coaching, self-play, profiles, and Codex prompt construction.
Docs:
- `gpt_layer_design_overview.md`
- `coaching_design_spec.md`
- `simulation_design_spec.md`
- `prediction_design_spec_phase_E.md`

### **Layer 3 — Codex (Exec Layer)**
Executes code changes.
Cannot infer rules. Fails safely when ambiguous.

---

## 2. Development Roles

### **GPT Layer (Architect/Strategist)**
- Designs specs, protocols, interfaces
- Writes fully-scoped prompts for Codex
- Uses deterministic engine outputs exclusively
- NEVER invents rules or data

### **Codex Layer (Implementation)**
- Writes Python code + tests
- Never modifies DB or rules unless authorized
- Requires:
  - Scope
  - Files to modify
  - Semantics
  - Acceptance tests

---

## 3. Development Process

### **Step 1 — User chooses track**
e.g.:
- Live Coaching Protocol  
- Self-Play Mode  
- Enemy Profiles  
- Episode Logging  
- GPT↔Engine API Bridge  
- UX/Visualization Layer  

### **Step 2 — GPT Layer drafts spec**
- Clear semantics  
- Expected behavior  
- Integration points  
- No ambiguity  
- References project docs  

### **Step 3 — GPT Layer produces Codex prompt**
Must contain:
- Task Summary  
- Scope (files to touch / not touch)  
- Authoritative semantics  
- Deterministic rules  
- Acceptance tests  
- Phase boundaries  

### **Step 4 — Codex executes**
- Implements changes  
- Adds tests  
- Runs full pytest  
- Reports success or clarifies missing semantics  

### **Step 5 — GPT Layer responds**
If Codex errors:
- Tighten instructions  
- Add missing semantics  
- Split into smaller phases  
- Reissue prompt  

### **Step 6 — User reviews + approves**
- Merge-ready commits  
- Documentation updates  
- Next development track chosen  

---

## 4. Safety & Determinism Rules

- Engine behavior must always match:
  - Official rules v2.2.4
  - Engine v2.1.0 architecture
  - Effects v1.1 semantics
  - DB + registry
  - Test suite expectations

- Codex never improvises:
  - mechanics  
  - geometry  
  - projection behavior  
  - scoring  

- GPT never describes effects beyond natural-language summaries unless documented.

---

## 5. Testing Requirements

Every Codex task must end with:
- New tests (if requested)
- All existing tests passing
- Clear implementation summary

All new engine behavior MUST be accompanied by tests.

---

## 6. When in Doubt

- GPT asks questions.
- Codex refuses unclear tasks.
- The user clarifies.

This keeps the qbCoach system deterministic, test-backed, and safely extensible.
