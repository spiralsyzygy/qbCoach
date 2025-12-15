# Strategy Patch

## Core strategic principles
- Pawn ranks are the core economy; early turns bias toward positive pawn delta and securing future legal placements. Avoid high-rank empty tiles that can be flipped and reused against you.
- Tempo = action availability. High leverage states reduce the opponent’s legal move space (lane starvation, cutoffs).
- Lane resolution is binary: losing by 1 = losing by 20. Sacrifice/abandon or tie-forcing is valid when a lane is unwinnable.
- Geometry matters: contest frontier/neutral tiles and center influence; forward projections and wedges create pressure, backfill/anchors convert once fronts are set.
- Pawn safety and flip threat: penalize placements the opponent can immediately flip; prefer tiles out of reach or with a counter-flip you control.
- Passing is a commitment to the current end-state, not a neutral action; strongest when move denial already exists. Negative margins imply seeking interaction/variance, not stasis.
- Infrastructure vs payoff: build geometry first (ranks/legality) before payoff drops; “wide” over “tall” when collection is limited; deck construction must guarantee rank-2 access for conditional interaction.

## GPT_Layer Application
- Legal-move anchoring: only recommend moves in the engine’s legal set; if a geometry line is illegal, pivot to a legal proxy.
- Passing guardrails: recommend pass only if the current end-state is winning and robust to resolution; explicitly state when passing locks in a loss.
- Interaction over margin when behind: prefer moves that reduce opponent conversion space or force commitments, even at lower short-term margins.
- Geometry + conditional interaction: if holding conditional interaction, one of the next two turns must advance its legality or deprioritize it.
- Framing: avoid “pass is safe/defensive”; explain passing as accepting the current outcome. Highlight when opponent is end-state favored (e.g., Regina).

## Engine Layer Application
- Heuristic hooks: legal_move_differential, pawn_delta/wealth, pawn_flip_threat, lane_lock_detect, frontier_pressure; incorporate geometry reach and opponent payoff paths.
- Geometry sufficiency checks in deck validation and evaluation: ensure rank-2 creation by turn 3 and flexible lane coverage for conditional interaction legality.
- Strategy evaluation should account for frontier contest, abandonment of unwinnable lanes, and variance-seeking when margins are negative.
- Passing/end-state: evaluations should reflect that passing is only optimal when end-state is already favorable; otherwise prefer interaction.

## Unaddressed Bugs/Issues
- Issue 001 (open): Capparwire @ MID-2 overvalued vs Regina infrastructure (BOT clustered at cols 4–5); engine lacks geometry-aware payoff modeling; GPT should override when effect geometry misses opponent conversion paths.
- Issue 002 (open): Conditional interaction held without geometry support; deck construction/evaluation must enforce geometry sufficiency for rank-gated interaction.

*(Closed items: pawn boundary flip neutralization bug fixed in engine/tests; not listed here.)*
