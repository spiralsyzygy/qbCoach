# qbCoach Snapshot — Senior Architect Handoff

Snapshot archive: `stateCurrent_snapshots/qbCoach_snapshot_20251214_181424_senior_architect_handoff.zip`

Use this README to navigate the contents quickly. It highlights the core engine, data loading, GPT interface, and supporting docs/tests.

## Core Engine (board state, projection, legality)
- `qb_engine/board_state.py` — Tile/Board model, influence recompute, invariants, occupant tracking.
- `qb_engine/game_state.py` — Turn flow, play/pass/draw, integrates projection/effects/legality.
- `qb_engine/projection.py` — Projection targets (you/enemy), pawn/effect application, pawn boundary-flip rule (rank-1 flips to attacker instead of N0; SPECIAL_PAWN_AMOUNT respected).
- `qb_engine/legality.py` — Placement legality (empty, owned, rank ≥ cost).
- `qb_engine/effect_engine.py` — Effect application pipeline (registry-driven).
- `qb_engine/scoring.py` — Lane/match scoring.

## Data Loader
- `qb_engine/card_hydrator.py` — Loads card DB (`data/qb_DB_Complete_v2.json`) and caches `Card` objects.
- `qb_engine/effect_engine.py` — Loads effect registry (`data/qb_effects_v1.1.json`).
- Card/Effect data files: `data/qb_DB_Complete_v2.json`, `data/qb_effects_v1.1.json`.

## GPT/CLI Interface
- `qb_engine/cli/qb_live_cli.py` — Live coaching REPL (commands: play, enemy, draw, pass, rec, resync_board, etc.), stateful token resolution, deck tags at init, default coaching_mode=strategy, friendly guards.
- `qb_engine/live_session.py` — Bridge for snapshots/logging, session metadata (deck tags, coaching_mode), resync_board parser.
- Docs (protocol/primer): `docs/qbcoach_gpt_primer.md`, `docs/GPT_layer/` (live coaching protocol, design overview).
- Tools for GPT KB/docs export: `tools/export_chatgpt_docs.py`, `tools/export_qb_uxGPT_kb.py`.

## Strategy/Design Docs
- `docs/dev_notes/strategy_patch_consolidated.md` — Unified strategy patch (core principles, GPT/engine application, open issues).
- Engine/rules specs: `docs/qb_rules_v2.2.4.md`, `docs/qb_engine_v2.1.0.md`, `docs/scoring_design_spec.md`, `docs/simulation_design_spec.md`, `docs/enemy_observation_design_spec.md`, `docs/prediction_design_spec_phase_E.md`, `docs/coaching_design_spec.md`, `docs/qb_visualization_conventions_v1.0.0.md`.

## Tests (high-signal)
- `qb_engine/tests/test_pawn_flip_boundary.py` — Regression for pawn boundary flip (rank-1 flips to attacker for P/X).
- `qb_engine/tests/test_cli_resync_board.py` — Resync parsing/occupant rules.
- `qb_engine/tests/test_cli_resolution.py` — Stateful token resolution.
- `qb_engine/tests/test_board_invariants.py` — Occupied tiles invariants.
- `qb_engine/tests/test_live_session_coaching_mode.py` — Default coaching_mode strategy.
- Broad coverage: `qb_engine/test_*` (legality, projection, effects, scoring, coaching).

## Snapshot Tooling
- `tools/archive_state.py` — Creates lean snapshots (the one used for this ZIP).

## Notable behaviors/fixes
- Pawn boundary flip: unoccupied opponent rank-1 (or lower) hit by pawn flips to attacker (rank = pawn amount), avoiding neutral N0; applies to P and pawn part of X.
- CLI defaults: coaching_mode=strategy; deck tags captured at session init; enemy command hard-blocked on your turn; resync_board is authoritative overwrite (tokens without :card_id clear occupants).

## Quick start (inspection)
- Board indexing: lanes 0..2 (TOP/MID/BOT), cols 0..4 (1-based in UX). See `board_state.py`, `projection.py`, `game_state.py`.
- Data parsing: start at `card_hydrator.py` and `effect_engine.py`.
- GPT prompt/UX: see `qb_live_cli.py`, `live_session.py`, and `docs/GPT_layer/*`.

If you need a lighter subset: focus on `qb_engine/`, `data/qb_DB_Complete_v2.json`, `data/qb_effects_v1.1.json`, `docs/qb_rules_v2.2.4.md`, `docs/qb_engine_v2.1.0.md`, and `docs/dev_notes/strategy_patch_consolidated.md`.
