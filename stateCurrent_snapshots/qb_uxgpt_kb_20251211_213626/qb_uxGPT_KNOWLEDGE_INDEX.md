# qb_uxGPT Knowledge Index (Phase H, Minimal / Fast)

Purpose: Help qb_uxGPT quickly locate the single best source for any question.
Scope: Live coaching + strategic analysis using engine snapshots. Not engine development.

---

## 0) Start Here (How qb_uxGPT should behave)
- `phase_H_onboarding_packet.md` — role, constraints, coaching modes (default = strategic), examples, diagnostic prompt
- `gpt_live_coaching_protocol_v0.4.md` — canonical live coaching protocol + structured output schema
- `qbcoach_gpt_primer.md` — GPT operating rules: anti-hallucination, “names from engine only”, workflow conventions

Use these first for:
- “What should you do / not do as the GPT layer?”
- “How do I respond in strategic vs strict vs reflective mode?”
- “What structure should my coaching output use?”

---

## 1) Rules of the Game (Authoritative)
- `qb_rules_v2.2.4.md` — legality, projections (P/E/X), ownership/ranks, scoring basics

Use for:
- Any dispute about what is legal or how tiles/ownership/ranks work.

---

## 2) Card & Effects Truth (Authoritative Data)
- `qb_DB_Complete_v2.json` — card IDs/names/cost/power/pattern/effect IDs (canonical card data)
- `qb_effects_v1.1.json` — effect registry payloads (engine-level effect definitions)
- `qb_effects_v1.1_status.md` — semantic notes: triggers/scopes/stacking rules (human-readable)

Use for:
- “What does card X do?” (only if not already provided in snapshot metadata)
- “What does ★ mean / which effect is applied?”

Important:
- Prefer engine snapshot metadata (id+name, effect IDs on tiles) over memory or inference.

---

## 3) Engine Outputs (Interpretation, Not Implementation)
- `qb_engine_v2.1.0.md` — what engine components mean at a high level (BoardState/GameState, effects, prediction hooks)

Use for:
- Interpreting snapshot fields or understanding what an output represents.
- Not for changing engine code.

---

## 4) Coaching Strategy (How to Reason)
- `coaching_design_spec.md` — coaching concepts: move quality, lane priorities, threat management (foundational)

Use for:
- Higher-level teaching and strategic framing, especially in strategic/reflective mode.

Note:
- When conflicts exist, **Phase H protocol + engine snapshot fields override** older coaching generalities.

---

## 5) CLI / User Interaction (What to Run Next)
- `README_live_cli.md` — commands, session loop, how to get `state` / `rec` / `log` outputs

Use for:
- “What should I type next?” or “How do I provide you the needed snapshot?”

---

## 6) Quick Triage Map (If user asks X, check Y)

- “What should I play right now?” → `gpt_live_coaching_protocol_v0.4.md` + engine `recommendations` in snapshot  
- “Switch modes / default behavior” → `phase_H_onboarding_packet.md`  
- “Is this move legal?” → engine legality result first; if needed, `qb_rules_v2.2.4.md`  
- “What does this card/effect do?” → snapshot metadata first; else `qb_DB_Complete_v2.json` / `qb_effects_v1.1.json` / `qb_effects_v1.1_status.md`  
- “What does lane_delta / move_strength mean?” → `gpt_live_coaching_protocol_v0.4.md`, then `qb_engine_v2.1.0.md`  
- “What did I miss last turn?” → reflective mode guidance in `phase_H_onboarding_packet.md` + compare engine-ranked moves  
- “How do I get you the right info?” → `README_live_cli.md`

---

## 7) Out of Scope for qb_uxGPT
qb_uxGPT should not rely on:
- test playbooks
- archived docs
- old protocol versions (v0.3 and earlier)
- engine internals beyond interpreting outputs
