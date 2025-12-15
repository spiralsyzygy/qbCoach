# qb_live_cli — Phase G / Track A.5 Live Coaching (Preview)

This CLI is a thin wrapper over the deterministic qbCoach engine for **live coaching** sessions. It sets `session_mode="live_coaching"`, mirrors user-reported state into the engine, and produces A.5 text blocks for qb_uxGPT. Nothing here re-implements rules or effects; it simply orchestrates existing engine components.

## Quick Start

```bash
python -m qb_engine.cli.qb_live_cli
```

You’ll be prompted to:
1) Confirm starting a live coaching session.
2) (Optional) Enter an `enemy_deck_tag`.
3) Choose how to provide your deck:
   - `(a) deck tag` (no-op placeholder for now; uses a default deterministic deck)
   - `(b) explicit 15-card list` (IDs or names, comma/space separated)

After init, you land in a REPL. Enter `help` to see commands.

## Commands (current wiring)

- `draw <ids/names...>` — Sync your hand after drawing. Resolves IDs or names, then calls `sync_you_hand_from_ids`.
- `enemy <id/name> <row> <col>` — Register an enemy play on the board. Rows: `top/mid/bot` or `t/m/b`. Cols: `1..5`.
- `rec` — Compute recommendations + prediction, build a TurnSnapshot, append to JSONL log, and print the A.5 block.
- `play <id/name> <row> <col>` — Apply your move, log the snapshot. Reports errors for illegal moves.
- `pass` — First-class action: skip your turn, log `last_event="you_pass"`, and hand off to the enemy.
- `resync_board` — Debug escape hatch to overwrite the board (see below).
- `state` — Print the current snapshot (A.5-style).
- `log` — Show the current JSONL log path (created on first append).
- `resolve <id/name>` — Resolve a card to its canonical name + id (helps fix typos quickly).
- `help` — Show the command menu.
- `quit` — Exit the session.
  - Defaults: coaching_mode is `strategy`; deck tags are optional free-form labels captured at session start and displayed in `[SESSION]`.

### Ambiguous / unknown card tokens (stateful resolution)
- Any command that accepts card tokens (`draw`, `set_hand`, `play`, `enemy`) enters a resolution mode when a token is unknown/ambiguous.
- Prompt shows ordered candidates (deterministic: exact, prefix, substring, then close matches). Respond with:
  - `y` / `yes` — accept candidate 1
  - `1..N` — pick a specific candidate
  - `n` / `cancel` — abort the command; nothing is executed
- While resolving, other commands are blocked until you finish/cancel.
- Examples:
  - `draw Quetzalcoatl?` → `y` accepts `Quetzalcoatl (014)`
  - `play grasslands wlf top 2` → `1` chooses the first suggestion, then applies the play

### Manual board resync (debug)
- `resync_board` prompts for three lines (TOP, MID, BOT), each with 5 bracketed tokens:
  - Empty: `[Y1] [E2] [N0]`
  - Occupied: `[Y2:011]` or `[E:048★]` (★ optional; effects are recomputed)
  - Tokens without `:card_id` clear occupants; include `:card_id` to keep/set one.
- Before applying, the CLI shows a structured diff. Confirm with `y` to proceed.
- Effect of apply:
  - Overwrites board tiles, rebuilds pawn deltas, clears auras/direct_effects (recomputed)
  - Preserves turn/phase/hand
  - Logs a snapshot with `last_event="manual_resync_board"` and `manual_override=True`

## What Gets Logged

Every `rec`/`play` appends a **TurnSnapshot** JSON line to `logs/live/<timestamp>_live_[enemy_tag].jsonl`, including:
- `session`: mode, session_id, turn, side_to_act, enemy_deck_tag (if set)
- `board`: canonical board snapshot
- `you_hand`: your current hand (IDs)
- `engine_output`: recommend_moves, prediction (when requested)
- `chosen_move`: the move you applied (for `play`/`pass` or `manual_resync_board` marker)
- `last_event`: event tag such as `you_play`, `you_draw`, `you_pass`, `enemy_play_registered`, `recommend`, `manual_resync_board`
- `manual_override`: present/true when a manual board override was applied
- `card_resolution`: lightweight note when a token was resolved interactively

## Notes & Caveats

- This is a **preview**: enemy play handling is basic and uses the existing engine legality checks; full live-coaching semantics will continue to evolve.
- Deck tags are not yet mapped to profiles; option (a) falls back to a deterministic default deck.
- Formatting uses `format_turn_snapshot_for_ux` so the A.5 block matches qb_uxGPT expectations (rows: Top/Mid/Bot; cols: 1–5; ranks shown only on empty tiles).
- The CLI is text-only and synchronous; no HTTP or OpenAI calls are made here.

## Related Files

- `qb_engine/live_session.py` — LiveSessionEngineBridge (session state, snapshots, logging, card resolution).
- `docs/qb_live_cli_design_spec.md` — Full design spec for the live CLI.
- `docs/qb_engine_v2.1.0.md`, `docs/qb_effects_v1.1_status.md` — Core engine/effects behavior.
