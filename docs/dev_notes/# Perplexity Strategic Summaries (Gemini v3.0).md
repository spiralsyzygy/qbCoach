# Perplexity Strategic Summaries (Gemini v3.0)

## Prompt 1

"Queen’s Blood FF7 Rebirth strategy principles —
Find authoritative explanations, guides, or analyses covering core strategic concepts such as pawn ranks, lane control, tempo, passing, geometry/projection, conditional card legality, and common win conditions.
Include general, opponent-agnostic principles (not just deck lists), explanations of why certain lanes or board states are strong or weak, and any discussion of infrastructure vs payoff, timing, or end-state resolution.
Also include insights from high-level players or guides on how to build decks when the card collection is limited, and how to translate board geometry into interaction and wins.
Cite sources clearly."

--------------------
Perplexity Response
--------------------

**Core Strategy Principles for Queen’s Blood (Design & Engine Implementation)**

Queen’s Blood is a deterministic territory-control game where board state evaluation relies heavily on "projected power" and "lane resolution." For a Design LLM and coding engine, the game should be modeled not just as a card battler, but as a grid-filling logic puzzle where the primary resource is **legal moves** (defined by pawn ownership and rank) rather than mana.

### 1. The Core Loop: Infrastructure vs. Payoff
The fundamental tension in Queen's Blood is between building **Infrastructure** (placing Pawns/Ranks) and executing **Payoff** (placing high-power Cards).
*   **Infrastructure (Pawn Ranks):** Pawns are the "mana" of the game. They are location-specific. A Rank 2 tile is a valuable resource that must be spent wisely.
*   **Payoff (Power):** Cards with high power often have poor projection (they don't create new pawns). Playing a high-power card "caps" a tile, ending its growth potential.
*   **Design Heuristic:** A strong engine evaluates a move not just by the points it scores, but by the **Net Pawn Delta** (Pawns created - Pawns consumed). Early game favors positive Pawn Delta; late game favors Point conversion.

### 2. Geometry & Projection
Board control is dictated by the specific grid patterns on cards.
*   **The "Forward Wedge" Principle:** The most contested tiles are the ones immediately between the two players' frontlines. Cards that project **forward-diagonal** (like *Cactuar* or *Security Officer*) are critical because they claim the "neutral zone" without occupying it, forcing the opponent to respond.
*   **The "Backfill" Buffer:** Cards that project **backward** are generally used as "Finishers." They are played on the front lines to buff cards behind them. This protects the backline from being flipped, as occupied tiles cannot be stolen.
*   **Checkerboard Dominance:** Because many cards project in diagonal or "X" patterns, board control often resolves into a checkerboard. An engine should value "interlocking" geometries where your cards protect each other’s flanks.

### 3. Conditional Legality & "The Flip"
The unique interaction mechanism in Queen's Blood is the ability to steal **empty** territory.
*   **The Rule:** If a card's projection hits a tile containing an *opponent's Pawn* (but no card), that Pawn flips to your color [1][2]. The Rank is preserved.
*   **Strategic Implication (Tempo):** This creates a "Second-Mover Advantage" in the neutral zone. If Player A claims a tile, Player B can play a card that projects onto that same tile to steal it.
*   **Engine Logic:**
    *   *Bad Move:* Placing a pawn where the opponent can immediately steal it with a known card in hand.
    *   *Good Move:* Placing a card that claims a tile *out of reach* of the opponent's current projection, or "cutting off" a lane so the opponent has no legal placement to steal it back.

### 4. Lane Control & Scoring Resolution
*   **Lane Valuation:** The game is won by total score, but points are binary per lane.
    *   If P1 has 10 Power and P2 has 9 Power in Lane 1, P1 gets 10 points, P2 gets 0.
    *   **Sacrifice Strategy:** If an engine calculates it cannot win a lane, it should stop investing resources there immediately. Losing a lane by 1 point is the same as losing it by 20.
*   **The "2-Lane" Condition:** You only need to win 2 out of 3 lanes to win the match (usually). A common high-level strategy is to completely abandon one lane to ensure dominance in the other two.
*   **Center Lane Priority:** The center lane is strategically most valuable because cards placed there can project/buff into the Top and Bottom lanes. Controlling the center restricts the opponent's ability to cross-pollinate power.

### 5. Tempo & Passing
*   **The "Starvation" Tactic:** Unlike many card games, "Passing" is a strategic weapon. If you have a winning board state, you can Pass. If the opponent cannot generate enough points to flip the lanes, they lose.
*   **Forced Moves:** If you cut off all of an opponent's valid moves (no pawns to play on), they are forced to Pass. If you then Pass, the game ends immediately. This "Lane Lock" is a primary win condition for control decks.

### 6. Deck Building for Limited Collections
For an engine or player with a "starter" collection (limited to Rank 1 and 2 cards), the strategy shifts:
*   **Rank 1 Spam:** Fill the deck with low-cost cards that project pawns (e.g., *Security Officer*, *Levrikon*). The goal is to flood the board with pawns faster than the opponent [3].
*   **Wide vs. Tall:** Limited decks should play "Wide" (filling every square) rather than "Tall" (high power on few squares). The starter opponent AI often struggles to clear "wide" boards.
*   **Replacement Cards:** Even in limited decks, cards like *Mandragora* or *Cactuar* are essential because they are flexible infrastructure builders.

### 7. Code/Engine Heuristics Summary
To assist the Coding LLM, the board state evaluator should use these weighted parameters:
*   **`owned_tile_count`**: +1 for every tile you own (high weight in early turns).
*   **`lane_win_probability`**: Binary check. Is `my_power > opp_power`? If yes, `value = my_power`. If no, `value = 0`.
*   **`opp_move_denial`**: Count of opponent's valid moves. Lower is better.
*   **`pawn_flip_threat`**: Penalty for creating pawns that the opponent can immediately steal next turn.

**Key Sources:**
*   Lane control and "cutting off" opponents are central strategies [4][5].
*   The "second-mover" advantage and stealing pawns via projection [1][2].
*   Deck building prioritizing Rank 1 cards for board coverage [3][6].
*   Passing mechanics and game termination [1].

Sources
[1] How to Play: Queen's Blood in Final Fantasy 7 Rebirth! - YouTube https://www.youtube.com/watch?v=K5z-ZRQD5-I
[2] Final Fantasy 7 Rebirth: Queen's Blood tips and tricks - Digital Trends https://www.digitaltrends.com/gaming/final-fantasy-7-rebirth-queens-blood-tips-and-tricks/
[3] Final Fantasy 7 (VII) Rebirth Queen's Blood Guide - Best Decks ... https://www.powerpyx.com/final-fantasy-7-vii-rebirth-queens-blood-guide-best-decks-strategies/
[4] A simple text guide for Queen's Blood : r/FFVIIRemake - Reddit https://www.reddit.com/r/FFVIIRemake/comments/1bdfdzk/a_simple_text_guide_for_queens_blood/
[5] Final Fantasy 7 Rebirth: How To Always Win Queen's Blood - YouTube https://www.youtube.com/watch?v=YfFgBbME3Ys
[6] Final Fantasy 7 Rebirth Queen's Blood tips for beginners - Eurogamer https://www.eurogamer.net/queens-blood-matches-rules-card-types-final-fantasy-7-rebirth-9403
[7] How To Be The Best Queen's Blood Player In Final Fantasy VII Rebirth https://kotaku.com/final-fantasy-7-rebirth-queens-blood-tips-beginners-1851306482
[8] Queen's Blood Opponents - Final Fantasy VII Rebirth ... - GameFAQs https://gamefaqs.gamespot.com/ps5/371123-final-fantasy-vii-rebirth/faqs/81141/queens-blood-opponents
[9] FINAL FANTASY VII REBIRTH: Tips and tricks for playing Queen's ... https://www.square-enix-games.com/en_US/news/final-fantasy-vii-rebirth-queens-blood-tips
[10] How to Win the Queen's Blood Tournament in FFVII Rebirth https://www.siliconera.com/how-to-win-the-queens-blood-tournament-in-ffvii-rebirth/
[11] Queen's Blood Best Decks | FF7 Rebirth - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Queens-Blood-Best-Decks
[12] Tips for Playing Queen's Blood in Final Fantasy 7 (FF7) Rebirth https://www.escapistmagazine.com/tips-for-playing-queens-blood-in-final-fantasy-7-ff7-rebirth/
[13] Queens Blood BEST Starter Deck, Tips, Tricks & How To Play! (FF7 ... https://www.youtube.com/watch?v=nYbJiuPqRYM
[14] How To Win ALL Card Carnival Queen's Blood Challenges In FF7 ... https://www.youtube.com/watch?v=tN9LUaSCS70
[15] What is good Deck for Queen Blood Gimmick Battlefield: Outflanked? https://www.facebook.com/groups/23491514182/posts/10161249161409183/
[16] Queen's Blood - Final Fantasy 7 Rebirth Guide - IGN https://www.ign.com/wikis/final-fantasy-7-rebirth/Queen's_Blood
[17] All Gold Saucer Queen's Blood Challenges and Solutions - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Minigames-Gold-Saucer-Queens-Blood
[18] How to Win the Queen's Blood Tournament | FF7 Rebirth - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Queens-Blood-Tournament
[19] How to Win ANY Queen's Blood Game - Best Deck & Strategy https://www.youtube.com/watch?v=CfX1vkB907c
[20] Queen's Blood Beginner's Guide - Final Fantasy VII Rebirth - YouTube https://www.youtube.com/watch?v=x_o3KFP7nxo
[21] Queen's Blood players. What's your strategy? : r/FinalFantasyVII https://www.reddit.com/r/FinalFantasyVII/comments/1idr9nz/queens_blood_players_whats_your_strategy/
[22] Final Fantasy 7 Rebirth - All Queen's Blood Opponents For Rank Ups https://www.gamespot.com/gallery/final-fantasy-7-rebirth-queens-blood-opponents-rank-guide/2900-5132/
[23] 'FF7 Rebirth' Queen's Blood Guide: The Best Cards, Decks ... - Inverse https://www.inverse.com/gaming/ff7-rebirth-queens-blood-guide-starter-deck-cards-tips-tournament
[24] Best Queen's Blood Strategies In Final Fantasy 7 Rebirth - TheGamer https://www.thegamer.com/final-fantasy-7-rebirth-best-queens-blood-strategies/
[25] Ways to compute minimal number of chess queen moves to go from a to b? https://www.reddit.com/r/algorithms/comments/kmznje/ways_to_compute_minimal_number_of_chess_queen/
[26] Down and Dirty Guide to Rebirth's Queen's Blood Card Game https://gamingtrend.com/editorials/down-and-dirty-guide-to-rebirths-queens-blood-card-game/
[27] How To Play Queen's Blood - FF7 Rebirth - YouTube https://www.youtube.com/watch?v=TpeQ3bEc8K4
[28] 10 Best Queen's Blood Cards In Final Fantasy 7 Rebirth - Screen Rant https://screenrant.com/final-fantasy-ff7-rebirth-best-queens-blood-cards/
[29] Queen's Blood Basics - Final Fantasy VII Rebirth Walkthrough & Guide https://gamefaqs.gamespot.com/ps5/371123-final-fantasy-vii-rebirth/faqs/81141/queens-blood-basics
[30] Queen's Blood | Final Fantasy Wiki - Fandom https://finalfantasy.fandom.com/wiki/Queen's_Blood
[31] Game Mechanics - Kaycee's Mod General Info - Google Sites https://sites.google.com/view/kaycees-mod-general-info/mechanics?authuser=0
[32] Built a pretty unstoppable Queen's Blood deck - Reddit https://www.reddit.com/r/FFVIIRemake/comments/1bugbxr/built_a_pretty_unstoppable_queens_blood_deck/
[33] The Gold Saucer Queens Blood Challenges and Choices Get Lucky ... https://worldwide-studies.com/the-gold-saucer-queens-blood-challenges-and-choices-get-lucky-casino-new-player-bonus-ff7-rebirth/
[34] How to Win the Queen's Blood Tournament in FF7 Rebirth https://www.escapistmagazine.com/how-to-win-the-queens-blood-tournament-in-ff7-rebirth/
[35] Costa del Sol Queen's Blood Puzzles - Final Fantasy 7 Rebirth Guide https://www.ign.com/wikis/final-fantasy-7-rebirth/All_Costa_del_Sol_Queen's_Blood_Puzzles
[36] tips/advice for queen's blood? It seems like it could get difficult https://gamefaqs.gamespot.com/boards/371123-final-fantasy-vii-rebirth/80710117
[37] How To Win The Queen's Blood Invitational In Final Fantasy 7 Rebirth https://www.thegamer.com/final-fantasy-7-rebirth-ff7r-queens-blood-invitational-walkthrough/
[38] Queen's Blood Tutorial - Final Fantasy VII Rebirth - Gamer Guides https://www.gamerguides.com/final-fantasy-vii-rebirth/guide/minigames/queens-blood/queens-blood-tutorial-final-fantasy-vii-rebirth
[39] Tips enjoy Queen's Bloodstream inside Finally Fantasy 7 Revival ... https://cotsen.org/tips-enjoy-queens-bloodstream-inside-finally-fantasy-7-revival-suggestions-to-victory/

=========
Prompt 2
=========

"Core principles of pawn ranks and placement priority"

--------------------
Perplexity Response
--------------------

**Core Principles of Pawn Ranks and Placement Priority**

The design of a Queen’s Blood engine or strategy guide must treat **Pawn Ranks** as the game's primary economic currency and **Placement Priority** as its spatial logic. These two concepts govern the flow of the game from the opening moves to the final board state.

### 1. Pawn Ranks: The "Mana" of Queen's Blood
Unlike card games where mana refreshes every turn, Pawn Ranks are a persistent, location-based resource that must be built, spent, and protected.

*   **Rank as "Entry Fee":** A card's rank (1, 2, or 3 pawns) dictates the "entry fee" for a specific tile. You cannot play a Rank 2 card on a Rank 1 tile [1].
*   **Rank Accumulation:** You "level up" a tile by placing cards on *neighboring* tiles whose projection patterns (yellow squares) hit that tile.
    *   *Engine Logic:* `Tile_Rank_Next = Tile_Rank_Current + Incoming_Projection`.
    *   *Strategic Implication:* You don't play high-rank cards to win lanes directly; you play low-rank cards to *build the infrastructure* for high-rank cards [2].
*   **The "Rank Trap":** Beginners often fill their deck with powerful Rank 3 cards but fail to include enough "Rank Builders" (cards with wide projection). A deck with too many high-rank cards will "brick" because you can never build the requisite pawns on the board to play them.
*   **Rank Persistence:** When a pawn is stolen by the opponent (flipped from green to red), the **Rank of that tile is preserved**.
    *   *Tactical Risk:* If you build a tile up to Rank 3 but leave it empty, your opponent can steal it with a simple projection and immediately drop a powerful Rank 3 card on it, using *your* infrastructure against you [3].

### 2. Placement Priority: "The Wedge" & "The Anchor"
Efficient placement isn't just about accumulating points; it's about restricting opponent options while expanding yours.

#### A. The Opening: Center & Forward (The "Wedge")
*   **Priority 1: Claim the Center Lane.** The center lane (Rank 2) is the most critical real estate. Cards placed here can project into *both* the top and bottom lanes, effectively doubling their infrastructure value [4][5].
*   **Priority 2: The "Forward Wedge".** Place low-rank cards (like *Security Officer* or *Levrikon*) that project **forward** into the neutral zone.
    *   *Goal:* Create a "wedge" where your pawns are closer to the enemy side than theirs are to yours. This forces the opponent to play defensively.
*   **Lane Synergy Rule:**
    *   **Flying/Top-Heavy Cards** (project down-forward) -> Play in **Top Lane**.
    *   **Ground/Bottom-Heavy Cards** (project up-forward) -> Play in **Bottom Lane**.
    *   **Forward-Only Cards** -> Play in **Middle Lane** [5].

#### B. The Mid-Game: Blocking & Stealing (The "Cutoff")
*   **Blocking (Denial):** If you can place a pawn on a tile that is the *only* valid expansion point for an opponent's lane, do it immediately. Even if the card is weak, "cutting off" their supply line effectively kills that lane [6][7].
*   **Stealing (The Flip):** Prioritize moves that flip an opponent's empty pawn to your color. This is a +2 net swing in economy (+1 for you, -1 for them).
    *   *Safe Stealing:* Only steal a pawn if your opponent cannot immediately steal it back on their next turn (check their hand/projection).

#### C. The End-Game: Backfilling (The "Anchor")
*   **Backfill Strategy:** Once the front lines meet and no more forward expansion is possible, shift focus to your **backline**.
*   **The Anchor:** Drop high-power, low-projection cards (like *Titan* or *Ifrit*) into the safe pockets you created behind your front line. These cards are "Payoff" cards—they don't need to build future value; they just need to score points [8].
*   **Buffing the Front:** Use cards that project *backward* to buff your front-line cards. Since front-line cards are often low-power "builders," they are vulnerable to being destroyed. Buffing them secures the lane win.

### Summary for Engine Implementation
| Concept | Logic/Heuristic |
| :--- | :--- |
| **Rank Economy** | Value moves that increase `sum(all_owned_tile_ranks)` early in the game. |
| **Pawn Security** | Penalize moves that create high-rank empty tiles adjacent to enemy projection. |
| **Lane Bias** | Weight `Center_Lane` moves 1.5x higher in the first 3 turns. |
| **Cutoff Value** | High reward for moves that reduce `opponent_valid_move_count` to 0 in a lane. |
| **Expansion** | Prefer cards that project into `neutral_zone` (cols 3-4) over safe zones (cols 1-2). |

Sources
[1] Queen's Blood | Final Fantasy Wiki - Fandom https://finalfantasy.fandom.com/wiki/Queen's_Blood
[2] Down and Dirty Guide to Rebirth's Queen's Blood Card Game https://gamingtrend.com/editorials/down-and-dirty-guide-to-rebirths-queens-blood-card-game/
[3] How to Play: Queen's Blood in Final Fantasy 7 Rebirth! - YouTube https://www.youtube.com/watch?v=K5z-ZRQD5-I
[4] Final Fantasy 7 Rebirth Queen's Blood tips for beginners - Eurogamer https://www.eurogamer.net/queens-blood-matches-rules-card-types-final-fantasy-7-rebirth-9403
[5] Final Fantasy 7 (VII) Rebirth Queen's Blood Guide - Best Decks ... https://www.powerpyx.com/final-fantasy-7-vii-rebirth-queens-blood-guide-best-decks-strategies/
[6] Queen's Blood Tutorial - Final Fantasy VII Rebirth - Gamer Guides https://www.gamerguides.com/final-fantasy-vii-rebirth/guide/minigames/queens-blood/queens-blood-tutorial-final-fantasy-vii-rebirth
[7] Best Queen's Blood Strategies In Final Fantasy 7 Rebirth - TheGamer https://www.thegamer.com/final-fantasy-7-rebirth-best-queens-blood-strategies/
[8] FINAL FANTASY VII REBIRTH: Tips and tricks for playing Queen's ... https://www.square-enix-games.com/en_US/news/final-fantasy-vii-rebirth-queens-blood-tips
[9] A simple text guide for Queen's Blood : r/FFVIIRemake - Reddit https://www.reddit.com/r/FFVIIRemake/comments/1bdfdzk/a_simple_text_guide_for_queens_blood/
[10] Queen's Blood Opponents - Final Fantasy VII Rebirth ... - GameFAQs https://gamefaqs.gamespot.com/ps5/371123-final-fantasy-vii-rebirth/faqs/81141/queens-blood-opponents
[11] How To Play Queen's Blood - FF7 Rebirth - YouTube https://www.youtube.com/watch?v=TpeQ3bEc8K4
[12] Final Fantasy 7 Rebirth: Queen's Blood tips and tricks - Digital Trends https://www.digitaltrends.com/gaming/final-fantasy-7-rebirth-queens-blood-tips-and-tricks/
[13] Beginners Tips for Queen's Blood in FFVII Rebirth - Hardcore Gamer https://hardcoregamer.com/beginners-tips-for-queens-blood-in-ffvii-rebirth/
[14] All Gold Saucer Queen's Blood Challenges and Solutions - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Minigames-Gold-Saucer-Queens-Blood
[15] Queen's Blood Beginner's Guide - Final Fantasy VII Rebirth - YouTube https://www.youtube.com/watch?v=x_o3KFP7nxo
[16] Strategies for Winning Queen's Blood and Gold Saucer Matches in ... https://www.facebook.com/groups/23491514182/posts/10161163860149183/
[17] Gold Saucer Queen's Blood Advanced Challenges - FF7 Rebirth https://www.gamerguides.com/final-fantasy-vii-rebirth/guide/minigames/queens-blood/gold-saucer-queens-blood-advanced-challenges-ff7-rebirth
[18] Final Fantasy 7 Rebirth: Queen's Blood and All Ranks Explained https://gamerant.com/final-fantasy-7-rebirth-queens-blood-all-ranks-explained/
[19] Queen's Blood players. What's your strategy? : r/FinalFantasyVII https://www.reddit.com/r/FinalFantasyVII/comments/1idr9nz/queens_blood_players_whats_your_strategy/
[20] FF7 Rebirth: How To Win Queen's Blood (Deckbuilding Guide) https://screenrant.com/ff7-rebirth-how-to-win-queens-blood-deckbuilding-guide/
[21] Queen's Blood - Final Fantasy 7 Rebirth Guide - IGN https://www.ign.com/wikis/final-fantasy-7-rebirth/Queen's_Blood


=========
Prompt 3
=========

"How lane control creates tempo and advantages in Queen's Blood"

--------------------
Perplexity Response
--------------------

**Lane Control and Tempo: Creating Advantages in Queen's Blood**

For the Design and Coding team, "Lane Control" and "Tempo" are the variables that determine the validity of the game state. They are less about the score (which is a lagging indicator) and more about the **Action Economy** (a leading indicator).

### 1. Defining "Tempo" in Queen's Blood
In most card games, tempo is speed. In Queen’s Blood, tempo is **Action Availability**.
*   **The Principle:** Every turn, both players *should* make a move. If you create a board state where your opponent *cannot* make a meaningful move (due to lack of pawns or valid tiles), you have gained infinite tempo.
*   **Forced Pass (The "Soft Lock"):** If Player B has 0 valid moves, they are forced to Pass. Player A can then continue playing until their hand is empty or they choose to stop. This is the ultimate tempo win condition.
    *   *Engine Logic:* A move that reduces `opponent_valid_moves` to 0 is valued higher than a move that gains +5 points but leaves the opponent with options.

### 2. Lane Control as Resource Denial (The "Choke")
Control is not about owning the most tiles; it is about owning the **frontier**.
*   **The Choke Point:** By placing a pawn on the specific tile that an opponent needs to expand their lane, you "choke" that lane.
    *   *Example:* If the opponent has a card in the back of the top lane that projects one square forward, placing *your* pawn on that square neutralizes their ability to play there.
*   **The "Starvation" Strategy:** Players with limited decks (Rank 1 spam) use this to win against high-level AI. By filling the board cheaply and quickly, you deny the AI the physical space to play their high-power Rank 3 cards [1].
    *   *Tactical Heuristic:* "It is better to place a 1-power card that blocks an enemy expansion than a 5-power card that does not."

### 3. "Second-Mover Advantage" and Reactionary Tempo
Because of the "Pawn Flip" mechanic (stealing empty pawns), the player who acts *second* in a contested zone often wins it.
*   **The Trap:** Player A claims a neutral tile. Player B plays a card that projects onto that tile, stealing it. Player B now owns the tile *and* has their projecting card safely behind it.
*   **Delayed Gratification:** High-level play often involves *refusing* to take a neutral tile until you can secure it permanently.
    *   *Engine Implementation:* The engine should penalize moves that claim neutral tiles if the opponent has a known "counter-projection" available.

### 4. Sacrificing Lanes for Global Tempo
Since you only need to win 2 out of 3 lanes, "losing correctly" is a key skill.
*   **The "Bait" Lane:** Intentionally play weak cards in a lane to entice the opponent to over-commit resources there. Once they drop a high-value card (like *Titan* or *Bahamut*), abandon the lane completely.
*   **Resource Asymmetry:** If the opponent spends 10 points of power to beat your 2 points of power, you have won the "efficiency war." You can now use your remaining high-power cards to dominate the other two lanes where the opponent is resource-poor.
*   **Tie-Breaking:** If a lane is tied, *nobody* gets points. An engine should recognize that forcing a tie in a losing lane is mathematically identical to winning it (relative to the score delta).

### 5. Interaction and "Kill" Decks
While territory is the default win condition, "Destroy" decks (using cards like *Tonberry King* or *Gi Nattak*) convert Board Geometry into direct removal.
*   **Geometry as a Weapon:** "Lane Control" here means positioning cards not to hold territory, but to align firing vectors.
*   **Resolution Order:** Effects resolve from Top-Left to Bottom-Right. Understanding this allows you to destroy an enemy buffing card *before* it applies its buff, effectively negating their turn.

### Summary for the Engine
*   **Metric:** `Action_Differential` = (My Valid Moves) - (Opponent Valid Moves). Maximize this.
*   **Heuristic:** If `Opponent_Valid_Moves` in Lane X == 0, Lane X is "Locked." Stop spending resources there unless the score is threatened.
*   **Win Condition:** If `Locked_Lanes` >= 2 and `My_Score` > `Opp_Score`, the game is mathematically won; execute aggressive Pass.

Sources
[1] I need a way to easy win Queen's Blood : r/FF7Rebirth - Reddit https://www.reddit.com/r/FF7Rebirth/comments/1jfrd59/i_need_a_way_to_easy_win_queens_blood/
[2] Queen's Blood players. What's your strategy? : r/FinalFantasyVII https://www.reddit.com/r/FinalFantasyVII/comments/1idr9nz/queens_blood_players_whats_your_strategy/
[3] Final Fantasy 7 Rebirth: How To Always Win Queen's Blood - YouTube https://www.youtube.com/watch?v=YfFgBbME3Ys
[4] How to Win the Queen's Blood Tournament | FF7 Rebirth - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Queens-Blood-Tournament
[5] How To Be The Best Queen's Blood Player In Final Fantasy VII Rebirth https://kotaku.com/final-fantasy-7-rebirth-queens-blood-tips-beginners-1851306482
[6] The Mechanisms of Gameplay: Value, Tempo, and Initiative https://rathetimes.com/articles/the-mechanisms-of-gameplay-value-tempo-and-initiative
[7] DOMINATE Queens Blood BEFORE Its Too Late (FF7 Rebirth) https://www.youtube.com/watch?v=SZGZJ4clMgQ
[8] Tips for Playing Queen's Blood in Final Fantasy 7 (FF7) Rebirth https://www.escapistmagazine.com/tips-for-playing-queens-blood-in-final-fantasy-7-ff7-rebirth/
[9] How To Win ALL Card Carnival Queen's Blood Challenges In FF7 ... https://www.youtube.com/watch?v=tN9LUaSCS70
[10] Final Fantasy 7 (VII) Rebirth Queen's Blood Guide - Best Decks ... https://www.powerpyx.com/final-fantasy-7-vii-rebirth-queens-blood-guide-best-decks-strategies/
[11] You aren't forced to do Queen's Blood at all! + some helpful QB info. https://gamefaqs.gamespot.com/boards/371123-final-fantasy-vii-rebirth/80720126
[12] 'FF7 Rebirth' Queen's Blood Guide: The Best Cards, Decks ... - Inverse https://www.inverse.com/gaming/ff7-rebirth-queens-blood-guide-starter-deck-cards-tips-tournament
[13] How to Win the Queen's Blood Tournament in FFVII Rebirth https://www.siliconera.com/how-to-win-the-queens-blood-tournament-in-ffvii-rebirth/
[14] FINAL FANTASY VII REBIRTH: Tips and tricks for playing Queen's ... https://www.square-enix-games.com/en_US/news/final-fantasy-vii-rebirth-queens-blood-tips
[15] The Best Queen's Blood Deck In Final Fantasy VII Rebirth https://gameinformer.com/tips-tricks/2024/02/28/the-best-queens-blood-deck-in-final-fantasy-vii-rebirth
[16] [FF7 Rebirth ] Queen`s Blood : Having FUN SACRIFICING Minions ... https://www.youtube.com/watch?v=ZDUZy7r03Uw
[17] Queen's Blood Beginner's Guide - Final Fantasy VII Rebirth - YouTube https://www.youtube.com/watch?v=x_o3KFP7nxo
[18] I just don't get Queen's Blood lol - Final Fantasy VII Rebirth https://gamefaqs.gamespot.com/boards/371123-final-fantasy-vii-rebirth/80710864
[19] Final Fantasy 7 Rebirth Queen's Blood tips for beginners - Eurogamer https://www.eurogamer.net/queens-blood-matches-rules-card-types-final-fantasy-7-rebirth-9403
[20] Best Queen's Blood Strategies In Final Fantasy 7 Rebirth - TheGamer https://www.thegamer.com/final-fantasy-7-rebirth-best-queens-blood-strategies/


=========
Prompt 4
=========

"Geometry and projection how to force opponent into bad boards"

--------------------
Perplexity Response
--------------------

**Geometry & Projection: Forcing "Bad Boards"**

For the Design and Coding team, "forcing a bad board" means using geometric projection to reduce the opponent's **Search Space** (valid moves) and **Efficiency** (points per tile). The goal is to make the opponent's board "clunky"—disconnected, blocked, or unusable.

### 1. The Geometry of "Bad Boards"
A "bad board" for an opponent is defined by three geometric states:
*   **The "Orphaned" Pawn:** A pawn (Rank 1/2) that has no valid neighbor tiles to expand into. It is stranded resource that cannot grow.
*   **The "L-Lock":** When an opponent's expansion options are blocked in an "L" shape by your pawns, preventing them from placing 2x2 or complex shape cards.
*   **The "Cross-Fire" Zone:** A tile where, if the opponent places a card, it will immediately be destroyed or debuffed by your existing projection (e.g., *Archdragon* or *Quetzalcoatl*).

### 2. Projection Archetypes & Their Functions
Different projection shapes serve distinct tactical roles in restricting the opponent:

| Projection Shape | Tactical Role | Key Example |
| :--- | :--- | :--- |
| **Forward-Diagonal (The Fork)** | Threatens two forward tiles simultaneously. Forces opponent to defend one, often surrendering the other. | *Security Officer, Cactuar* |
| **The "Wall" (Vertical Line)** | Creates a solid front that is hard to "jump" over. Good for locking down a won neutral zone. | *Elphadunk, Mandragora* |
| **The "Sniper" (Forward-Skip)** | Projects onto a tile *behind* the immediate front line. Used to steal back-line pawns or break opponent connectivity. | *Levrikon, Archdragon* |
| **The "Back-Brace" (Backward)** | Projects backward to secure your own weak points. Prevents opponent from using "Sniper" geometry to flip your rear pawns. | *Crystalline Crab* |

### 3. The "Pinning" Technique
You can "pin" an opponent's expansion by manipulating the "Entry Fee" (Rank) of the tiles they want.
*   **The Rank Gap:** If you suspect the opponent has a hand full of Rank 2 cards (common in mid-game), you can aggressively flip their only Rank 2 pawn back to Rank 1 (using destruction or replacement effects).
*   **Result:** They are now "Rank Locked." They have powerful cards but no legal infrastructure to play them. This forces them to waste turns playing weak Rank 1 cards just to rebuild, destroying their tempo.

### 4. Advanced Geometry: The "Checkerboard" Trap
High-level play often devolves into a checkerboard pattern where players own alternating tiles.
*   **The Trap:** If you can force the board into a checkerboard state where *your* cards project diagonally (hitting their squares) but *their* cards project orthogonally (hitting empty space or edges), you win the attrition war.
*   **Implementation:** Prioritize cards with **X-shaped** or **Diagonal** projection (like *Mindflayer*) when the board gets crowded. Orthogonal projection (*Elphadunk*) is strong early but weak in a crowded "clinch."

### 5. Engine Logic for "Projection Pressure"
To code an engine that understands this:
*   **Pressure Map:** Calculate a "Pressure Value" for every empty tile.
    *   `Pressure = (My_Incoming_Projection_Count) - (Opponent_Incoming_Projection_Count)`
*   **The "Bad Board" Heuristic:** The engine should value moves that *decrease* the average `Pressure` on the opponent's side (meaning the opponent has fewer ways to expand).
*   **Lookahead:** "If I play Card A here, does it remove the *only* valid placement tile for the opponent's likely Card B?"

### 6. Summary: The "Geometric Strangle"
The ultimate goal of geometry strategy is the **Strangle**:
1.  **Advance:** Use Forward-Diagonal cards to touch the enemy's side of the board.
2.  **Claim:** Place a pawn on their "expansion node" (the tile they need to grow).
3.  **Solidify:** Play a card that projects *sideways* into that node to secure it, making it impossible for them to steal back.
4.  **Result:** The opponent is boxed into their starting corner, with no geometric path to the center [1][2].

**Citations:**
*   Blocking expansion nodes ("The Choke") [1][3].
*   Diagonal vs Orthogonal projection utility [4].
*   The "Rank Lock" concept implicitly derived from Rank mechanics [5].
*   Pressure and territory denial strategies [6][7].

**Final Fantasy VII Rebirth: Queen’s Blood Strategy Principles**

### Executive Summary
Queen's Blood is a deterministic, territory-control card game that rewards **spatial denial** over raw power. The core strategic loop involves balancing **Infrastructure** (building Pawn Ranks) against **Payoff** (scoring points), governed by a strict "Action Economy." An effective AI engine or player strategy must prioritize **Net Pawn Delta** (creating more future moves than you consume) and **Lane Locking** (denying the opponent legal moves).

### 1. Core Mechanics & Infrastructure
*   **Pawn Economy:** Pawns are the game's "mana," but they are location-specific. A move is only efficient if it maintains or grows your total "Pawn Wealth" (sum of ranks of all owned tiles) [5].
*   **Rank Building:** The primary early-game goal is to build Rank 2 tiles in the center lane. The Center Lane is the "high ground" because it allows projection into both Top and Bottom lanes, maximizing board influence [4][3].
*   **Deck Composition:** "Brick" hands (unplayable high-rank cards) are the most common loss condition. A stable deck requires a ratio of ~6-8 Rank 1 "enablers" to ensure the board can be developed.
    *   *Engine Heuristic:* Value Rank 1 cards with forward projection (e.g., *Security Officer*) highly in the opening 3 turns.

### 2. Geometry & Projection
*   **The "Wedge" Principle:** Cards with forward-diagonal projection (e.g., *Cactuar*) are superior openers. They claim the "Neutral Zone" (columns 3-4) without occupying it, forcing the opponent to respond to your threat rather than developing their own game [1][4].
*   **The "Flip" (Stealing Territory):** A unique mechanic allows you to steal an opponent's empty pawn if your card projects onto it. This creates a "Second-Mover Advantage" in contested tiles.
    *   *Strategy:* Do not claim a neutral tile if the opponent can immediately steal it back. Instead, set up a "counter-flip" by letting them claim it first [8][9].
*   **Checkerboard Control:** As the board fills, diagonal ("X") projection becomes more valuable than orthogonal ("+") projection because it can reach "behind" enemy lines and support isolated allies.

### 3. Lane Control & Tempo
*   **Tempo as Action Availability:** Tempo is defined by the number of **Valid Moves** available. If you reduce an opponent's valid moves to zero, they are forced to Pass. If you then Pass, the game ends.
    *   *The "Lane Lock":* By placing a pawn on the specific tile an opponent needs to expand a lane, you "lock" that lane. Even a low-power card is valuable if it denies the opponent 100% of a lane's potential [10][2].
*   **The "2-Lane" Condition:** You only need to win 2 out of 3 lanes.
    *   *Sacrifice Play:* If a lane is mathematically lost (or requires too many resources to save), abandon it immediately. Reallocate those resources to secure the other two lanes.
    *   *Tie-Breaking:* A tied lane awards 0 points to both players. Forcing a tie in a losing lane is strategically identical to winning it [3].

### 4. Limited Collection & Starter Strategy
*   **Rank 1 Spam (The "Wide" Strategy):** For limited collections, the optimal strategy is to flood the board with low-cost Rank 1 cards. The AI often struggles to clear a board that is "wide" (many low-power cards) vs "tall" (few high-power cards) [4][11].
*   **Critical Starter Cards:**
    *   *Security Officer / Levrikon:* Essential for forward expansion.
    *   *Cactuar:* Provides excellent "Wedge" geometry.
    *   *Titan:* The classic "Payoff" card for the mid-game.

### 5. Engine Implementation Guidelines
For the Coding LLM, the board evaluator should prioritize these weighted factors:
1.  **`Legal_Move_Differential`**: (My Valid Moves) - (Opponent Valid Moves). *Maximize this to force a lock.*
2.  **`Center_Control`**: Weight ownership of Center Lane (Col 2-4) 1.5x higher than edges.
3.  **`Pawn_Safety`**: Penalize placing a pawn on a tile that the opponent can steal next turn (lookahead = 1).
4.  **`Lane_Resolution`**: If `My_Score` > `Opp_Score` + `Opp_Max_Potential` in a lane, mark lane as "Won" and stop investing resources.

| Concept | Strategic Action | Engine Variable |
| :--- | :--- | :--- |
| **Infrastructure** | Play Rank 1 cards to build Rank 2 tiles. | `pawn_wealth` |
| **Tempo** | Deny opponent valid moves ("Choking"). | `opp_legal_moves` |
| **Payoff** | Place high-power cards on "capped" tiles. | `tile_power_efficiency` |
| **Geometry** | Use diagonal projection to control neutral zones. | `tile_pressure_map` |

Sources
[1] A simple text guide for Queen's Blood : r/FFVIIRemake - Reddit https://www.reddit.com/r/FFVIIRemake/comments/1bdfdzk/a_simple_text_guide_for_queens_blood/
[2] Queen's Blood Tutorial - Final Fantasy VII Rebirth - Gamer Guides https://www.gamerguides.com/final-fantasy-vii-rebirth/guide/minigames/queens-blood/queens-blood-tutorial-final-fantasy-vii-rebirth
[3] Final Fantasy 7 Rebirth Queen's Blood tips for beginners - Eurogamer https://www.eurogamer.net/queens-blood-matches-rules-card-types-final-fantasy-7-rebirth-9403
[4] Final Fantasy 7 (VII) Rebirth Queen's Blood Guide - Best Decks ... https://www.powerpyx.com/final-fantasy-7-vii-rebirth-queens-blood-guide-best-decks-strategies/
[5] Queen's Blood | Final Fantasy Wiki - Fandom https://finalfantasy.fandom.com/wiki/Queen's_Blood
[6] How to Win the Queen's Blood Tournament | FF7 Rebirth - Game8 https://game8.co/games/Final-Fantasy-VII-Rebirth/archives/Queens-Blood-Tournament
[7] Down and Dirty Guide to Rebirth's Queen's Blood Card Game https://gamingtrend.com/editorials/down-and-dirty-guide-to-rebirths-queens-blood-card-game/
[8] How to Play: Queen's Blood in Final Fantasy 7 Rebirth! - YouTube https://www.youtube.com/watch?v=K5z-ZRQD5-I
[9] Final Fantasy 7 Rebirth: Queen's Blood tips and tricks - Digital Trends https://www.digitaltrends.com/gaming/final-fantasy-7-rebirth-queens-blood-tips-and-tricks/
[10] Best Queen's Blood Strategies In Final Fantasy 7 Rebirth - TheGamer https://www.thegamer.com/final-fantasy-7-rebirth-best-queens-blood-strategies/
[11] I need a way to easy win Queen's Blood : r/FF7Rebirth - Reddit https://www.reddit.com/r/FF7Rebirth/comments/1jfrd59/i_need_a_way_to_easy_win_queens_blood/

