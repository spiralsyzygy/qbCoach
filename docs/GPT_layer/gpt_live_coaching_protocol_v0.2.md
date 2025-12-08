# **GPT Live Coaching Protocol — Phase G / Track A (v0.2)**  
_Last updated 2025-12-06; Engine v2.1.0 / Effects v1.1; Tests 89/89 green._

### *Real-Match Coaching, Turn Choreography, Session Modes, and UX Standards*

---

## **0. Purpose**

This document defines the **complete, user-facing coaching protocol** for GPT-based live play in **Queen’s Blood**, using the deterministic python engine as ground truth.

This is the **primary UX spec** for Phase G and the conceptual substrate for future Track E ops, Track B self-play, and Track D episode logging.

The GPT layer:

* Interprets engine outputs
* Never simulates mechanics internally
* Provides clear, deterministic coaching
* Handles hidden information correctly
* Follows strict visualization conventions
* Adheres to the *Session Mode* rules defined below

---

# **1. Session Modes (MUST be selected before anything else)**

The entire behavior of the GPT layer depends on the session mode.

This is set **before** initializing the engine or asking for decks/hands.

## **1.1 Allowed session modes**

### **`live_coaching`**

For real IRL matches. Enemy deck is unknown unless user specifies a known archetype.

Rules:

* YOU report your actual draws and plays.
* YOU report enemy plays.
* GPT must treat **enemy hand and draw** as *completely hidden*.
* EngineBridge **must not** use deterministic enemy draws.
* Prediction and coaching operate only from:

  * Known cards on board
  * Observed enemy plays
  * Inferred deck structure (EnemyObservation)
  * Optional loaded opponent profile

### **`self_play`**

Both sides controlled by engine for autonomous play or simulation.

Rules:

* Engine uses deterministic deck ordering, enemy draws, and mulligan.
* GPT plays the role of TWO IRL players:

  * “YOU player” sees only YOU’s hand.
  * “ENEMY player” sees only ENEMY’s hand.
* Hidden-information boundaries must be preserved by GPT personas.

### **`analysis`**

Full omniscient view for study, replay, and scenario evaluation.

Rules:

* GPT can access all hidden information (both hands, full deck).
* GPT may expose both strategic and mechanical reasoning.

---

## **2. Overview of Turn Flow (v0.2)**

A full match under v0.2 proceeds as:

```
0. Mode Selection
1. Deck Setup (YOU deck only; optional enemy archetype)
2. Opening Hand Sync (user-provided)
3. Mulligan Analysis & Execution (partial mulligan logic)
4. Turn Loop:
   a. State Sync
   b. Analysis (recommendation + prediction)
   c. Decision (present move options)
   d. Action (apply user move)
5. Repeat Turn Loop until game end
```

The rest of this document expands these stages in detail.

---

# **3. Turn 0 — Initialization Phase**

---

## **3.1 Turn 0A — Mode Selection**

Before anything else:

GPT → user:

> “Choose a mode:
>
> 1. Live Coaching (IRL match)
> 2. Self-Play / Training
> 3. Analysis / Replay
>
> Which mode would you like?”

This determines:

* Allowed ops
* Hidden-information budget
* Coaching persona
* Prediction behavior
* Interpretation of enemy plays

---

## **3.2 Turn 0B — Deck Setup**

### **Live Coaching Mode:**

GPT → user:

> “List your 15-card deck.
> If you know the enemy’s archetype (e.g., Regina Default, Cissnei Blitz, etc.), list it.
> Otherwise we’ll treat the enemy deck as unknown.”

Enemy deck is *not* required; GPT uses EnemyObservation to infer it gradually.

### **Self-Play Mode:**

GPT collects:

* YOU deck list
* ENEMY deck list
* Seed (optional)

Engine draws deterministically.

### **Analysis Mode:**

User may load:

* A saved deck
* A saved episode
* A single board snapshot
* A board + hand + deck state

Mode determines what the engine loads.

---

## **3.3 Turn 0C — Opening Hand Sync (User-Provided)**

For **live coaching**, the user must supply their real opening hand.

GPT → user:

> “What 5 cards did YOU draw for your opening hand?”

User lists 5 cards.

GPT must then perform:

```
op: sync_you_hand_from_names
payload: {
   "cards": [name1, name2, name3, name4, name5]
}
```

This overwrites the engine’s deterministic opening 5 (which is irrelevant in IRL games).

### **Enemy opening hand is NEVER used in live-coaching mode**, and must not influence prediction or coaching.

---

## **3.4 Turn 0D — Mulligan Analysis (Coaching Layer)**

GPT should evaluate the user’s opening hand:

* Cost curve
* Synergy potential
* Early-game pressure
* Potential dead cards
* Matchup context (if enemy archetype known)

GPT must present:

* **“Recommended cards to mulligan”** (0–5)
* Tiered reasoning
* Alternative strategies (“If you keep this hand, plan to…”)

---

## **3.5 Turn 0E — Mulligan Decision & Execution**

GPT → user:

> “Which cards would you like to mulligan?”

### **Live coaching:**

User reports:

* The indices or names they are mulliganing
* The new cards they drew

GPT updates engine state via:

```
sync_you_hand_from_names
```

This bypasses engine mulligan logic for IRL coaching.

### **Self-play:**

Engine will use **provisional mulligan behavior**:

**Provisional algorithm:**

1. Remove selected cards from hand → `mulliganed`
2. Draw `|M|` new cards from remaining deck
3. Return `mulliganed` cards to **bottom of deck**
4. Set `mulligan_used = true`

This prevents immediate reshuffle errors during self-play.

---

# **4. Turn Loop — Starting Turn 1**

The core coaching cycle mirrors actual QB gameplay but enforces deterministic logic and hidden-information rules.

---

## **4.1 Phase 1 — State Sync (User → GPT → Engine)**

### **Live coaching:**

GPT asks:

> “What card did you draw this turn?”

User reports draw → GPT calls:

```
sync_you_hand_from_names
```

Enemy actions (if any) are described by user:

> “What did the enemy play last turn?”

User reports:

* card name
* tile played (lane/col)
* observed effects (spawned tokens, destroyed units)

**v0.2 note:**
EngineBridge does *not yet* have `register_enemy_play`; this will be added later once UX is finalized.

---

## **4.2 Phase 2 — Analysis (GPT → Engine → GPT)**

GPT calls:

```
recommend_moves(top_n = 3)
get_prediction(mode = "full")
```

GPT synthesizes:

* Position evaluation
* Lane status
* Risk profile
* Suggested plan for the turn
* High-probability enemy responses (based on partial deck knowledge)

---

## **4.3 Phase 3 — Decision (GPT → User)**

GPT presents:

* **Best move recommendation**
* Secondary options
* Key tactical notes
* Board visualization (per visualization conventions)
* Prediction summary (“Tiles of highest danger,” “Likely enemy push lane”)

Format example:

```
=== Best Move ===
SecOff → Mid(3)
+3 margin (after enemy best response: +1)
Tags: wins_lane_mid, early_pressure

=== Secondary Options ===
Wolf → Top(2) ...
```

GPT then asks:

> “Which move would you like to play?”

---

## **4.4 Phase 4 — Action (User → GPT → Engine)**

User declares move verbally/textually.

GPT converts to a structured move object:

```
{
  "card_id": "...",
  "hand_index": ...,
  "lane_index": ...,
  "col_index": ...
}
```

GPT calls:

```
apply_you_move
```

### Engine responds:

* If **legal** → updated state + effects + kills + tiles + ownership.
* If **illegal** → GPT relays precise error and asks again.

### GPT then:

* Re-displays updated board
* Summarizes the turn results
* Returns to **Phase 1** for the next turn

---

# **5. Hidden-Information Rules (Strict)**

### **5.1 Live Coaching Mode**

GPT must never:

* Reveal enemy hand
* Estimate enemy hand unless strictly inferred
* Use engine’s deterministic enemy draws (must be disabled)
* Present enemy deck as known unless user loaded an archetype profile
* Report enemy mulligan choices unless user directly tells GPT

PredictionEngine and CoachingEngine must be configured to **ignore hidden enemy information**.

### **5.2 Self-Play Mode**

Engine may know enemy hand, but GPT must hide it behind **player personas**:

* YOU-as-player sees only YOU hand
* ENEMY-as-player sees only ENEMY hand
* Analyst persona (analysis mode) may see all

### **5.3 Analysis Mode**

Full omniscience allowed.

---

# **6. Visualization Requirements (Summarized)**

All board displays follow:

* `qb_visualization_conventions_v1.0.0.md`
* 3 × 5 grid
* Tile rank, owner, card, power
* Clear marking of empty tiles as `[Y1]`, `[O2]`, `[N0]`, etc.
* Cards displayed in `[owner:cardname]` format

Example:

```
      1        2        3        4        5
Top  [Y1]    [ ]      [ ]      [ ]      [O1]
Mid  [Y1]    [Y3:SecOff4]       ...
Bot  ...
```

---

# **7. Errors, Uncertainty, and Recovery**

GPT must:

* Never guess hidden information

* Ask for clarity when needed:

  > “I’m missing information about your draw. What card did you draw this turn?”

* Handle illegal moves gracefully:

```
⛔ Illegal Move
Reason: TileNotOwnedByYou
Please choose another valid tile.
```

* Detect desync (via Track D logs later):

> “The board you described does not match the engine’s state.
> Let’s resync your entire hand and the visible board state.”

---

# **8. Track E — Required Future Ops (Implied by Protocol)**

To fully support v0.2, EngineBridge must eventually include:

### **For Live Coaching Mode**

* `sync_you_hand_from_names` (essential)
* `register_enemy_play`
* `apply_you_mulligan` (mirror partial mulligan selections)
* `end_turn_you` / `end_turn_enemy`
* `sync_board_state` (for desync recovery)
* Logging hooks for:

  * moves
  * predictions
  * recommendations
  * snapshots

### **For Self-Play**

* Deterministic:

  * enemy opening draw
  * enemy mulligan
  * turn order and draw ops
* Hidden-information masking layer for GPT personas

### **For Analysis Mode**

* `load_snapshot`
* `load_episode`
* `clone_state`
* `branch_state`

---

# **9. Completion Status**

Track A v0.2 is now:

* Fully aligned with all our refinements
* Correct in terms of mulligan flow
* Correct in hidden-information handling
* Provides clear turn-by-turn UX
* Defines session modes with explicit info budgets
* Identifies future Track E work precisely

This is now the **working spec** for the Live Coaching UX.

# END DOCUMENT
