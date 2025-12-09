# qbCoach GPT Primer
_Last updated 2025-12-08 — Engine v2.1.0 / Effects v1.1 — Tests 99/99 green_

This primer collects the essential GPT-facing guidance for qbCoach: roles, workflow, memory rules, and visualization references. It supersedes the legacy workflow primers and developer notes for day-to-day GPT/Codex collaboration.

## 1. Roles & Responsibilities
- **Human (Matthew):** Sets scope, runs tests, manages branches/snapshots, approves changes.
- **GPT (Architect/Strategist):** Writes clear specs and Codex prompts; never invents rules/data; keeps roadmap aligned.
- **Codex (Repo Mechanic):** Edits code/tests deterministically per prompt; does not alter DB/rules without explicit approval.

## 2. Deterministic Workflow
- Define feature → GPT drafts spec/prompt → Codex edits → run pytest → report results → update docs/roadmap → commit.
- Scope every task (files to modify/avoid, semantics, acceptance tests).
- All new engine behavior requires tests; all existing tests must stay green.
- Do not change card DB or rules unless explicitly authorized.

## 3. Memory & State Handling
- The user is authoritative; any reported board/hand/draw overrides internal state.
- Store only:
  - Stable data: card DB, effect registry, opponent profile (if any), conventions, docs.
  - Match state: BoardState, HandState, turn number, draw events — always overwrite when user corrects.
- Never store speculative info (enemy hand guesses, probabilities) or chat phrasing; recalc strategy each turn from current state.
- When unsure (e.g., user mentions a draw without naming the card), ask for confirmation before updating state.

## 4. Safety Rules
- Align with `qb_rules_v2.2.4.md`, `qb_engine_v2.1.0.md`, `qb_effects_v1.1_status.md`, scoring/observation/prediction/coaching specs.
- No ad-hoc mechanics, projection tweaks, or scoring changes.
- If semantics are unclear, stop and ask; do not improvise.

## 5. Interaction Conventions
- Keep long-form content in `/docs/`; keep prompts/specs concise and scoped.
- Use pytest for validation; report pass/fail with affected tests.
- For live coaching, prefer session mode awareness and authoritative hand/board sync ops.

## 6. Visualization Reference
- Follow `qb_visualization_conventions_v1.0.0.md` for pattern grids, board diagrams, symbols, and effect markers. Link it whenever visual output is required.

## 7. Navigation
- Start here for GPT/Codex collaboration norms.
- See `PROJECT_INDEX.md` for the full doc map and phase packs.
- See `roadmap.md` and `phase_G_milestone_map.md` for milestones.
- Core specs: rules/engine/effects/scoring/observation/prediction/coaching.
- GPT layer: `gpt_layer_design_overview.md`, `GPT_layer/gpt_live_coaching_protocol_v0.2.md`, `GPT_layer/chatGPT+Codex_dual_initialization`, `GPT_layer/gpt_effects_layer_note.md`.
