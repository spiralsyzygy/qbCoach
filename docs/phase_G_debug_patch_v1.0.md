# Phase G — Live Coaching Debug Patch v1.0 Checkpoint

## Overview

This patch set addresses the live coaching desync discovered in session `20251209T004312`, where:

- Archdragon’s `X` projections were mis-modeled as effect-only.
- Archdragon’s JSON grid did not align with its pattern.
- The internal legality board diverged from the rendered `[BOARD]`.
- Enemy Spearhawk @ TOP-3 was rejected as illegal while the printed board and FF7R both agreed it was legal.

The fixes bring the deterministic engine back into alignment with **Rules v2.2.4** and the observed FF7R behavior, and harden the GPT-layer naming behavior.

---

## Engine Changes

### 1. Pattern-Driven Projection (Canonical Source of Truth)

**Files:**  
- `qb_engine/card_hydrator.py`  
- `qb_engine/projection.py`  

**Behavior:**

- `card.pattern` is now the canonical source of projection geometry.
- `card_hydrator.py` parses pattern strings (e.g. `B3X,D2P,D4P`) into a list of `ProjectionCell(row_offset, col_offset, symbol)`.
- Hydrated cards carry `projection_cells` as part of their enriched metadata.
- `ProjectionEngine` iterates `projection_cells` (pattern-derived) to project onto the 3×5 board.
- The JSON `grid` remains in `qb_DB_Complete_v2.json` but is no longer used for operational logic; it is a visual/sanity artifact only.

### 2. Correct `X` Semantics (P + E)

**Files:**  
- `qb_engine/projection.py`  
- `qb_engine/test_projection_apply.py`  

**Behavior:**

- `X` now behaves exactly as specified in Rules v2.2.4:

  > X = pawn projection (P) followed by effect projection (E).

- Implementation:
  - `X` dispatch calls the same pawn helper used for `P`.
  - Then calls the same effect helper used for `E`.
- This affects both YOU and ENEMY plays; mirroring uses the same projection dispatch.
- Tests added:
  - `X` applies both pawn and effect to an empty tile.
  - `X` can be the first pawn contribution on a neutral tile (claims ownership).
  - Archdragon `X` stacked with Crawler `P` yields the expected `[Y2★]` state on the shared tile.

### 3. DB Consistency Validator & Archdragon Grid Fix

**Files:**  
- `qb_engine/card_db_validator.py`  
- `qb_engine/test_card_db_consistency.py`  
- `data/qb_DB_Complete_v2.json`  

**Behavior:**

- `pattern_to_grid()` reconstructs a 5×5 visual grid from `card.pattern` with `W` at center `(2,2)`.
- Validator tests:
  - `test_all_cards_center_w` asserts `grid[2][2] == "W"` for every card.
  - `test_pattern_matches_grid_for_all_cards` asserts pattern-derived non-`.` cells match DB `grid`.
  - `test_archdragon_pattern_grid_match` locks Archdragon’s visual grid to its pattern.
- Archdragon’s JSON `grid` is updated to match its pattern `B3X,D2P,D4P`. No other card data changed.
- Any future drift between pattern and grid will be caught by CI via these tests.

### 4. BoardState ↔ Legality Consistency

**Files:**  
- `qb_engine/live_session.py` (and related board/legality modules)  
- `qb_engine/test_legality_board_consistency.py`  

**Behavior:**

- The BoardState used by the renderer and by `LegalityChecker` is now a single, authoritative instance.
- Board snapshots (for CLI/GPT) render directly from this BoardState.
- Tests assert that:
  - Tiles rendered as empty and owned with sufficient rank are legal placement targets for a matching-cost test card.
  - Tiles rendered as occupied, neutral, or with insufficient rank are illegal.
- This prevents “printed legal but evaluated illegal” desyncs like the Spearhawk @ TOP-3 incident.

### 5. End-to-End Regression: Archdragon → Crawler → Spearhawk

**Files:**  
- `qb_engine/test_live_archdragon_spearhawk_sequence.py`  

**Behavior:**

- Encodes the live session sequence as a deterministic regression test:
  - Uses real card data (Archdragon 020, Crawler 019, Spearhawk, Ignilisk, Amphidex, etc.).
  - After Archdragon’s `X` and Crawler’s `P` stack, MID-2 is asserted as `[Y2★]`.
  - Later, ENEMY Spearhawk @ TOP-3 is asserted to be a legal placement.
- This test fails under the old engine behavior and now passes, guarding against regressions in projection, DB alignment, and legality.

---

## GPT-Layer Changes

### 6. Card Naming Provenance

**Files:**  
- `docs/GPT_layer/gpt_live_coaching_protocol_v0.3.md`  
- `docs/qbcoach_gpt_primer.md`  
- `qb_engine/live_session.py`  

**Behavior:**

- Protocol v0.3 introduces a **card naming provenance rule**:
  - GPT must derive card names from engine-provided `id → name` metadata in the current snapshot.
  - If a card’s name is absent from the snapshot, GPT must say so and **must not guess**.
- Primer reinforces:
  - No nicknames or invented card names in analytical output.
  - Using a name not present in metadata is considered a GPT-layer bug.
- Engine snapshots (hand, board, recommendations, mulligans) now consistently serialize both `card_id` and `card_name`.

---

## Test Status

- Full pytest suite passing (≈ 110/110 tests).
- New DB validator and live-sequence regression add negligible runtime overhead.
- No flaky tests identified during this patch set.

---

## Known Follow-Ups / Recommended Next Steps

- Audit any additional GPT-facing serializers (e.g., gpt_bridge) to ensure they always emit `id + name`.
- Consider an optional runtime invariant for CLI debug sessions to cross-check legality vs rendered board tiles.
- Implement a robust **card name/ID resolver** for user input (CLI + GPT), so free-form card lists map safely to canonical IDs.
