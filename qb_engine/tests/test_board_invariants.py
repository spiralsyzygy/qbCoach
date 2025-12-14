from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine
from qb_engine.game_state import GameState


def test_occupied_tile_not_neutral_after_recompute():
    hydrator = CardHydrator()
    card = hydrator.get_card("001")
    board = BoardState.create_initial_board()
    # Place enemy card on neutral base tile (mid-3) with no pawn deltas; influence is 0
    board.tile_at(1, 2).owner = "E"
    board.tile_at(1, 2).rank = 1
    board.place_card("MID", 3, card, placed_by="E")
    board.recompute_influence_from_deltas()
    assert board.tile_at(1, 2).owner == "E"
    assert board.tile_at(1, 2).rank >= 1
    assert board.tile_at(1, 2).placed_by == "E"


def test_destruction_reveals_underlay_pawns():
    hydrator = CardHydrator()
    effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    board = BoardState.create_initial_board()
    # Add pawn influence for YOU under a future enemy placement
    board.add_pawn_delta_for_you(0, 2, "001", amount=2)
    board.recompute_influence_from_deltas()
    card = hydrator.get_card("020")
    board.place_card("TOP", 3, card, placed_by="E", effect_engine=effect_engine)
    # Destroy the card and recompute; underlay influence should show
    effect_engine._destroy_cards(board, [(0, 2)])
    board.recompute_influence_from_deltas()
    assert board.tile_at(0, 2).card_id is None
    assert board.tile_at(0, 2).owner == "Y"
    assert board.tile_at(0, 2).rank >= 1


def test_get_card_side_prefers_placed_by():
    hydrator = CardHydrator()
    effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    board = BoardState.create_initial_board()
    card = hydrator.get_card("001")
    board.place_card("MID", 3, card, placed_by="Y", effect_engine=effect_engine)
    board.recompute_influence_from_deltas()
    assert board.get_card_side("001") == "Y"
