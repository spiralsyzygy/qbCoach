# 📘 **EPIC E — Opponent & Deck Modeling (Design Spec v0.1)**

*(High-Level Design Only — No Implementation Yet)*

---

# **E0 — Purpose**

Epic E introduces **predictive reasoning over unseen cards**, allowing qbCoach_v2 to:

* Model the **player’s deck**
* Model the **enemy’s deck**
* Track which cards are already used
* Infer possible remaining enemy cards
* Weight future moves based on likely enemy draws
* Recognize matchup-specific traps earlier (e.g., Mandragora)
* Improve the Predictor Engine beyond 1-ply “local reply”

This Epic transforms qbCoach from a *localized tactical engine* into a *true strategic forecasting engine*.

---

# **E1 — Core Insight**

Game state is not just:

* Board
* Hand

It is also:

* **Deck composition**
* **Remaining cards**
* **Enemy’s likely remaining cards**
* **Turn timing**
* **Matchup-specific play patterns**

Epic E enables the coach to reason about:

> “What can the enemy still play next turn, or the turn after that? And how likely is it?”

This dramatically improves:

* Trap avoidance
* Lane stability predictions
* Long-term move planning
* Early detection of geometric risks
* Risk-weighted scoring
* Handling high-variance matchups

---

# **E2 — Components Introduced in Epic E**

Epic E introduces three major modules:

---

## **E2.1 — PlayerDeckModel**

Tracks your deck composition, including:

* Full deck list (provided by user or inferred from match context)
* Starting hand
* Drawn cards
* Played cards
* Cards remaining in deck

### PlayerDeckModel Fields

```text
deckList: full list of cards (hydrated)
drawnCards: cards in hand + cards played
remainingCards: deckList - drawnCards
turnDrawHistory: ordered list of draws
```

### PlayerDeckModel Capabilities

1. Validate deck size and composition (optional rules).
2. Predict your next draw (uniform unless effects alter odds).
3. Check if you still have key cards left (ZU, AD, MDR, etc.).
4. Support multi-turn forecasting in PredictorEngine v2.x.

---

## **E2.2 — OpponentDeckModel**

This is the heart of Epic E.

The engine must:

* Use **matchup deck profiles** when available
  (`qb_opponent_profile_red_xiii_v1.0.0.md`, etc.)
* Update enemy’s remaining deck as cards appear
* Infer enemy hand size
* Infer what enemy CAN’T play anymore
* Predict which strategic threats are still live

### OpponentDeckModel Fields

```text
startingDeckProfile: canonical deck for this opponent
observedCards: cards enemy has played
remainingDeck: startingDeckProfile - observedCards
estimatedHandSize: based on turn order
estimatedHand: probabilistic set from remainingDeck
threatModel: evaluations of remaining high-impact cards
```

### ThreatModel Example

For Red XIII:

* Mandragora threat: HIGH
* Flametrooper spine reinforcement: MED
* Gryphon Wolf chase: LOW
* Capparwire X-effect disruptor: HIGH

The threat model informs prediction heuristics.

---

## **E2.3 — Probabilistic Predictor Engine (v2.0)**

Epic D introduced Predictor v1:

**YOU → ENEMY local reply**, deterministic from known hand.

Epic E upgrades this:

**YOU → ENEMY (local reply + possible drawn cards)**
and eventually **YOU → ENEMY → YOU**, shallow tree.

### Predictor v2 Steps

1. Simulate your move
2. Enumerate **enemy legal replies from current hand**
3. Enumerate **enemy legal replies from *predicted* hand**
4. Weight each predicted reply by likelihood
5. Blend predicted outcomes into a probabilistic score

### Sample likelihood calculation

```
P(enemy_has_MDR_next_turn) =  (# Mandragora in remainingDeck) / deckSizeRemaining
```

### Influences on moveScore

* If enemy likely has MDR → penalize fragile mid-lines
* If FT likely gone → reward aggressive mid2 pushes
* If enemy retains high-cost cards → avoid neutralizing tiles prematurely
* If enemy low on 2-cost plays → blocking moves become stronger

Epic E would make qbCoach *much* better at anticipating losses like the Mandragora trap.

---

# **E3 — New Heuristics Introduced**

Epic E adds:

### 1. **Threat Detection Layer**

* Identifies cards in enemy’s remaining deck that could punish you
* Determines risk weighting for each lane

### 2. **Draw Pressure Forecasting**

* Estimates how long until enemy hits specific cards
* Compares their deck velocity to your own

### 3. **Trap Avoidance Model**

* Detects geometric states that enemy *could* exploit
* Even if they don’t have the card *yet*
* Uses threat likelihood to adjust move ranking

### 4. **Long-Term Lane Stability Model**

* Current lane lead becomes less valuable if enemy likely has access to powerful swing cards

### 5. **Probability-Weighted Move Ranking**

Turns Epic D’s deterministic predictor into:

```
expectedMoveScore = Σ (probability × outcomeValue)
```

---

# **E4 — Epic E Deliverables**

Epic E would produce:

## **4.1 New KB Docs**

* `qb_deck_modeling_v1.0.0.md`
* `qb_opponent_modeling_v1.0.0.md`
* Updated opponent profiles (optional)

## **4.2 Document Upgrades**

* Update `qb_engine` → v2.2.0
* Update `qb_rules` only if opponent draw rules need clarification
* Update startup diagnostic to include deck validation
* Update core prompt → v1.1.0

## **4.3 Engine Changes**

* Add PlayerDeckModel
* Add OpponentDeckModel
* Add Predictor v2 (probabilistic)
* Enhance MoveRanker heuristics

---

# **E5 — What Epic E Does *Not* Do**

To control scope:

* It does **not** add deep minimax or simulation tree > 2-ply
* It does **not** use machine learning or statistical inference beyond deck composition
* It does **not** attempt to “learn” opponent behavior
* It does **not** override rules or engine logic

Epic E remains fully deterministic and rules-driven.