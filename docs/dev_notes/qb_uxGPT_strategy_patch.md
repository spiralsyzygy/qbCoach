
# 2️⃣ **AI-Facing Strategy Patch — qb_uxGPT Internal Update**

*(This is the “if I were patching myself right now” section.)*

---

## A. New Hard Rule: Passing Requires End-State Validation

### ❌ Old (faulty) heuristic

> If all engine moves are negative, consider passing to reduce risk.

### ✅ New enforced rule

> **Passing is only legal to recommend if the current end-state is winning for YOU.**

This must be **explicitly validated**, not inferred.

---

## B. Required Internal Check Before Recommending `pass`

Before suggesting `pass`, I must internally answer **YES** to *all* of the following:

1. **If the game ends now, does YOU win at least 2 lanes?**
2. Are those lane wins **robust to end-of-game effect resolution**?
3. Is the opponent’s deck **not end-state biased** (Regina *is* end-state biased)?
4. Would extending the game **strictly increase opponent leverage**?

If *any* answer is “no” → **passing must not be recommended**.

---

## C. New Interpretation of Engine Negative Margins

### ❌ Incorrect interpretation

> Negative margins → no good moves → consider pass

### ✅ Correct interpretation

> Negative margins → equilibrium favors opponent
> → seek **forced interaction or variance**, not stasis

Passing **reduces variance**.
When variance is your only out, passing is self-defeating.

---

## D. Regina-Specific Override (High Priority)

When opponent profile includes **Regina**:

* Treat **end-of-game resolution as hostile**
* Assume:

  * delayed effects > immediate power
  * frozen boards favor her
* Bias recommendations toward:

  * *continuing play*
  * *forcing extra turns*
  * *disrupting effect surfaces*

Even if engine margins worsen short-term.

---

## E. Language & Framing Patch (Critical UX Fix)

I must **never** frame `pass` as:

* “safe”
* “defensive”
* “risk-reducing”

Correct framing:

> “Passing accepts the current end-state.”

If end-state is losing, I must say so **explicitly**.

---

## F. New Endgame Coaching Pattern

When engine outputs are all negative late game:

I should say something like:

> “The engine believes the end-state favors the opponent.
> Passing will lock in that outcome.
> Your only remaining outs involve forcing one more interaction, even if the immediate evaluation worsens.”

This reframes the situation correctly and avoids the trap we fell into.

---

## Final Meta-Lesson (for both docs)

The core learning wasn’t about Regina alone.

It was this:

> **Passing is not a neutral action.
> It is a strategic commitment to the current scoring function.**

Against an end-state-favored opponent, that commitment is often fatal.

---

If you want, next we can:

* formalize a **“lane mathematically locked” checklist**, or
* write a short **Regina endgame playbook** distilled to 5 rules.

This was a painful loss — but it produced *real*, high-quality signal.