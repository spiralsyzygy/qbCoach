# GPT Live Coaching Cheat Sheet (Engine v2.1.0 / Effects v1.1)

This guide is for GPT-layer agents interacting with the deterministic qbCoach engine via the live-coaching bridge/CLI. It summarizes how to read/write state, what to log, and how to keep the conversation consistent with the engine.

## Session Modes
- Default for live coaching: `session_mode="live_coaching"`.
- Session metadata: `session_id`, `turn`, `side_to_act`, optional `enemy_deck_tag`.

## Core Ops (via EngineBridge/CLI)
- **State**: `get_state()` → GameSnapshotJSON (session, board, you_hand, engine_output, chosen_move).
- **Hand sync**: `sync_you_hand_from_ids(card_ids)` — user-reported hand is authoritative.
- **Enemy play**: `register_enemy_play(card_id, row, col)` — mirror IRL enemy plays onto the board.
- **Your move**: `apply_you_move(card_id, row, col)` — applies move if legal; else returns error.
- **Recommend**: `recommend_moves(top_n=3)` — coaching output (YOU margin perspective).
- **Prediction**: `get_prediction()` — threat map (YOU margin perspective).
- **Snapshot + Log**: `create_turn_snapshot(...)` + `append_turn_snapshot(snapshot)` → JSONL in `logs/live/`.
- **Formatting**: `format_turn_snapshot_for_ux(snapshot)` → A.5 text block for qb_uxGPT.

## TurnSnapshot (logging & UX)
Keys:
- `session`: mode, session_id, turn, side_to_act, enemy_deck_tag
- `board`: 3×5 tiles; owner/rank; card_id if occupied
- `you_hand`: list of card_ids
- `engine_output`: recommend_moves + prediction (when requested)
- `chosen_move`: you move applied (or null)

## A.5 Text Block (paste to qb_uxGPT)
Sections:
- `[SESSION]` — mode, session_id, turn, side_to_act, enemy_deck_tag
- `[BOARD]` — Top/Mid/Bot rows; cols 1–5; ranks shown only on empty tiles
- `[YOU_HAND]` — card_ids list
- `[ENGINE_OUTPUT]` — recommendations and prediction summary

Use `format_turn_snapshot_for_ux(snapshot)` to ensure consistent formatting and visualization conventions.

## Card Resolution
- Accepts card IDs (e.g., `"020"`) or names (case-insensitive, quotes/whitespace tolerated).
- Use `resolve_card_id(identifier)`; raise/handle errors on unknown/ambiguous input.

## Live Coaching Conventions
- User reports are authoritative for draws/hands/plays.
- Do not invent rules or effects; call engine ops only.
- Rows: top/mid/bot (t/m/b). Cols: 1–5.
- Illegal moves: surface engine error; do not mutate state/logs.

## Files to Know
- `qb_engine/live_session.py` — LiveSessionEngineBridge (ops, snapshots, logging).
- `qb_engine/cli/qb_live_cli.py` — CLI wrapper and REPL commands.
- `qb_engine/cli/README_live_cli.md` — CLI usage for humans.
- Specs: `docs/qb_live_cli_design_spec.md`, `docs/gpt_live_coaching_protocol_v0.2.md`.

## Logging
- JSONL in `logs/live/<timestamp>_live_[enemy_tag].jsonl`.
- Each line = TurnSnapshot; use for replay/training/evaluation.
