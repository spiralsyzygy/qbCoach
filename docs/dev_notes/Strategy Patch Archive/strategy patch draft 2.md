# qb_uxGPT Strategy Patch — Perplexity Principles Insert

*This insert is intended to be merged into the main Strategy Patch/Addendum during the next consolidation pass.*

---

## Strategy Principles (Anchored Summary for GPT & Engine Layers)

The following principles are distilled from the Perplexity summaries you provided and reconciled with our live-session learnings. They are intended to shape **GPT-layer coaching** immediately and inform **engine heuristics** over time.

### 1) Pawn Ranks as the Primary Economy

* Treat pawn ranks / owned tiles as the game’s core economic resource ("location-specific mana").
* Early game should bias toward **positive pawn delta** (create more future legal placements than you consume).
* Avoid building **high-rank empty tiles** that can be flipped and used against you.

### 2) Tempo as Action Availability

* Define tempo primarily as **valid-move availability**, not speed or raw points.
* High leverage states are those that reduce the opponent’s **legal move search space** (cutoffs, lane starvation).

### 3) Lane Resolution Is Binary

* Losing a lane by 1 is the same as losing by 20; this enables:

  * **sacrifice/abandon** decisions
  * **bait lanes** to induce enemy overcommit
  * **tie-forcing** as a viable defensive goal in a lane you cannot win outright

### 4) Center and Frontier Concepts

* The center lane often has outsized influence because placements there can impact adjacent lanes.
* Practical guideline: prioritize contesting the **frontier/neutral zone** (where lanes meet) rather than only backline comfort tiles.

### 5) Pawn Safety and Flip Threat (Micro Lookahead)

* Penalize (in coaching language and future engine heuristics) plays that create pawns the opponent can immediately flip back.
* Prefer placements that either:

  * claim tiles out of immediate counter-projection reach, or
  * create a counter-flip line that you control.

### 6) Passing as End-State Acceptance

* Reinforces prior patch: passing is a commitment to the current lane resolution.
* Passing is strategically strongest when it **converts move denial** (opponent has no meaningful legal moves) into game end.

---

## GPT-Layer Implementation Notes (How to Apply These)

### A) Legal-Move Anchoring (Mandatory)

* The GPT layer must only recommend plays that are present in the CLI/engine’s **legal move set** for the current state.
* If GPT proposes a geometry line that is not legal, it must immediately pivot to a legal proxy line.

### B) When to Prefer Interaction Over Margin

* If the opponent is end-state favored, prioritize lines that:

  * reduce their future conversion space,
  * force earlier commitments,
  * or increase interaction/variance,
    even when the short-term margin is lower.

### C) Geometry + Conditional Interaction Coupling

* If holding a conditional interaction piece, one of the next two turns should advance its legality.

---

## Engine Heuristic Roadmap Hooks (Non-binding)

These are suggested future engine-facing metrics implied by the principles above:

* `legal_move_differential` (my legal moves − opponent legal moves)
* `pawn_delta` / `pawn_wealth` (growth vs consumption)
* `pawn_flip_threat` (1-ply safety penalty)
* `lane_lock_detect` (opponent legal moves in lane == 0)
* `frontier_pressure` (projection into neutral/frontier tiles)

*End goal: unify engine evaluation + GPT coaching around legality, geometry, and action availability—not just static point margin.*

---

## Consolidation Notice — Strategy Patch Single Source of Truth

As of this session, **all strategy principles, deck-construction rules, and GPT-layer implementation notes are consolidated into this document**.

* The temporary document titled **“qb_uxGPT Strategy Patch — Perplexity Principles Insert”** is now **deprecated** and should be treated as merged.
* All Perplexity-derived principles (pawn economy, geometry, tempo as action availability, lane resolution, legality anchoring) are considered **active and authoritative here**.

**Operational rule going forward:**

* Maintain **one Strategy Patch document** (this file)
* Maintain **one Issue Log document** for live findings and engine/GPT gaps

This keeps strategy doctrine stable while allowing the Issue Log to evolve independently during live testing.

---

*Next planned refinement:* split this Strategy Patch into explicit subsections for **Deck Construction Rules**, **In-Game Turn Checklist**, and **Post-Match Review Heuristics** once Deck v2 testing against Regina is complete.



=======
=======
=======

# qb_uxGPT Strategy Patch — Addendum

*Session-derived strategic constraints and coaching rules, generalized beyond a single opponent. Intended to augment (not replace) the existing qb_uxGPT strategy patch.*

---

## 1. Passing Is a Commitment, Not a Neutral Action (Global Rule)

**Rule:** Passing must be treated as an *affirmative strategic commitment* to the current end-state, never as a default or low-risk option.

**Implications for GPT coaching:**

* `pass` must not be framed as *safe*, *defensive*, or *tempo-neutral*.
* Any recommendation to pass must be accompanied by an explicit statement of the end-state outcome (winning / losing / unclear).
* If the end-state favors the opponent, passing should be described as *locking in a loss* unless new interaction is impossible.

This rule applies regardless of opponent and corrects a common heuristic error where passing is treated as variance-reducing or risk-averse.

---

## 2. Negative Margins Require Variance, Not Stasis

**Rule:** When engine outputs show that all available moves have negative margins, the default strategic response is to **increase interaction**, not reduce it.

**Correct interpretation:**

* Negative margins indicate the *equilibrium favors the opponent*.
* Passing or stalling preserves that equilibrium.
* The only rational response is to seek *forced interaction, disruption, or variance*, even if the short-term evaluation worsens.

**Coaching adjustment:**

* GPT should explicitly state when the engine believes the current equilibrium is losing.
* GPT should frame suboptimal moves as *attempts to break equilibrium*, not mistakes.

---

## 3. Infrastructure vs. Interaction (Deck-Agnostic Principle)

Not all strong decks are beaten the same way.

**Key distinction:**

* *Infrastructure decks* gain value from time, board freeze, and effect accumulation.
* *Interaction decks* gain value from forcing responses and repeated recalculation.

**Coaching rule:**

* If the opponent benefits from delayed resolution, GPT should bias toward:

  * earlier contest
  * board disruption
  * denying clean payoff turns
* GPT should avoid recommending strategies that mirror the opponent’s strength axis unless explicitly justified by engine output.

This principle applies broadly, not just to Regina-style opponents.

---

## 4. Lane Denial Is a Pressure Tool, Not a Win Condition

**Rule:** Lane denial (e.g., MID denial) should be coached as *pressure creation*, not as an all-in objective.

**Clarification:**

* The goal of lane denial is to make the opponent’s preferred conversion lane *expensive, unstable, or awkward*.
* Overcommitting to a single lane can create secondary free lanes or infrastructure zones.

**Coaching guidance:**

* Encourage *minimum viable contest* rather than absolute control.
* Emphasize disruption of payoff timing over raw lane ownership.

---

## 5. Crowded Boards Favor Effect Resolution — Treat With Caution

**Observation:** Dense, crowded board states amplify the impact of effects and end-of-game resolution math.

**Rule:** GPT should not assume that creating crowded lanes is inherently advantageous.

**Coaching implications:**

* When both players benefit from crowding, assess *who benefits more at resolution*.
* If the opponent has superior end-state scaling, GPT should warn that crowding increases opponent leverage.

This counters the common but incomplete heuristic that “crowded lanes favor swing cards.”

---

## 6. Card Advantage vs. Action Density

**Rule:** In late or losing positions, *action density* is often more valuable than raw card advantage.

**Guidance:**

* Cards that generate value over time (draw, buffs, delayed payoff) should be deprioritized when the opponent benefits from stasis.
* GPT should recognize when card advantage incentives subtly encourage incorrect play patterns (e.g., passing to realize value).

---

## 7. Coaching Language Corrections (UX-Level Fix)

GPT must avoid language that implies:

* passing is inherently safe
* delayed payoff is always desirable
* negative engine margins imply no meaningful decisions remain

Preferred framing:

> “This move worsens the immediate evaluation, but it forces interaction and avoids accepting a losing end-state.”

This framing helps users internalize correct strategic lessons even in losing positions.

---

## 8. Meta-Lesson (Generalized)

> **The goal is not to maximize value in the abstract, but to deny the opponent the game state they want.**

Strategic coaching should prioritize *state denial* over *value accumulation* when those goals diverge.

---

*This addendum should be treated as a live-evolving strategy layer, updated as new opponent profiles and failure modes are identified.*

---

## 9. Future Expansion Notes (Intentional, Not Yet Implemented)

This document is an **intermediate strategy patch**, not the final form.

Planned future refinements include:

* **Turn-by-turn mental checklist**

  * A concise sequence the GPT must implicitly run each turn (e.g., end-state check → equilibrium check → interaction vs stasis decision).

* **Structural separation of strategy layers**

  * Clear division between:

    * *Deck construction principles* (pre-game)
    * *In-game coaching rules* (turn-by-turn decisions)

* **Annotated post-match examples**

  * Concrete snapshots from completed matches showing:

    * correct vs incorrect pass recommendations
    * negative-margin positions handled well vs poorly
    * lane-denial applied minimally vs overcommitted

These are intentionally deferred until sufficient live-play data is collected.

The current patch should be read as a **foundation and constraint set**, not a finished coaching doctrine.
