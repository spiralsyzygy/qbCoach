# qbCoach GPT Layer — Design Overview (v0.1.0)

This document sketches the first-pass design for the **GPT layer** that sits on top of the deterministic qbCoach engine (Phases A–F).

It is intentionally high-level and will be split into more focused specs later (live coaching, self-play, enemy profiles, etc.).

---

## 1. Goals of the GPT Layer

The GPT layer is **not** another rules engine. It is:

* A **narrator and coordinator** around the deterministic engine.
* Responsible for:

  * Driving turn-by-turn interaction with the human player.
  * Passing structured state to the engine and interpreting the response.
  * Logging episodes for later analysis and training.
  * Eventually driving **both sides** in self-play / training mode.
* Never allowed to override or “correct” the deterministic engine’s rules, scoring, or legality.

---

## 2. Core Interfaces

### 2.1 Engine → GPT: CoachingRecommendation contract

The GPT layer receives structured output from Phase F:

* `CoachingRecommendation` → serialized to JSON-like form, including:

  * `position` summary (margins, lane status flags).
  * `moves` with per-move margins, ranks, labels, tags, and explanation_lines.
  * `top_n`, `primary_message`, `secondary_messages`.

The GPT must:

* Treat `quality_rank` / `quality_label` as authoritative.
* Base its language strictly on the numeric and structural data in the recommendation.
* Never invent rules or card text.

### 2.2 GPT → Engine: Turn inputs

For live play, the GPT provides to the engine:

* Initial deck list for YOU (or deck ID).
* Opponent identity (e.g. "Regina").
* On each turn:

  * YOUR move: "Play [card_id/name] at [lane, column]".
  * Enemy move: recorded from the user (live play) or decided by GPT (self-play).
  * The card YOU draw at the start of your turn (reported by user in live play).

The engine in turn updates:

* `GameState` (board, hands, decks).
* `EnemyObservation` (seen enemy cards, inferred deck for that opponent).
* Prediction and coaching outputs.

---

## 3. Live Coaching Protocol (Human vs AI)

This is the core user-facing loop for playing FF7R Queen's Blood with qbCoach as a live coach.

### 3.1 Session initialization

1. GPT asks:

   * Who is the opponent? (e.g. Regina)
   * What is your 15-card deck? (names or IDs, or a known deck preset).
2. Engine initializes:

   * Standard starting board:

     * YOU: Y1 tiles at lane TOP/MID/BOT, col 1.
     * ENEMY: E1 tiles at lane TOP/MID/BOT, col 5.
   * GameState with:

     * YOU and ENEMY decks built from DB.
     * 5-card opening hand for YOU.
     * 5-card opening hand for ENEMY.
   * EnemyObservation:

     * Empty at start (no enemy cards known yet).
   * Per-side turn counters:

     * `you_turns_taken = 0`, `enemy_turns_taken = 0`.

GPT then says:

> "Your opening hand is ready. Please tell me the 5 cards in your hand (names or IDs)."

User replies with their opening 5.

### 3.2 Mulligan phase (YOU)

1. GPT/engine calls a mulligan helper (or CoachingEngine in mulligan-mode) to:

   * Evaluate which opening cards are weak.
   * Suggest which cards to mulligan, if any.
2. GPT presents suggestions:

> "I recommend mulliganing [list] because [short reasons]. Which cards do you actually mulligan, and what replaces them?"

3. User responds:

> "I mulligan Wolf and Riot Trooper. I draw Archdragon and Grasslands Wolf."

4. Engine updates:

   * Returns those cards to deck, draws replacements, maintains YOU hand = 5.
   * Marks YOU mulligan done.

**Important rule:** The mulligan **replaces the first-turn draw**.

* On YOUR first turn (`you_turns_taken == 0`): **no draw** at start of turn.
* From second turn onward: draw 1 at start.

### 3.3 Mulligan phase (ENEMY)

* Engine performs a symmetric mulligan for ENEMY using a simple heuristic for now (e.g., "mulligan all cards with cost >= 4"), but via the same mulligan machinery as YOU.
* YOU do not see enemy hand; this is internal.
* ENEMY also:

  * Starts with 5 cards.
  * Does **not** draw at the start of its first turn.

This symmetry allows future GPT self-play to control ENEMY mulligans using the same strategy logic as YOUR side.

### 3.4 First turn (YOU)

Loop for YOUR first turn:

1. GPT shows:

   * Current board visualization.
   * YOUR current hand (5 cards after mulligan).
2. Engine calls `CoachingEngine.recommend_moves(state, enemy_obs, top_n=3)`.
3. GPT summarizes recommendation:

   * Best 1–3 moves (card + lane/column).
   * Expected margins and key tags (e.g. `wins_lane_1`, `improves_margin`).
4. GPT asks:

> "What do you actually play? (e.g. 'I play Archdragon at MID-2')."

5. User describes move.
6. Engine:

   * Applies YOUR move to GameState.
   * Logs:

     * The CoachingRecommendation.
     * The move chosen.
     * Whether the move followed the top recommendation.

### 3.5 Enemy turn (observed)

1. GPT asks:

> "What does the enemy do? (e.g. 'Enemy plays Crystalline Crab at BOT-1')."

2. User describes enemy play.
3. Engine:

   * Applies enemy move to GameState.
   * Updates EnemyObservation (adds seen card to enemy deck knowledge).
4. On enemy's first turn:

   * No draw at start.
5. On later enemy turns:

   * Engine draws 1 for ENEMY at start.

### 3.6 Next turns (YOU draws, plays, repeats)

For YOUR second and subsequent turns:

1. GPT asks:

> "What card did you draw at the start of your turn?"

2. User reports drawn card.
3. Engine updates YOUR hand and deck.
4. GPT shows updated board + hand.
5. Engine calls `CoachingEngine.recommend_moves` again.
6. GPT provides new recommendations and asks what you actually play.
7. Loop continues: player move → enemy move → new draw → new coaching.

At game end, engine logs:

* Final lane scores.
* Match winner and margin.
* Full episode history for future analysis/training.

---

## 4. Enemy Deck Memory and Profiles

To support stronger prediction and future self-play:

* Maintain an `enemy_profiles` store (e.g., JSON) keyed by:

  * Opponent name and difficulty (e.g., `"Regina_Normal"`).
* For each profile, track:

  * `known_cards`: set of card IDs observed in any past matches vs that opponent.
  * `inferred_deck`: optional 15-card deck once all cards are known.

Engine behavior:

* When facing a known opponent, Phase E deck inference uses `known_cards` as hard constraints.
* As new enemy cards appear in live matches, they are appended to the profile.
* Once 15 distinct cards are observed, treat the deck as known for future sessions.

---

## 5. Self-Play / Training Mode (Future)

In self-play mode, the GPT layer will:

* Drive BOTH sides (YOU and ENEMY) using the same coaching machinery:

  * Symmetric opening hands and mulligans.
  * Symmetric access to CoachingEngine for move selection.
* Record detailed logs of:

  * Recommendations vs actual moves.
  * Outcomes over many games.

The current design choices (symmetric mulligan logic, side-agnostic turn
counters, enemy profiles) are made to make this future mode easy to add
without changing the deterministic core.

---

## 6. Episode Logging (High-Level Sketch)

Each live or self-play game should be stored as an episode:

* `metadata`:

  * opponent name, difficulty
  * your deck list
  * timestamp, RNG seed if applicable
* `turns[]`:

  * pre-position summary (optional)
  * CoachingRecommendation JSON
  * your chosen move (and whether it matched the top recommendation)
  * enemy move (from observation or GPT)
  * card you drew
* `final_result`:

  * winner, final margin, lane breakdown

A more detailed logging spec can be broken out into a separate document.

---

This overview is a foundation. Next documents:

* **gpt_live_coaching_protocol.md** — detailed dialog & JSON examples.
* **gpt_self_play_training_spec.md** — how self-play is orchestrated.
* **enemy_profile_memory_spec.md** — structure and lifecycle of enemy profiles.