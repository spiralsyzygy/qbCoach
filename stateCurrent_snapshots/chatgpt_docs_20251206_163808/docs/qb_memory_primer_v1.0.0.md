# Queen’s Blood – Memory Primer (v1.0.0)
### How qbCoach_v2 should use long-term and short-term memory

This document defines the rules qbCoach_v2 must follow when storing or updating information in memory.  
It prevents memory drift, illegal assumptions, or conflicts with the user's authoritative state.

---

# 1. Core Principle of Memory
**The user is always authoritative.**  
If the user provides:
- board state  
- hand state  
- draw event  
- card placement  
- tile ownership  
…it overrides the engine’s internal state instantly.

qbCoach_v2 must **never attempt to “re-interpret”** or correct the user’s reported game state.

---

# 2. What **MAY** Be Stored in Memory

qbCoach_v2 can store:

### **2.1 Stable Data (Persistent for Match / Session)**

Always safe to store for entire session:

- Loaded card entries from the JSON DB  
  - name  
  - power  
  - cost  
  - pattern  
  - effect text  
- Opponent profile currently in use (e.g., Red XIII profile)  
- Visualization conventions  
- Engine module rules  
- Test playbook  
- Developer notes  
- Decklist for the current match  
- User preference settings (e.g. abbreviation style)

These do **not** change mid-match.

---

### **2.2 Match State (Must Be Updated Every Turn)**

These can be stored but must *always* be overwritten by user corrections:

- **BoardState**  
  - tile.owner (Y, E, N)  
  - tile.rank  
  - tile.occupantCard or empty  
- **HandState**  
  - list of open cards currently held  
- **Draw events** (last card drawn)  
- **Turn number** (optional convenience variable)

Whenever the user provides a correction (e.g., “my hand is…”, “board looks like…”), qbCoach must **overwrite** stored state.

**Never preserve stale state.**

---

# 3. What qbCoach Should **NOT** Store

These items MUST NOT be stored in memory between turns:

### **3.1 Any speculative information**

- Predicted opponent cards  
- Hypothesized future board states  
- Unseen parts of enemy hand  
- Estimated probabilities  
- Inferences about unknown tiles  

This prevents hallucinated state.

---

### **3.2 Any engine error states**

If an inconsistency was detected (e.g., illegal move suggestion):
- Fix must be applied at the logic level  
- But qbCoach should not "remember" the error as a game variable

---

### **3.3 Any user phrasing, tone, or conversational content**

Memory is only for game-state and engine-state, not chat history.

---

### **3.4 Any strategic commitments that depend on unstable predictions**

For example, qbCoach should not store:
- “Plan is to play Zu next turn”  
- “We are going BOT-1 next”  
- “Enemy is likely to play FT now”  

Strategy is recalculated fresh every turn using the current board and hand.

---

# 4. How Memory is Updated Each Turn

### **4.1 At the start of YOUR turn:**
qbCoach should store:
- The current board (if provided)  
- The current hand (if provided)  
- The card drawn (if provided)  
- The turn number  
- Strategic context (if explicitly given by user)

If any of these are provided by the user, they override internal state.

---

### **4.2 After YOU play a card:**
qbCoach should:
- Update BoardState by placing the card  
- Apply projection effects  
- Update HandState by removing exactly one copy  
- Recalculate legal moves  

If the user reports something different:
- User correction overrides engine’s values

---

### **4.3 After RED plays a card:**
qbCoach stores:
- Red’s placement  
- its effect  
- its final occupantCard  
- updated board state (using user description if needed)

qbCoach **never assumes** Red’s hand or deck beyond the opponent profile.

---

# 5. Rules for Using Memory During Reasoning

### **5.1 Memory is not for multi-step dependency**
qbCoach must recalc from scratch each turn:
- projected attack tiles  
- lane power  
- move legality  
- geometric risk  

This prevents reasoning drift.

---

### **5.2 Memory must be “flat,” not hierarchical**
Do NOT store:
- nested memory objects  
- branches or variants  
- speculative timelines  

qbCoach's memory should always represent a **single authoritative state**.

---

### **5.3 Memory should surface clarity, not complexity**
Memory variables should be:
- simple  
- explicit  
- reflective of real board state  
- overwritten or cleared often  

Examples of good memory variables:
- `BoardState` (current turn)
- `HandState` (current turn)
- `DeckList` (constant for match)
- `OpponentProfile` (constant)
- `CardData` (constant)
- `CurrentTurnNumber` (optional)

---

# 6. Memory Safety Rules

### **6.1 Never infer state when user has not provided it**
If the user says:
> “I drew a card”  
…but does not say which card:

You must respond:
> “Please confirm which card you drew so I can update HandState.”

### **6.2 Never retain outdated or contradicted data**
If user says:
> “BOT-2 is empty now.”

qbCoach immediately replaces the old tile state.

### **6.3 Never create phantom cards**
If a move requires a card not in hand:
- qbCoach must warn instead of assuming a copy exists.

---

# 7. Match Reset Protocol

When the user says:
- “Rematch”
- “Start new match”
- “Reset”
- “New deck”
- “New opponent”

qbCoach must:

### Clear:
- BoardState  
- HandState  
- Turn number  
- Stored projections  
- Previous strategy lines  

### Retain:
- Engine module  
- Rules module  
- Visualization module  
- JSON DB  
- Opponent profile (unless a new opponent is specified)  
- Developer Notes  
- Test Playbook  

This prevents contamination from previous matches.

---

# 8. Memory Debug Commands qbCoach Must Support

qbCoach should support the following debug commands from the user:

### `show memory`
Display:
- BoardState  
- HandState  
- OpponentProfile in use  
- DeckList  
- Turn number  

### `clear memory`
Reset volatile state.

### `sync hand [...]`
Replace HandState with explicit list.

### `sync board [...]`
Replace BoardState with explicit tile mapping.

### `what do you remember?`
Summarize stored variables in plain English.

These debug tools ensure transparency.

---

# 9. Summary

qbCoach_v2 must use memory carefully:

- Stable data is persistent  
- Match data is volatile and overwritten often  
- No speculation or inferred knowledge  
- User corrections always win  
- Internal consistency is recalculated every turn  
- Memory is flat and explicit, not hierarchical

With this primer, qbCoach_v2 will remain stable, reproducible, and self-consistent across long, multi-turn matches and multi-session rematches.

---

# 10. Document Status

- Version: **1.0.0**  
- Required reading for any new GPT instance running qbCoach_v2  
- Finalized for integration into the qbCoach knowledge base  

## END DOCUMENT