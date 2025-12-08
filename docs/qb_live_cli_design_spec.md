# qb_live_cli & EngineBridge — Phase G / Track A.5 Design Spec (v1.1)

**Scope:**  
This document specifies a **live-coaching–ready module + CLI** that:

- Boots the deterministic qbCoach engine
- Sets `session_mode="live_coaching"`
- Accepts **deck input**, **enemy plays**, and **your draws/moves**
- Produces **Track A.5–compatible text blocks** for qb_uxGPT
- Logs every turn as structured JSON for later analysis

It is designed to:

- Work immediately in a **manual “engine-in-the-loop” mode** (Track A.5)
- Transition cleanly to **API/tool-based integration** later
- Never duplicate any rules or mechanics already implemented in the engine


---

## 0. Goals & Non-Goals

### 0.1 Goals

- Provide a **single human-facing entrypoint** (`qb_live_cli`) that:
  - Initializes a live-coaching session with `session_mode="live_coaching"`
  - Accepts **deck information**:
    - By `deck_tag` (predefined config), or
    - By explicit **15-card deck list** (card IDs and/or names)
  - Steps through a full IRL game via simple commands
  - Emits **copy-pasteable A.5 state blocks**:

    - `[SESSION]`
    - `[BOARD]`
    - `[YOU_HAND]`
    - `[ENGINE_OUTPUT]`

  - Logs each turn to a JSONL file for offline analysis and qb_uxGPT training/evaluation

### 0.2 Non-Goals

- No HTTP server or OpenAI integration in this module
- No GUI; this is a text-only CLI
- No internal reimplementation of rules, scoring, effects, or legality
- No self-play UX in v1.1 (only `live_coaching` mode is required here)


---

## 1. High-Level Architecture

We introduce two new components:

- `qb_engine/live_session.py`  
  - Core **session + EngineBridge** module
- `qb_engine/cli/qb_live_cli.py`  
  - CLI wrapper that uses `LiveSessionEngineBridge`

### 1.1 Existing Core Types (Reused)

The bridge wraps the existing deterministic engine:

- `GameState` — global game state (board, hands, decks, scores, side_to_act, etc.)
- `BoardState` — 3×5 tile representation
- `EnemyObservation` — enemy plays + inferred deck info
- `PredictionEngine` — threat map, expected margin
- `CoachingEngine` — move ranking / recommendations

The new EngineBridge provides a **narrow, opinionated API** used by:

- The CLI (in Track A.5)
- Future API/tools (HTTP server, custom GPT tools layer)


---

## 2. EngineBridge API (Python-Level Contract)

The bridge is a thin orchestration wrapper around the engine.

**Module:** `qb_engine/live_session.py`  
**Class:** `LiveSessionEngineBridge`

```python
class LiveSessionEngineBridge:
    def __init__(self, session_mode: str = "live_coaching"):
        ...

    def init_match(
        self,
        you_deck_ids: list[str] | None = None,
        enemy_deck_tag: str | None = None,
    ) -> None:
        """
        Initialize GameState, PredictionEngine, CoachingEngine, EnemyObservation, etc.
        session_mode MUST be persisted and returned via get_state().
        """

    def get_state(self) -> dict:
        """
        Return a serializable snapshot with fields suitable for CLI + logging:
        {
          "session": {...},
          "board": {...},
          "you_hand": [...],
          "enemy_known_cards": [...],
          "scores": {...},
          ...
        }
        """

    def sync_you_hand_from_ids(self, card_ids: list[str]) -> None:
        """Authoritative overwrite of YOU's hand (live_coaching)."""

    def register_enemy_play(self, card_id: str, row: int, col: int) -> None:
        """Mirror the enemy's real-world play onto the engine board."""

    def apply_you_move(self, card_id: str, row: int, col: int) -> dict:
        """
        Apply YOU's move, advance the game state, and return an updated snapshot.
        Illegal moves must NOT mutate state; see error handling.
        """

    def recommend_moves(self, top_n: int = 3) -> list[dict]:
        """
        Return CoachingEngine's top move candidates, including margins and lane breakdown.
        """

    def get_prediction(self) -> dict:
        """
        Return PredictionEngine threat map & expected margin for the current state.
        """
````

### 2.1 Card Resolution: Names and IDs

To support both card IDs and card names at the CLI level, the bridge module should provide a helper:

```python
def resolve_card_id(self, identifier: str) -> str:
    """
    Accept either:
      - a card_id string (e.g. "020"), or
      - a case-insensitive card name (e.g. "levrikon"/"Levrikon").

    Returns the canonical card_id string.

    Raises a clear error if the identifier does not match any known card or is ambiguous.
    """
```

* This helper uses the **canonical JSON DB** (e.g. `QB_DB_Complete_v2.json`) under the hood.
* It is used by CLI commands to normalize identifier input into `card_id` strings before calling engine methods.

---

## 3. A.5 Output Contract (Text + JSON)

The EngineBridge + CLI must produce two synchronized representations:

1. A **human-readable A.5 text block** for qb_uxGPT.
2. A **machine-readable `TurnSnapshot` dict** for logging and future APIs.

### 3.1 A.5 Text Block

For each turn where YOU are to act, the CLI should be able to print:

```text
[SESSION]
mode: live_coaching
session_id: 2025-12-07T20:15:03Z-001
turn: 3
side_to_act: YOU
enemy_deck_tag: RedXIII_Rematch

[BOARD]
      1        2        3        4        5
Top  [Y1]    [Y1]    [Y1:Wolf] [N0]    [O1]
Mid  [Y1]    [Y3]    [Y1]     [N0]    [O1]
Bot  [Y1]    [Y1]    [Y1]     [N0]    [O1]

[YOU_HAND]
card_ids: [008, 019, 020, 025, 053]

[ENGINE_OUTPUT]
recommend_moves:
- 1) Levrikon (020) @ Mid-4 | margin +6
- 2) Crawler  (008) @ Top-3 | margin +3
- 3) Wolf     (019) @ Mid-2 | margin +1

prediction:
- expected_final_margin_best_line: +6
- lane_summary:
  TOP: Y+3
  MID: Y+2
  BOT: E+1
```

### 3.2 TurnSnapshot Dict

The same information should exist as a structured Python dict:

```python
TurnSnapshot = dict[str, Any]

snapshot: TurnSnapshot = {
  "session": {
    "mode": "live_coaching",
    "session_id": "2025-12-07T20:15:03Z-001",
    "turn": 3,
    "side_to_act": "YOU",
    "enemy_deck_tag": "RedXIII_Rematch",
  },
  "board": {
    # engine's canonical board representation
  },
  "you_hand": ["008", "019", "020", "025", "053"],
  "engine_output": {
    "recommend_moves": [
      {
        "card_id": "020",
        "card_name": "Levrikon",
        "target": {"row": 1, "col": 4},
        "margin": 6,
        "lane_breakdown": {
          "top": 3,
          "mid": 2,
          "bot": -1
        },
        "notes": "primary lane consolidation"
      },
      ...
    ],
    "prediction": {
      "expected_final_margin_best_line": 6,
      "lane_summary": {
        "top": 3,
        "mid": 2,
        "bot": -1
      },
      "raw_threat_map": {...}  # optional, may be omitted from CLI view
    }
  },
  "chosen_move": null  # filled in after YOU plays
}
```

### 3.3 Shared Formatting Function

Add a helper to `live_session.py` (or a small utility module):

```python
def format_turn_snapshot_for_ux(snapshot: TurnSnapshot) -> str:
    """
    Render the `[SESSION]`, `[BOARD]`, `[YOU_HAND]`, `[ENGINE_OUTPUT]` block
    from the snapshot.

    This is the single source of truth for A.5 text formatting.
    Both CLI and future HTTP APIs should use this helper for consistency.
    """
```

The CLI calls this to print the block that you paste into qb_uxGPT.

---

## 4. CLI UX Design

**Module:** `qb_engine/cli/qb_live_cli.py`
**Entrypoint:**

```bash
python -m qb_engine.cli.qb_live_cli
# or installed script:
qb_live_cli
```

### 4.1 Startup & Match Initialization

On launch:

1. Print a header:

   ```text
   qb_live_cli — Phase G / Track A.5 Live Coaching
   ```

2. Prompt to start a new session:

   ```text
   Start new live coaching session? [y/N]
   ```

3. If yes, collect:

   * Optional **enemy deck tag** (e.g. `RedXIII_Rematch`), or leave blank.
   * **Your deck selection**, with two options:

     **4.1.1 Deck Selection**

     * Prompt:

       ```text
       Provide your deck:
         (a) deck tag
         (b) explicit 15-card list
       Choice [a/b]:
       ```

     * If user chooses **a)**:

       * Prompt:

         ```text
         Enter your deck tag (or leave blank for none):
         ```

       * CLI passes `you_deck_ids=None`, `you_deck_tag` to some deck-profile loader **if implemented** or simply ignores it for v1.1 (deck tags are optional and may be a no-op initially).

     * If user chooses **b)**:

       * Prompt:

         ```text
         Enter your 15-card deck as IDs and/or names, separated by commas.
         Example:
           003, 005, Levrikon, "Grasslands Wolf", 018, ...
         Deck:
         ```

       * CLI splits the input, normalizes tokens, and for each **identifier**:

         * Calls `bridge.resolve_card_id(identifier)`

           * Accepts either card_id (e.g. `"020"`) or name (case-insensitive, stripped quotes).
           * On error (unknown or ambiguous), prints a clear message and re-prompts.

       * Once 15 valid card IDs are collected, the CLI passes `you_deck_ids=list_of_15_ids` into `init_match`.

4. Call:

   ```python
   bridge = LiveSessionEngineBridge(session_mode="live_coaching")
   bridge.init_match(you_deck_ids=..., enemy_deck_tag=...)
   ```

5. After init, immediately display a concise summary (optional) and proceed to **opening hand sync**.

### 4.2 Opening Hand Sync (Turn 0)

The engine may or may not track a canonical opening draw; for v1.1 we assume the **user is authoritative** for their starting hand.

* Prompt:

  ```text
  Enter your opening hand (IDs and/or names, space-separated):
    e.g. 003 005 Levrikon "Grasslands Wolf" 021
  HAND:
  ```

* Resolve all identifiers via `resolve_card_id`.

* Call `bridge.sync_you_hand_from_ids(card_ids)`.

* Optionally call `bridge.get_state()` then format & display a `TURN 0 (PRE-MULLIGAN)` A.5 block.

If user mulligans:

* Ask them to enter their **post-mulligan hand** the same way.
* Call `sync_you_hand_from_ids` again.

---

### 4.3 Turn Loop Commands

Once Turn 1 begins, show a simple command menu:

```text
Commands:
  draw <ids/names...>           sync your current hand after drawing
  enemy <id/name> <row> <col>   register enemy play
  rec                           compute recommendations + prediction, print A.5 block
  play <id/name> <row> <col>    apply your move, advance turn
  state                         show board & your hand
  log                           print the current session log path
  help                          show this menu again
  quit                          end session
```

#### Command Semantics

* **`draw`**

  * Example:

    ```text
    draw 003 Levrikon "Grasslands Wolf" 021
    ```

  * Resolve all identifiers via `resolve_card_id` and call `sync_you_hand_from_ids`.

* **`enemy`**

  * Example:

    ```text
    enemy Levrikon top 4
    enemy 020 mid 3
    ```

  * Resolve card identifier.

  * Accept `row` as:

    * `top` / `mid` / `bot` or `t`/`m`/`b` (case-insensitive)

  * Accept `col` as integer `1..5`.

  * Normalize to internal engine coordinate system and call `register_enemy_play`.

* **`rec`**

  * Calls `bridge.recommend_moves(top_n=3)` and `bridge.get_prediction()`, then `bridge.get_state()`.
  * Builds a `TurnSnapshot`.
  * Appends it to in-memory and log file.
  * Calls `format_turn_snapshot_for_ux(snapshot)` to print the A.5 block.

* **`play`**

  * Example:

    ```text
    play Levrikon mid 4
    play 020 top 3
    ```

  * Resolve the card identifier.

  * Normalize row/col.

  * Call `apply_you_move`.

  * If legal, update state, append a `TurnSnapshot` with `chosen_move`.

  * If illegal, print engine-provided error and do not mutate state.

* **`state`**

  * Calls `get_state()` and prints a human-friendly board + hand summary.
  * May reuse the `[BOARD]` part of `format_turn_snapshot_for_ux`.

* **`log`**

  * Prints full path to current session’s JSONL log file.

* **`help`**

  * Reprints the command menu.

* **`quit`**

  * Ends the loop, closes the log file.

---

## 5. Logging & Reporting

For each turn, the CLI must produce a `TurnSnapshot` and append it to a JSONL log file.

### 5.1 File Layout

* Directory: `logs/live/` (configurable via env or CLI flag)
* Naming pattern:
  `YYYYMMDD_HHMMSS_live_<optional_enemy_deck_tag>.jsonl`

Example:

```text
logs/live/20251207_201503_live_RedXIII_Rematch.jsonl
```

### 5.2 JSONL Schema (Per Line)

Each line contains a full `TurnSnapshot`:

```json
{
  "session_id": "2025-12-07T20:15:03Z-001",
  "mode": "live_coaching",
  "turn": 3,
  "side_to_act": "YOU",
  "enemy_deck_tag": "RedXIII_Rematch",
  "board": { ... },
  "you_hand": ["008", "019", "020", "025", "053"],
  "engine_output": {
    "recommend_moves": [ ... ],
    "prediction": { ... }
  },
  "chosen_move": {
    "card_id": "020",
    "row": 1,
    "col": 4
  }
}
```

* For turns where no recommendation was requested yet, `engine_output` may be empty or partial.
* For pre-mulligan or mulligan turns, `chosen_move` may be `null`.

These logs serve as the **ground truth** event stream and can be cross-referenced with qb_uxGPT transcripts.

---

## 6. Error Handling & Guardrails

### 6.1 Card Resolution Errors

If `resolve_card_id(identifier)` fails:

* Print:

  ```text
  Error: Unknown or ambiguous card identifier "X".
  Please check the spelling or use a card ID.
  ```

* Do not call any engine method.

* Re-prompt the user for a valid command.

### 6.2 Illegal Moves

If `apply_you_move` reports the move as illegal:

* Print:

  ```text
  Illegal move: <reason from engine>
  ```

* Do **not** mutate `GameState`.

* Do **not** increment the turn counter.

* Allow the user to re-issue `play` or call `rec` again.

### 6.3 Coordinate Validation

* Valid rows (user input): `top`, `mid`, `bot`, `t`, `m`, `b` (case-insensitive).
* Valid columns: integers `1..5`.
* Any invalid input yields:

  ```text
  Error: Invalid row/col. Use top/mid/bot and 1-5.
  ```

### 6.4 Desync Recovery

If the engine returns unexpected data (e.g., unknown `side_to_act`, mismatched board dimensions):

* CLI should:

  * Print the raw `get_state()` snapshot for debugging.

  * Warn the user that the session may be corrupted:

    ```text
    Warning: Engine returned unexpected state. You may want to end this session and start a new one.
    ```

  * Do not attempt automatic repair.

---

## 7. Extensibility & Future Work

This design is intentionally modular:

* **Self-play & analysis modes**

  * `LiveSessionEngineBridge` already takes `session_mode`.
  * CLI can later expose `--mode self_play` or `--mode analysis`.
  * Additional commands/personas can be layered without changing the bridge.

* **HTTP / Tool Layer**

  * `TurnSnapshot` and `format_turn_snapshot_for_ux` are suitable for:

    * REST responses
    * OpenAI Tools / Actions
    * Web dashboards

* **Deck Profiles**

  * Future work can implement named deck tags that expand to canonical 15-card lists:

    * e.g. `you_deck_tag="Aggro_Wolf"`.
  * The CLI’s “deck tag or 15-card list” choice will remain valid.

* **Reporting**

  * Additional scripts can consume JSONL logs to:

    * Summarize match statistics
    * Train new heuristics
    * Evaluate qb_uxGPT behavior

---

## 8. Implementation Notes for Codex

When handing this to Codex (or another coding LLM), emphasize:

1. **Do not re-implement rules or scoring** — always call into existing engine modules.
2. **Centralize card resolution** (`resolve_card_id`) against the canonical DB.
3. **Centralize A.5 formatting** (`format_turn_snapshot_for_ux`) so both CLI and future APIs match qb_uxGPT expectations.
4. **Keep CLI logic thin and imperative** — no clever abstractions required; clarity > brevity.

This spec should be sufficient to implement:

* `qb_engine/live_session.py`
* `qb_engine/cli/qb_live_cli.py`
* Supporting utilities (card resolution, snapshot formatting, logging helpers)

ready for integration with **qb_uxGPT v1.0 (Track A.5)**.