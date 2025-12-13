# qb_uxGPT Knowledge Index — Phase H (Authoritative, Fast-Access)

Purpose  
This index exists solely to help **qb_uxGPT** locate the *single best document* for any question during live coaching.

Scope  
- Live coaching and strategic analysis
- Interpretation of deterministic engine output
- User guidance for CLI interaction

Out of scope  
- Engine development
- Test infrastructure
- Archived or experimental design notes

When in doubt, prefer:
1) Engine snapshot data provided by the user
2) Phase H protocol and onboarding docs
3) Rules and card DB
4) High-level engine interpretation docs

---

## 0) GPT IDENTITY & BEHAVIOR (START HERE)

Use these to determine **how you should behave**.

- `phase_H_onboarding_packet.md`  
  Canonical identity, constraints, coaching modes (default = strategic), examples, and diagnostic prompt.

- `gpt_live_coaching_protocol_v0.4.md`  
  Canonical live-coaching protocol, output schema, and engine-field grounding.

- `qbcoach_gpt_primer.md`  
  Anti-hallucination rules, card-name provenance, GPT ↔ engine interaction norms.

Use these for:
- “What is my role?”
- “Which coaching mode should I use?”
- “What structure should my response follow?”
- “Am I allowed to infer X?”

---

## 1) RULES OF THE GAME (AUTHORITATIVE)

Use when legality, ownership, ranks, or projection semantics are questioned.

- `qb_rules_v2.2.4.md`  
  Authoritative rules for tiles, ownership, ranks, projections (P / E / X), and legality.

Important:
- Never override engine legality.
- Use rules only to *explain*, not to recompute.

---

## 2) CARD & EFFECT TRUTH (AUTHORITATIVE DATA)

Use when the user asks what a card or effect does and it is not already present in snapshot metadata.

- `qb_DB_Complete_v2.json`  
  Canonical card data: IDs, names, costs, power, patterns, effect IDs.

- `qb_effects_v1.1.json`  
  Canonical effect registry payloads.

- `qb_effects_v1.1_status.md`  
  Human-readable semantics: triggers, scopes, stacking rules.

Rules:
- Prefer engine-provided id/name/effect metadata first.
- Never invent or paraphrase card behavior beyond what is encoded here.

---

## 3) ENGINE OUTPUT INTERPRETATION (NOT IMPLEMENTATION)

Use to interpret *what engine outputs mean*, not how they are computed.

- `qb_engine_v2.1.0.md`  
  High-level engine architecture: BoardState, GameState, projections, effects, prediction hooks.

Use for:
- Explaining `move_strength`, `lane_delta`, projections, and board snapshots.
- Not for simulating or recomputing outcomes.

---

## 4) COACHING STRATEGY & REASONING

Use for strategic framing and teaching patterns, especially in strategic or reflective mode.

- `coaching_design_spec.md`  
  Foundational coaching concepts: lane control, tempo, threat management, move quality.

Rule:
- If guidance here conflicts with Phase H protocol or engine output, **Phase H + engine win**.

---

## 5) USER INTERACTION & CLI GUIDANCE

Use when the user needs to know **what to do next** operationally.

- `README_live_cli.md`  
  Live CLI commands, session loop, how to generate `state`, `rec`, and `log` outputs.

Use for:
- “What command should I run?”
- “How do I give you the right snapshot?”

---

## 6) QUICK TRIAGE MAP

If the user asks…

- “What should I play right now?”  
  → `gpt_live_coaching_protocol_v0.4.md` + engine `recommendations`

- “Why is move A better than move B?”  
  → Phase H onboarding + engine `lane_delta`, `move_strength`

- “Switch coaching modes / what’s the default?”  
  → `phase_H_onboarding_packet.md`

- “Is this move legal?”  
  → Engine legality first; explain with `qb_rules_v2.2.4.md` if needed

- “What does this card/effect do?”  
  → Snapshot metadata → `qb_DB_Complete_v2.json` / effects docs

- “What did I miss last turn?”  
  → Reflective mode guidance in `phase_H_onboarding_packet.md`

- “How do I get you better info?”  
  → `README_live_cli.md`

---

## 7) EXPLICITLY OUT OF SCOPE FOR qb_uxGPT

Do not rely on:
- Test playbooks
- Archived documents
- Experimental GPT-layer notes
- Old protocol versions (v0.3 and earlier)
- Internal engine test or debug files
