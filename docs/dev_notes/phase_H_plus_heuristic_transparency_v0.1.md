# Phase H+ Spec: Heuristic Transparency Layer v0.1

Repo-ready • Human-readable • AI-ready (for next chat instance + Codex)

**Status context (Phase H just completed)**
Phase H shipped reliability + UX + safety patches and is now stable enough for IRL live-coaching testing:

* **Correctness hardening:** `placed_by`, occupied tiles never neutral after recompute, invariants validated, `get_card_side` stabilized.
* **CLI UX:** stateful ambiguous-token resolution across `draw/set_hand/play/enemy`, deterministic candidate ordering, snapshot-logged resolution events.
* **Debug safety valve:** `resync_board` / `manual_resync_board` with validation, diff preview, explicit `manual_override=True` logging, deterministic rebuild.
* **PASS action:** first-class in engine + CLI + legal_moves + logging.

This H+ spec starts the next track: **Heuristic Transparency**, without changing gameplay rules or recommendation ranking.

---

## 1. Purpose

Add a **Heuristic Transparency Layer** that surfaces *why* a move is recommended (tempo, lane swing, geometry usage, denial signals) so the GPT layer can:

* explain recommendations clearly
* acknowledge tradeoffs (engine-optimal vs human-controversial)
* build trust during live coaching
* enable future evaluation improvements (geometry heuristics, temporal discounting, shallow lookahead) with measurable, explainable features

**Key principle:** This is *explanation*, not a new strategy engine.

---

## 2. Scope

### In scope (v0.1)

* Add an `explain` payload to each recommendation.
* Deterministic `heuristic_tags` + concise `reasons` derived from *existing* computed signals:

  * lane deltas
  * projection summary / tile deltas (if available)
  * (optional) legal-move count deltas if already computed cheaply and deterministically

### Out of scope (v0.1)

* Changing recommendation ordering or `move_strength` computation.
* Adding plies / lookahead.
* Adding new rule semantics, effect rules, or scoring changes.
* Adding new card DB fields.

---

## 3. Requirements

### R1 — Determinism

Given identical session state and input, `explain` must be identical:

* deterministic tag selection
* deterministic candidate ordering
* deterministic reason ordering

### R2 — Minimal footprint

* Prefer adding a small helper module (e.g., `qb_engine/explain.py`) over refactoring evaluation code.
* Do not change existing recommendation ranking behavior.

### R3 — Usable by GPT layer

* Provide compact tags + 1–3 human-readable reasons per move.
* Avoid huge payloads; no full-board diffs inside `explain`.

---

## 4. Data contract

### Recommendation object: add `explain`

Add a new block to each recommendation emitted in:

* engine recommendation payloads
* JSONL snapshots
* CLI `rec` output

**Schema v0.1**

```json
"explain": {
  "heuristic_tags": ["tempo_gain", "lane_swing_mid", "geometry_wasteful"],
  "reasons": [
    { "tag": "lane_swing_mid", "text": "+3 projected mid lane margin", "weight": 0.35 },
    { "tag": "tempo_gain", "text": "Immediate margin gain this turn", "weight": 0.25 },
    { "tag": "geometry_wasteful", "text": "Most of the pattern projects off-board or onto already-set tiles", "weight": 0.15 }
  ],
  "features": {
    "immediate_margin_gain": 3,
    "lane_swing": "mid",
    "geometry_coverage_used": 0.25,
    "projected_tile_changes": 2,
    "projected_targets": 8
  },
  "confidence": {
    "kind": "engine_exact",
    "notes": "Derived from deterministic evaluation features; no lookahead."
  }
}
```

### Ordering rules

* `heuristic_tags`: sorted alphabetically (or stable deterministic insertion order—pick one and enforce consistently).
* `reasons`: sort by `(-weight, tag)`.

### Field rules

* If a feature isn’t available deterministically, omit the corresponding tag/reason/feature instead of guessing.
* Keep `reasons` short (one sentence max).

---

## 5. Tag taxonomy v0.1

Only include tags derivable from existing data.

### Tempo / lane

* `tempo_gain`
  Condition: `immediate_margin_gain > 0` (or sum of positive lane deltas > 0).
* `lane_swing_top` / `lane_swing_mid` / `lane_swing_bot`
  Condition: lane with max absolute delta (ties resolved deterministically by lane order TOP→MID→BOT).

### Geometry (descriptive only; no scoring changes)

* `geometry_efficient`
  Condition: `geometry_coverage_used >= GEOM_EFFICIENT_THRESHOLD` (default 0.60).
* `geometry_wasteful`
  Condition: `geometry_coverage_used <= GEOM_WASTEFUL_THRESHOLD` (default 0.25).

> v0.1 geometry coverage is a *descriptive proxy* derived from projection summary. It is **not** used to re-rank moves in this phase.

### Optional (only if cheap + already available)

* `tempo_denial`
  Condition: deterministic drop in opponent legal moves after the move (if already computed or trivially computed on a cloned state with existing legality checks). If not available, omit in v0.1.

---

## 6. Feature derivation rules

### 6.1 immediate_margin_gain

* From `lane_delta`:
  `immediate_margin_gain = max(|top|, |mid|, |bot|)` (or sum of positive deltas; choose one and document).
  Recommended: use **max absolute lane delta** for stable “swing” meaning.

Also store:

* `lane_swing`: the lane name (top/mid/bot) with the max absolute delta.

### 6.2 geometry_coverage_used

Goal: estimate how much of the card’s projection meaningfully “did something.”

Preferred derivation:

* If `projection_summary.tile_deltas` exists and you can also obtain the total projected target count:

  * `projected_tile_changes = len(tile_deltas)`
  * `projected_targets = <count of projected targets considered>`
  * `geometry_coverage_used = projected_tile_changes / max(1, projected_targets)`

Fallback if projected target count is not available:

* Set `projected_targets = None`
* Set `geometry_coverage_used = None`
* Skip geometry tags/reasons (do **not** invent coverage).

> If projected target count is not currently surfaced, you may add a small field to `projection_summary` to include it, as long as it’s deterministic and already computed.

---

## 7. Integration points

### Where to compute

* Add a helper (recommended): `qb_engine/explain.py`

  * `build_explain_payload(rec: dict) -> dict`
* Call it at the point recommendations are finalized, just before emission:

  * prediction / recommendation pipeline
  * and/or live session bridge where engine output is packaged

### Where to surface

* CLI `rec` output should include `explain`.
* JSONL snapshots should include `explain` inside each recommendation.
* Keep payload bounded (do not include full board states).

---

## 8. GPT-layer consumption requirements

In `coaching_mode=strategy`, GPT should:

* cite 1–2 top `reasons` for the top recommendation
* if `geometry_wasteful` tag exists, use phrasing:

  * “Engine-optimal but geometry-inefficient…”
* if `tempo_gain` exists:

  * mention immediate swing
* if future `tempo_denial` exists:

  * mention limiting opponent options

No prompt changes required in this phase, but this spec is designed to enable them immediately.

---

## 9. Tests

Add tests to ensure stability and prevent unintentional ranking changes.

### Unit tests

* `test_explain_block_present`
  Every recommendation includes `explain`, with `heuristic_tags` list and `reasons` list (may be empty if no features).
* `test_reason_order_deterministic`
  Confirm reasons sorted by `(-weight, tag)`.
* `test_lane_swing_tag`
  Given known lane deltas, confirm correct `lane_swing_*`.
* `test_geometry_tags_optional`
  If `projection_summary` lacks needed fields, ensure geometry tags are absent (no guessing).

### Regression guard

* `test_recommendation_order_unchanged` (if you have existing goldens)
  Confirm the list order and `move_strength` values match pre-H+ behavior.

---

## 10. Rollout plan

1. Implement `explain` payload (v0.1) + tests.
2. Run full suite.
3. IRL reliability testing (live coaching).
4. Record feedback:

   * are reasons interpretable?
   * are tags too noisy?
   * do we need a smaller tag set?

---

## 11. Future extensions (explicitly not in v0.1)

These are the next items from the session log, in recommended order:

1. **Strategic GPT phrasing templates** (consume tags consistently)
2. **Geometry preservation heuristic** (add scoring penalty/bonus term)
3. **Temporal discounting** (delayed value)
4. **1–2 ply effect lookahead** (expected future relevance)

---

## 12. Implementation checklist (for next chat + Codex)

* [ ] Locate recommendation emission point(s) and add `explain` block.
* [ ] Implement deterministic `build_explain_payload`.
* [ ] Add tests listed above.
* [ ] Ensure JSONL snapshots include `explain`.
* [ ] Verify recommendation ranking unchanged.
* [ ] Update docs (brief): where `explain` appears and how GPT should use it.

---

## 13. Files likely to change (guidance)

Actual paths may vary; confirm in repo:

* `qb_engine/prediction.py` or recommendation builder module
* `qb_engine/live_session.py` (if that’s where output is packaged/logged)
* `qb_engine/cli/qb_live_cli.py` (only if formatting needs update)
* `qb_engine/explain.py` (new helper)
* `qb_engine/tests/test_explain_payload.py` (new)
* docs: CLI/live coaching docs to mention `explain` payload (optional in H+)

---

## Appendix: “AI-ready kickoff prompt” for next chat instance

Paste this to start the next design/patch chat:

> You are entering Phase H+ Heuristic Transparency Layer v0.1.
> Do not change gameplay rules, scoring, legality, or recommendation ranking.
> Implement an `explain` payload for each recommendation with deterministic `heuristic_tags`, weighted `reasons`, and structured `features`, as specified in `Phase H+ Spec: Heuristic Transparency Layer v0.1`.
> Add tests ensuring determinism and no change in ranking.
> This is explanation-only: no lookahead, no temporal discounting, no geometry re-scoring in this phase.