Next in your log, now that correctness + CLI flow + safety valve are handled, is **Category 4: Engine capability gaps (NOT bugs)** — but we should tackle it in a very specific order so we don’t muddy determinism or re-open correctness issues.

### 1) Heuristic transparency for GPT layer

This is the highest ROI “gap” because it improves coaching quality **without changing move selection logic**.

What to do next:

* Add lightweight `heuristic_tags` (strings) to each recommendation:

  * `tempo_gain`, `tempo_denial`, `geometry_sacrifice`, `geometry_preserve`, `delayed_value_tradeoff`, `low_variance`, `high_ceiling`
* Expose *why* a move scored well (not just the score): e.g. “lane_delta +3 mid”, “denies enemy legal anchors”, “consumes central anchor”.

Why this first:

* Zero risk to correctness.
* Makes strategic mode explanations dramatically better.
* Lets you audit the engine’s “personality” before adding deeper modeling.

### 2) Strategic mode awareness improvements (GPT layer behavior)

Once tags exist, update GPT-layer phrasing patterns:

* “Engine-optimal but geometry-inefficient”
* “Low-variance line vs higher-ceiling alternative”
* “Timing-sensitive effect: strong later if delayed”

This is mostly prompt/spec work and keeps engine deterministic.

### 3) Geometry preservation heuristics

Then add a *small* penalty/bonus term that measures “geometry entropy”:

* reward preserving central anchors and multi-directional projection potential
* penalize early plays that waste pattern coverage

Do this before deeper lookahead because it’s cheap and interpretable.

### 4) Delayed value modeling (temporal discounting)

Introduce a simple “value curve”:

* discount immediate margin slightly when a card is tagged as “high-ceiling later”
* incorporate opportunity cost for committing scarce anchors early

Keep it shallow (no plies yet).

### 5) Limited-depth effect lookahead (1–2 plies)

Last, because it’s the most complex and easiest to get wrong:

* simulate opponent replies for a small subset of high-impact effects
* compute expected future relevance rather than immediate effect resolution

This should come after we’ve improved transparency and heuristics so we can validate behavior changes.