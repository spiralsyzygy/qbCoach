## Phase H+ Mini-Spec: Heuristic Tags + Explanation Payload

### Purpose

Improve GPT-layer coaching clarity without changing game rules or compromising determinism by surfacing **why** a recommendation ranks well, not just that it does.

### Non-goals

* No new evaluation logic (yet).
* No lookahead, temporal discounting, or geometry modeling changes in this patch.
* No scoring/legality changes.

---

## Output Contract Changes

### Engine recommendation object: add `explain` block

Add a new field to each recommendation (or whatever your engine currently returns in the recommendations list):

```json
{
  "card_id": "020",
  "card_name": "Archdragon",
  "row": "mid",
  "col": 2,
  "move_strength": 0.876,
  "lane_delta": { "top": 0, "mid": 3, "bot": 0 },
  "projection_summary": { "...": "..." },

  "explain": {
    "heuristic_tags": [
      "tempo_gain",
      "lane_swing_mid",
      "denies_anchor"
    ],
    "reasons": [
      { "tag": "lane_swing_mid", "text": "+3 projected mid lane margin", "weight": 0.35 },
      { "tag": "tempo_gain", "text": "Immediate board control gain this turn", "weight": 0.25 },
      { "tag": "denies_anchor", "text": "Reduces enemy legal high-leverage placements next turn", "weight": 0.15 }
    ],
    "features": {
      "immediate_margin_gain": 3,
      "enemy_legal_moves_delta": -2,
      "geometry_coverage_used": 0.67,
      "anchor_value": "medium"
    },
    "confidence": {
      "kind": "engine_exact",
      "notes": "Derived from deterministic evaluation features; no lookahead."
    }
  }
}
```

#### Notes

* `heuristic_tags` is compact: GPT uses it for phrasing.
* `reasons` are human-readable one-liners + numeric weights (optional but strongly recommended).
* `features` are structured, machine-readable numbers for later improvements.
* `confidence.kind` is one of: `engine_exact`, `heuristic_inferred` (if you have to infer some tags), `unknown`.

### Determinism requirement

* Tags and reasons must be derived from deterministic features already computed.
* Ordering must be deterministic:

  * Sort `reasons` by descending `weight`, then by `tag` name as tie-break.
  * Sort `heuristic_tags` alphabetically (or stable insertion order derived deterministically).

---

## Tag Taxonomy v0.1

Implement only tags you can justify from existing evaluation outputs. Start small:

### Tempo / margin

* `tempo_gain` — positive immediate margin gain (any lane)
* `tempo_denial` — reduces opponent’s immediate potential (e.g., reduces their legal moves / reduces their projected best reply margin if you already compute that)
* `lane_swing_top|mid|bot` — largest lane delta is in that lane

### Geometry (no new scoring yet; just descriptive tags)

* `geometry_efficient` — high projection coverage used (if computable from projection_summary)
* `geometry_wasteful` — low coverage (pattern projects mostly off-board or onto already-owned/occupied tiles)
* `consumes_anchor` — move occupies a tile you classify as “anchor-like” (center columns etc.) using a simple static map
* `preserves_optionality` — non-committal placement (if you already compute something like “remaining legal moves”; otherwise skip for now)

### Risk/variance (descriptive only)

* `low_variance` — if your evaluation already has low sensitivity / robust advantage metric; otherwise skip
* `high_ceiling` — only if you already have a feature for potential upside (not recommended in v0.1 unless already present)

**If a tag would require inventing new evaluation, don’t include it yet.** This patch is “explain what we already compute.”

---

## Minimal Feature Extraction

Use already-available fields:

* `lane_delta` → immediate_margin_gain and lane_swing tag
* `projection_summary.tile_deltas` → coverage estimate (count of projected targets that change owner/rank / total projected)
* legality module (optional): compute `enemy_legal_moves_delta` by counting legal moves pre/post on cloned state (if you already do this anywhere; otherwise defer)
* simple static anchor map:

  * columns 2–3 (0-index 1–3?) or your chosen definition; keep deterministic and documented

---

## GPT Layer Usage (requirements)

Update GPT coaching templates to:

* Mention 1–2 top `reasons` verbatim-ish (paraphrase allowed)
* If tags include `geometry_wasteful`, label as: “Engine-optimal but geometry-inefficient”
* If `tempo_denial`, say: “This also limits their next-turn options.”

No change to recommendation ranking required for this patch.

---

## Test Plan

### Unit tests

1. `test_explain_block_present`

* For a known board + hand state, assert every recommendation includes `explain.heuristic_tags` and `explain.reasons`.

2. `test_reason_order_deterministic`

* Ensure reasons are sorted by `weight` then tag name.

3. `test_tag_derivation_lane_swing`

* Given `lane_delta` with max in mid, assert `lane_swing_mid` in tags.

4. `test_geometry_coverage_estimate_stable`

* For a known card projection summary, compute coverage and assert it matches expected (or at least stable under repeated runs).

### Golden snapshot test (optional)

* If you have JSON snapshot fixtures, assert a recommendation’s explain payload matches a golden JSON fragment.

---

# Codex Implementation Prompt

> **Task**
>
> Implement “Heuristic Tags + Explanation Payload” (v0.1) in the deterministic engine output, without changing recommendation ranking logic.
>
> **Scope**
>
> * Add `explain` block to each recommendation object returned by the engine / live session bridge.
> * Implement deterministic tag derivation and reason generation using existing evaluation fields (`lane_delta`, `projection_summary`, any existing features you already compute).
> * Add tests as described below.
>
> **Constraints**
>
> * No rules changes, no scoring changes, no lookahead.
> * Deterministic ordering for tags and reasons.
> * Keep diff minimal; do not refactor the evaluation pipeline unless necessary.
>
> ---
>
> ## 1) Locate recommendation schema + emission point
>
> Find where the engine constructs the recommendation objects (likely in prediction/recommendation module or live_session bridge formatting). Add:
>
> * `explain.heuristic_tags: list[str]`
> * `explain.reasons: list[{"tag": str, "text": str, "weight": float}]`
> * `explain.features: dict[str, object]` (start with `immediate_margin_gain`, `enemy_legal_moves_delta` if easy, `geometry_coverage_used`)
> * `explain.confidence: {"kind": "engine_exact", "notes": str}`
>
> Ensure this is included in JSON output and snapshots.
>
> ---
>
> ## 2) Implement tag derivation (v0.1)
>
> Create a helper, e.g. `qb_engine/explain.py` or local helper in the recommendation module:
>
> ```py
> def build_explain_payload(rec: dict) -> dict:
>     ...
> ```
>
> Derive:
>
> * `lane_swing_*` based on max absolute value in `lane_delta`
> * `tempo_gain` if sum of positive lane_delta > 0 (or immediate_margin_gain > 0)
> * `geometry_coverage_used`:
>
>   * if `projection_summary.tile_deltas` exists: coverage = len(tile_deltas) / max(1, projected_target_count)
>   * if projected_target_count not available, use len(tile_deltas) as a proxy and document it
> * `geometry_efficient` if coverage >= threshold (pick a constant like 0.6)
> * `geometry_wasteful` if coverage <= threshold (like 0.25)
>
> Generate `reasons` with weights:
>
> * lane swing reason: weight 0.35
> * tempo gain reason: weight 0.25
> * geometry reason: weight 0.15
>   Sort reasons deterministically by (-weight, tag).
>   Sort heuristic_tags deterministically (alphabetical).
>
> If a required source field is missing, omit the tag/reason rather than guessing.
>
> ---
>
> ## 3) Logging / snapshot inclusion
>
> Ensure the `explain` block is included wherever recommendations appear in:
>
> * CLI `rec` output JSON
> * JSONL snapshot logs
>
> Keep payload small (avoid dumping full board diffs).
>
> ---
>
> ## 4) Tests
>
> Add `qb_engine/tests/test_explain_payload.py` (or similar) with:
>
> 1. `test_explain_block_present`
> 2. `test_reason_order_deterministic`
> 3. `test_tag_derivation_lane_swing`
> 4. `test_geometry_coverage_estimate_stable`
>
> Use a small deterministic board state and a fixed card set from the existing DB/hydrator.
>
> ---
>
> **Acceptance criteria**
>
> * All recommendations include a stable `explain` payload.
> * No change to move ranking (move_strength order unchanged in existing tests).
> * All tests pass.
> * Output stays deterministic across runs.