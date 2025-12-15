from pathlib import Path

from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.game_state import GameState
from qb_engine.projection import (
    ProjectionResult,
    apply_pawns_for_enemy,
    apply_pawns_for_you,
    compute_projection_targets,
    compute_projection_targets_for_enemy,
)


def _make_game_state():
    hydrator = CardHydrator()
    effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    dummy_ids = [cid for cid in sorted(hydrator.index.keys()) if cid != "_meta"][:15]
    return GameState(Deck(dummy_ids), Deck(dummy_ids), hydrator, effect_engine), hydrator


def test_enemy_pawn_flips_at_boundary_not_neutral():
    gs, hydrator = _make_game_state()
    board = gs.board
    # Ensure target tile is unoccupied Y1
    target = board.tile_at(1, 1)
    target.owner = "Y"
    target.rank = 1
    target.card_id = None
    # Place an enemy pawn targeting this tile explicitly via projection
    card = hydrator.get_card("001")
    proj = ProjectionResult(root_lane_index=1, root_col_index=1, targets=[(1, 1, "P")])
    apply_pawns_for_enemy(board, proj, card)
    assert target.owner == "E"
    assert target.rank >= 1


def test_you_pawn_flips_at_boundary_not_neutral():
    gs, hydrator = _make_game_state()
    board = gs.board
    target = board.tile_at(1, 3)
    target.owner = "E"
    target.rank = 1
    target.card_id = None
    card = hydrator.get_card("001")
    proj = ProjectionResult(root_lane_index=1, root_col_index=3, targets=[(1, 3, "P")])
    apply_pawns_for_you(board, proj, card)
    assert target.owner == "Y"
    assert target.rank >= 1


def test_crystalline_crab_flips_y1_to_e1_on_projection():
    gs, hydrator = _make_game_state()
    board = gs.board
    # Make top-4 legal for enemy and top-3 a Y1 target
    board.tile_at(0, 3).owner = "E"
    board.tile_at(0, 3).rank = 3
    target = board.tile_at(0, 2)
    target.owner = "Y"
    target.rank = 1
    target.card_id = None
    card = hydrator.get_card("013")  # Crystalline Crab B3P,C2X,D3P
    gs.apply_enemy_play_from_card_id("013", lane=0, col=3)
    target_after = board.tile_at(0, 2)
    assert target_after.owner == "E"
    assert target_after.rank >= 1
    # Also ensure other projection applied (top-5)
    assert board.tile_at(0, 4).owner == "E"


def test_special_pawn_amount_boundary_flip():
    gs, hydrator = _make_game_state()
    board = gs.board
    target = board.tile_at(1, 1)
    target.owner = "Y"
    target.rank = 1
    target.card_id = None
    # Find a card with special pawn amount (effect_id on_play_raise_positions_rank_2)
    # Use hydrator index to locate
    special = None
    for cid, entry in hydrator.index.items():
        if cid == "_meta":
            continue
        if entry.get("effect_id") == "on_play_raise_positions_rank_2":
            special = hydrator.get_card(cid)
            break
    if special is None:
        return  # skip if DB lacks such a card
    proj = ProjectionResult(root_lane_index=1, root_col_index=1, targets=[(1, 1, "P")])
    apply_pawns_for_enemy(board, proj, special)
    assert target.owner == "E"
    assert target.rank >= 2
