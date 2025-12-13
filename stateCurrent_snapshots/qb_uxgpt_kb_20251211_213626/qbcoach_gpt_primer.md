# qbCoach GPT Primer
_Last updated 2025-12-08 — Engine v2.1.0 / Effects v1.1 — Tests 109/109 green_

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
- **Card naming provenance:** whenever you mention a card, derive its name from the engine metadata (id → name) present in the current snapshot/logs. Never invent or guess names; if a name is missing, say so explicitly.

## 5. Interaction Conventions
- Keep long-form content in `/docs/`; keep prompts/specs concise and scoped.
- Use pytest for validation; report pass/fail with affected tests.
- For live coaching, prefer session mode awareness and authoritative hand/board sync ops.

## 6. Visualization Reference
- Follow `qb_visualization_conventions_v1.0.0.md` for pattern grids, board diagrams, symbols, and effect markers. Link it whenever visual output is required.

## 7. Phase H — Strategic Coaching Modes
- Coaching modes: **strict (default)**, **strategy**, **reflective**. Echo the selected mode in `[SESSION]` and snapshots.
- Engine-grounded outputs:
  - Each move includes `move_strength`, `lane_delta`, and a `projection_summary.tile_deltas` diff.
  - Snapshots include `lanes` (per-lane you/enemy/net power) and `global` score estimates.
  - Never recommend moves outside engine recommendations unless explicitly asked to analyze arbitrary legal moves; if analyzing user-suggested off-list moves, call out the engine ranked them lower or omitted them.
- Card names: always from engine metadata in the snapshot; never guess or nickname.

## 8. Navigation
- Start here for GPT/Codex collaboration norms.
- See `PROJECT_INDEX.md` for the full doc map and phase packs.
- See `roadmap.md` and `phase_G_milestone_map.md` for milestones.
- Core specs: rules/engine/effects/scoring/observation/prediction/coaching.
- GPT layer: `gpt_layer_design_overview.md`, `GPT_layer/gpt_live_coaching_protocol_v0.4.md` (v0.3 retained for history), `GPT_layer/chatGPT+Codex_dual_initialization`, `GPT_layer/gpt_effects_layer_note.md`.

## 9. Card-name sanity (for GPT devs)
- If GPT output ever uses a card name that is not present in the current snapshot metadata, treat it as a GPT-layer bug.
- Card ids and names supplied by the engine are authoritative; nicknames/aliases are not allowed in analysis or recommendations.
- When users provide free-form decks/hands, parse the tokens and call the engine/bridge resolver; if it reports unknown/ambiguous tokens, repeat the resolver message and ask the user to clarify. Never guess.
