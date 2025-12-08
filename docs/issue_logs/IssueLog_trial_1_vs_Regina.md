# ========================================

# ✅ **GitHub Issue Bundle for qbCoach / Phase G / qb_engine**

# ========================================

Below are **9 GitHub issues**, each fully structured.

---

# ----------------------------------------

# **ISSUE 1 — Strategic Discussion Blocked in Live Coaching**

# ----------------------------------------

### **Title:** Phase G GPT Layer Cannot Provide Strategy While Staying Engine-Strict

### **Description**

In `live_coaching` mode, the UX GPT Layer cannot provide strategic commentary because Phase G rules require it to rely strictly on ENGINE_OUTPUT. This prohibits any high-level explanation, matchup guidance, or non-mechanical reasoning even though this is explicitly intended for the coaching UX layer.

### **Repro Steps**

1. Start `qb_live_cli`.
2. Provide deck + initial hand.
3. Ask GPT layer for strategy explanations.
4. GPT must decline, per Phase G restrictions.

### **Expected Behavior**

* GPT should be able to provide high-level, non-mechanical strategic advice separate from engine-strict calculations.

### **Actual Behavior**

* GPT must reject all strategy discussion because ENGINE_OUTPUT does not contain strategy metadata.

### **Spec Citations**

* **gpt_layer_design_overview.md**: GPT layer is responsible for *coaching, interpretation, and UX*.
* **coaching_design_spec.md**: Strategy is conceptual, **not tied** to engine legality or projections.

### **Proposed Fix**

* Introduce **dual-mode** responses within live_coaching:

  * **Strict Mode:** engine-interpreting
  * **Strategy Mode:** high-level coaching that does not attempt to compute mechanics

---

# ----------------------------------------

# **ISSUE 2 — `recommend_moves` Incorrectly Used as Legality Source**

# ----------------------------------------

### **Title:** CLI Validates Legal Moves Against `recommend_moves` Instead of Full Legal Move Generator

### **Description**

`recommend_moves` is a *subset* of legal moves, but the CLI prevents playing any move not in `recommend_moves`.

### **Repro Steps**

1. Load any state where a card can legally be played on multiple tiles.
2. Run `rec`.
3. Attempt to `play` a legal move that is not listed in `recommend_moves`.
4. CLI rejects it.

### **Expected**

* `play <card> <lane> <col>` should validate against **all** legal moves from `MoveGenerator`.

### **Actual**

* CLI only allows moves present in `recommend_moves`.

### **Spec Citations**

* **qb_uxGPT-Engine_interaction_contract.md**: GPT may choose *any legal move* provided by the engine.
* **coaching_design_spec.md**: `recommend_moves ⊆ legal_moves`, NOT vice versa.

### **Proposed Fix**

* Add `LegalMoves()` output to ENGINE_OUTPUT or expose via CLI.
* Validate `play` commands against **all legal moves**.

### **Impact**

* Currently makes qbCoach nonfunctional in real matches.

---

# ----------------------------------------

# **ISSUE 3 — Draw Phase Missing in Turn Flow**

# ----------------------------------------

### **Title:** Live-coaching CLI Does Not Prompt for Player’s Top-of-Turn Draw After Enemy Play

### **Description**

In `live_coaching` mode, the turn sequence should be:

1. Player plays a card (or passes).
2. Enemy play is registered (`enemy <id/name> <row> <col>`).
3. Board state is updated; **enemy turn ends**.
4. **Player’s new turn begins**, and the engine/CLI should prompt the user to provide the card they drew at the top of their turn.
5. After the user inputs the drawn card (by name or ID), the engine updates `YOU_HAND`.
6. Only then should `rec` be called to generate meaningful recommendations for that turn.

Currently, the CLI does **not** explicitly prompt for the player’s draw at the correct time, nor does it structure the loop to enforce that order. The user has to manually remember to call `draw <id>` and can also call `rec` before syncing the draw, which produces misleading or incomplete recommendations.

### **Repro Steps**

1. Start `qb_live_cli` and initialize a `live_coaching` session.
2. Provide a valid 15-card deck and sync your opening hand via `draw …`.
3. Play a move with `play <id> <row> <col>`.
4. Register an enemy move with `enemy <id> <row> <col>`.

   * At this point, the enemy turn is conceptually over; your new turn is starting.
5. Observe that:

   * The CLI does **not** prompt: “What card did you draw? Please enter `draw <id/name>`”.
   * You can immediately call `rec` without having synced your draw.
6. Call `rec`.

   * Recommendations are generated without knowledge of your new top-of-turn card, causing `YOU_HAND` and recommendations to be incorrect/underspecified.

### **Expected Behavior**

After an enemy play is registered and the board is updated:

1. The enemy turn should end; the player’s turn should begin.

2. The CLI should **explicitly prompt the user** for their top-of-turn draw, for example:

   ```text
   Enemy play registered.
   Your turn begins.
   Please enter the card you drew: draw <id/name>
   ```

3. Only after `draw <id/name>` is received and the engine has updated `YOU_HAND` should the CLI allow `rec` to be called and considered valid for that turn.

4. `rec` should assume the draw is already synced; recommendations should always reflect the **correct, current hand**.

### **Actual Behavior**

* After `enemy <id> <row> <col>`, the CLI:

  * Does not indicate a new turn has started.
  * Does not prompt for a draw.
  * Allows `rec` to be called immediately with stale or incomplete hand state.
* As a result:

  * GPT/live-coaching must “remember” to ask the user for their draw out-of-band.
  * It’s easy to generate ENGINE_OUTPUT that does not include the newly drawn card.
  * The coaching loop becomes fragile and error-prone.

### **Spec Citations**

* **qb_rules_v2.2.4.md** — Turn Flow & Draw Rules:

  * On each of the player’s turns (except their first), they draw 1 card at the start of the turn.
* **qb_uxGPT-Engine_interaction_contract_v1.0.md**:

  * The GPT layer expects the engine/CLI to provide a deterministic turn structure so that `BOARD + YOU_HAND + ENGINE_OUTPUT` are always coherent for each turn snapshot.
* **gpt_live_coaching_protocol_v0.2.md**:

  * Track A.5 assumes a consistent sequence: state sync → draw (if applicable) → recommendation → decision → action.

### **Proposed Fix**

* Update `qb_live_cli` turn choreography so that:

  1. After `enemy <id> <row> <col>`:

     * Mark enemy turn as finished.
     * Mark that it is now “YOU to act”.

  2. Immediately prompt the user:

     ```text
     Enemy play registered.
     Your turn begins.
     Please sync your top-of-turn draw:
       draw <id/name>
     ```

  3. Internally, disallow `rec` until a `draw` (or an explicit “no draw this turn” case, e.g. first turn) has been processed for the new turn.

  4. After `draw` is processed, allow `rec` and guarantee that:

     * `YOU_HAND` in the `[YOU_HAND]` section of the snapshot includes the new card.
     * Recommendations are based on the correct hand.

* Optionally, log turn boundaries in `[SESSION]`:

  * Increment `turn` and keep `side_to_act: Y` consistent with the beginning of each player turn.

---

# ----------------------------------------

# **ISSUE 4 — `draw` Command Overwrites Hand Instead of Appending**

# ----------------------------------------

### **Title:** `draw <id>` Replaces `YOU_HAND` Completely

### **Description**

Calling `draw` wipes all previous cards and sets the hand to `[id]`.

### **Repro Steps**

1. Start a session with a hand of 5 cards.
2. Call `draw 007`.
3. Observe `YOU_HAND` becomes `[007]`.

### **Expected**

* Append to hand list.
* Preserve existing hand.

### **Actual**

* Overwrites entire hand.

### **Spec Citations**

* **qb_rules_v2.2.4.md**: Hand is cumulative.
* **qb_engine_test_playbook.md**: Multiple draw events maintain hand size.

### **Proposed Fix**

Implement `append_to_hand(id)` not `replace_hand([id])`.

### **Severity:** **Critical**

Breaks game logic, prevents correct play.

---

# ----------------------------------------

# **ISSUE 5 — `[SESSION] turn` and `side_to_act` Never Update**

# ----------------------------------------

### **Title:** Turn Number and Side-to-Act are Static in Live Coaching

### **Repro Steps**

1. Start live session.
2. Play several turns.
3. Observe `[SESSION] turn` stays `1`.

### **Expected**

* Turn increments each cycle.
* side_to_act toggles: `Y → E → Y → …`.

### **Actual**

* Always `turn: 1`, `side_to_act: Y`.

### **Spec Citation**

* **qb_engine_v2.1.0.md**: Session metadata must reflect true turn count.

### **Proposed Fix**

* Update session metadata after every play.

---

# ----------------------------------------

# **ISSUE 6 — No Full-Hand Sync Command**

# ----------------------------------------

### **Title:** Impossible to Correct Hand Desync Without Restarting Session

### **Description**

No command exists to reset the hand or resync all cards.

### **Expected**

* Something like:

  ```
  sync_hand 005 007 019 015 018
  ```

### **Actual**

* Only `draw` or `play` exist.

### **Proposed Fix**

Add explicit CLI support for:

```
set_hand <ids...>
```

---

# ----------------------------------------

# **ISSUE 7 — CLI Allows Enemy Move Out of Sequence**

# ----------------------------------------

### **Title:** `enemy` Command Accepted Even Before Player Move Completes

### **Repro Steps**

1. Call `enemy <id> <lane> <col>` before resolving player move.
2. CLI accepts it.

### **Expected**

* Reject enemy play until player move is registered.

### **Actual**

* CLI accepts enemy play anytime.

### **Fix**

* Enforce strict turn constraints in CLI.

---

# ----------------------------------------

# **ISSUE 8 — Lack of Turn-Boundary Events**

# ----------------------------------------

### **Title:** No Indication of Turn End / Turn Start in CLI

### **Expected**

* CLI should show:

  ```
  YOUR TURN BEGINS
  ENEMY TURN BEGINS
  ```

### **Actual**

* No boundaries → GPT must infer timeline.

---

# ----------------------------------------

# **ISSUE 9 — Visualization Ambiguity (No Distinction Between Projected Ranks and Placed Ranks)**

# ----------------------------------------

### **Description**

Board ranks shown in `[Y2]` / `[N0]` format do not distinguish between:

* projected ranks
* effect-modified ranks
* base tile rank

This complicates debugging.

### **Proposed Fix**

* Add formatting:

  ```
  [Y2(p)] = projected
  [Y2(e)] = effect-modified
  ```

---

# ====================================

# **Architecture Diagrams for Fix Path**

# ====================================

Below are ASCII-form diagrams you can paste into GitHub issues or documentation.

---

## **1. Turn Loop Architecture (Correct Version)**

```
+-------------------+
|   Start Turn      |
+---------+---------+
          |
          v
+-------------------+
|   DRAW event      |
|  (engine emits)   |
+---------+---------+
          |
          v
+-------------------+
|  rec (engine →    |
|  legal_moves,      |
|  recommend_moves,  |
|  prediction)       |
+---------+---------+
          |
          v
+-------------------+
| GPT interprets    |
| engine output     |
+---------+---------+
          |
          v
+-------------------+
|    play command   |
+---------+---------+
          |
          v
+-------------------+
| enemy command     |
+-------------------+
```

---

## **2. Correct Data Flow for Legal Moves**

```
MoveGenerator (true legality)
           |
           v
  +-------------------------+
  |   LegalMoves (ALL)     |
  +-------------------------+
           |
           +------> CoachingEngine (ranking)
                           |
                           v
                 recommend_moves (subset)
```

**CLI must validate `play` against LegalMoves, not recommend_moves.**

---

## **3. Hand State Architecture (Fix)**

```
   +---------------+
   | current_hand  |
   +-------+-------+
           ^
           |
    append_to_hand()
           |
   +-------+--------+
   |   draw(id)     |
   +----------------+
```

Not:

```
current_hand = [id]
```

---