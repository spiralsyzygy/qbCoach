# Issue Log — Live Coaching & Engine Strategy Gaps

This log tracks observed mismatches between engine-level evaluation and optimal strategic play as identified during live coaching. Entries are descriptive and diagnostic, not criticisms of engine correctness.

---

## Issue 001 — Capparwire @ MID-2 Overvaluation vs Infrastructure Geometry

**Tag:** `engine_strategy`

**Context:**

* Live coaching session vs Regina
* Board state where Regina committed BOT as an effect infrastructure lane via Amphidex at BOT-4 and BOT-5
* Engine recommendation ranked **Capparwire @ MID-2** as best move (margin +5.0)

**Observed problem:**

* Capparwire’s effect geometry at MID-2 debuffs **TOP-2 and BOT-2 only**
* Regina’s BOT infrastructure historically:

  * clusters at columns 4–5
  * rarely projects meaningful value past column 3
* As a result, Capparwire @ MID-2:

  * does **not** meaningfully suppress Regina’s BOT engine
  * introduces self-inflicted debuffs on YOU lanes
  * does not directly disrupt MID payoff math

**Root cause (hypothesis):**

* Engine evaluation currently:

  * values immediate lane margin and static debuff effects
  * lacks modeling for *projection reach* and *future enemy payoff geometry*
  * does not yet simulate opponent follow-up plays or conversion patterns

**Impact:**

* Engine may overvalue symmetric or cross-lane debuffs in positions where:

  * opponent infrastructure is spatially isolated
  * future payoff does not interact with the affected tiles

**GPT-layer mitigation (current):**

* Override engine recommendation when:

  * effect geometry does not intersect opponent’s known conversion paths
  * opponent behavior strongly suggests future plays outside affected columns
* Favor plays that:

  * contest MID directly
  * delay or tax payoff timing
  * preserve interaction leverage (e.g., Grenadier timing)

**Status:** Open

---

*This issue should inform future engine strategy extensions, including geometry-aware evaluation and limited opponent-forward simulation.*

---

## Issue 002 — Conditional Interaction Without Guaranteed Geometry

**Tag:** `engine_strategy`

**Context:**

* Live session vs Regina
* Deck contained conditional interaction cards (e.g., Grenadier)
* Multiple turns elapsed where interaction was held but never became legally playable

**Observed problem:**

* The deck did not reliably generate **rank-2 pawn tiles** in relevant columns by Turn 3–4
* Interaction cards remained theoretical threats rather than practical tools
* Loss occurred despite correct timing instincts due to *geometry starvation*

**Root cause (hypothesis):**

* Deck construction emphasized interaction and denial without guaranteeing legality conditions
* Engine and GPT layers did not explicitly audit geometry sufficiency during deck validation

**Impact:**

* Correct strategic decisions (holding interaction) failed due to missing structural prerequisites
* Player forced into unlock or delay lines that ceded tempo

**Recommended mitigation:**

* Add a **geometry sufficiency check** during deck evaluation
* Treat lack of geometry as a deck-level flaw, not a sequencing mistake
* Bias GPT coaching toward earlier geometry acceleration when conditional interaction is present

**Status:** Open

---

## 11. Deck Construction Checklist — Geometry-First (Collection-Aware)

**Purpose:** Provide a lightweight, opponent-agnostic checklist for deck construction when card quality, rarity, or collection depth is limited.

This checklist is **mandatory guidance** for the GPT layer when evaluating or suggesting decks, and **advisory** for players.

### A. Geometry Production (Primary)

Before evaluating power, effects, or synergies, confirm:

* ☐ The deck contains **at least 3–5 cards** whose primary function is to *produce pawn geometry*.
* ☐ At least **2 cards** can reliably create a **rank-2 pawn tile** by **Turn 3** without opponent cooperation.
* ☐ Geometry producers are not all lane-locked (i.e., they can be used flexibly across TOP / MID / BOT).

*Examples of geometry roles (not card-specific):*

* forward projection shapes
* wide pawn grids
* overlapping pawn placement

---

### B. Conditional Interaction Support

For each **conditional interaction card** (e.g., requires legality, rank thresholds, or specific tile states):

* ☐ Identify **which geometry cards enable its legality**.
* ☐ Confirm legality can be achieved in **≤2 turns** in an average game.
* ☐ If legality requires multiple preparatory turns, **add geometry support or reduce conditional cards**.

> **Rule:** Conditional interaction without intentional geometry support is a deck construction error, not a play error.

---

### C. Geometry vs Effects Priority

When collection depth is limited:

* ☐ Prefer **geometry-producing cards** over pure effect or modifier cards.
* ☐ Treat geometry-neutral effect cards as *context-sensitive*, not auto-includes.
* ☐ Avoid decks where core interaction relies on opponent mistakes to become legal.

---

### D. Live Play Heuristic (Derived)

If holding a conditional interaction card during live play:

* One of the next **two turns** must explicitly advance its legality, **or**
* The interaction should be deprioritized or converted into a tempo play.

Failure to do so indicates strategic drift.

---

### E. Collection-Aware Framing (Meta Rule)

When card pool quality is low:

> **Geometry creates legality → legality creates interaction → interaction creates wins.**

This principle supersedes raw power evaluation and should guide both deck construction and in-game coaching.

---

*This checklist was derived from live-session analysis and is intended to reduce losses caused by invisible geometry constraints rather than misplays.*

---

## 11. Strategy Principles (Anchored Summary for GPT & Engine Layers)

The following principles are distilled from external strategy guidance and reconciled with live-session learnings. They are intended to shape **GPT-layer coaching** immediately and inform **engine heuristics** over time.

### A. Pawn Ranks as the Primary Economy

* Treat pawn ranks / owned tiles as the game’s core economic resource ("location-specific mana").
* Early game should bias toward **positive pawn delta** (create more future legal placements than you consume).
* Avoid building **high-rank empty tiles** that can be flipped and used against you.

### B. Tempo as Action Availability

* Define tempo primarily as **valid-move availability**, not speed or raw points.
* High leverage states are those that reduce the opponent’s **legal move search space** (cutoffs, lane starvation).

### C. Lane Resolution Is Binary

* Losing a lane by 1 is the same as losing by 20; this enables:

  * **sacrifice/abandon** decisions
  * **bait lanes** to induce enemy overcommit
  * **tie-forcing** as a viable defensive goal in a lane you cannot win outright

### D. Center and Frontier Concepts

* The center lane often has outsized influence because placements there can impact adjacent lanes.
* Practical guideline: prioritize contesting the **frontier/neutral zone** (where lanes meet) rather than only backline comfort tiles.

### E. Pawn Safety and Flip Threat (Micro Lookahead)

* Penalize (in coaching language and future engine heuristics) plays that create pawns the opponent can immediately flip back.
* Prefer placements that either:

  * claim tiles out of immediate counter-projection reach, or
  * create a counter-flip line that you control.

### F. Passing as End-State Acceptance

* Reinforces prior patch: passing is a commitment to the current lane resolution.
* Passing is strategically strongest when it **converts move denial** (opponent has no meaningful legal moves) into game end.

---

## 12. GPT-Layer Implementation Notes (How to Apply These)

### A. Legal-Move Anchoring (Mandatory)

* The GPT layer must only recommend plays that are present in the CLI/engine’s **legal move set** for the current state.
* If GPT proposes a geometry line that is not legal, it must immediately pivot to a legal proxy line.

### B. When to Prefer Interaction Over Margin

* If the opponent is end-state favored, prioritize lines that:

  * reduce their future conversion space,
  * force earlier commitments,
  * or increase interaction/variance,
    even when the short-term margin is lower.

### C. Geometry + Conditional Interaction Coupling

* Reinforces the deck checklist: if holding a conditional interaction piece, one of the next two turns should advance its legality.

---

*These sections are designed to be used as inputs for a future turn-by-turn checklist and engine heuristic roadmap.*

---

## 11. Strategy Principles (Anchored Summary for GPT & Engine Layers)

The following principles are distilled from external strategy guidance and reconciled with live-session learnings. They are intended to shape **GPT-layer coaching** immediately and inform **engine heuristics** over time.

### A. Pawn Ranks as the Primary Economy

* Treat pawn ranks / owned tiles as the game’s core economic resource ("location-specific mana").
* Early game should bias toward **positive pawn delta** (create more future legal placements than you consume).
* Avoid building **high-rank empty tiles** that can be flipped and used against you.

### B. Tempo as Action Availability

* Define tempo primarily as **valid-move availability**, not speed or raw points.
* High leverage states are those that reduce the opponent’s **legal move search space** (cutoffs, lane starvation).

### C. Lane Resolution Is Binary

* Losing a lane by 1 is the same as losing by 20; this enables:

  * **sacrifice/abandon** decisions
  * **bait lanes** to induce enemy overcommit
  * **tie-forcing** as a viable defensive goal in a lane you cannot win outright

### D. Center and Frontier Concepts

* The center lane often has outsized influence because placements there can impact adjacent lanes.
* Practical guideline: prioritize contesting the **frontier/neutral zone** (where lanes meet) rather than only backline comfort tiles.

### E. Pawn Safety and Flip Threat (Micro Lookahead)

* Penalize (in coaching language and future engine heuristics) plays that create pawns the opponent can immediately flip back.
* Prefer placements that either:

  * claim tiles out of immediate counter-projection reach, or
  * create a counter-flip line that you control.

### F. Passing as End-State Acceptance

* Reinforces prior patch: passing is a commitment to the current lane resolution.
* Passing is strategically strongest when it **converts move denial** (opponent has no meaningful legal moves) into game end.

---

## 12. GPT-Layer Implementation Notes (How to Apply These)

### A. Legal-Move Anchoring (Mandatory)

* The GPT layer must only recommend plays that are present in the CLI/engine’s **legal move set** for the current state.
* If GPT proposes a geometry line that is not legal, it must immediately pivot to a legal proxy line.

### B. When to Prefer Interaction Over Margin

* If the opponent is end-state favored, prioritize lines that:

  * reduce their future conversion space,
  * force earlier commitments,
  * or increase interaction/variance,
    even when the short-term margin is lower.

### C. Geometry + Conditional Interaction Coupling

* Reinforces the deck checklist: if holding a conditional interaction piece, one of the next two turns should advance its legality.

---

*These sections are designed to be used as inputs for a future turn-by-turn checklist and engine heuristic roadmap.*
