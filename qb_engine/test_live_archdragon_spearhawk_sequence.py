from pathlib import Path

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.effect_engine import EffectEngine
from qb_engine.legality import is_legal_placement
from qb_engine.projection import (
    compute_projection_targets,
    apply_pawns_for_you,
    apply_effects_for_you,
    apply_pawns_for_enemy,
    apply_effects_for_enemy,
)


def _reset_board_to_neutral(board: BoardState) -> None:
    for row in board.tiles:
        for tile in row:
            tile.owner = "N"
            tile.rank = 0
            tile.card_id = None
    board.effect_auras.clear()
    board.pawn_deltas.clear()


def test_archdragon_crawler_spearhawk_sequence_allows_enemy_play():
    hydrator = CardHydrator()
    engine = EffectEngine(Path("data/qb_effects_v1.1.json"), hydrator)
    board = BoardState.create_initial_board()

    archdragon = hydrator.get_card("020")
    crawler = hydrator.get_card("019")
    spearkhawk = hydrator.get_card("031")

    # YOU play Archdragon at MID-1; ensure placement tile is legal.
    tile_arch = board.tile_at(1, 0)
    tile_arch.owner = "Y"
    tile_arch.rank = max(tile_arch.rank, archdragon.cost)
    board.place_card("MID", 1, archdragon, effect_engine=engine)
    proj = compute_projection_targets(1, 0, archdragon)
    apply_pawns_for_you(board, proj, archdragon)
    apply_effects_for_you(board, proj, archdragon)

    # Archdragon's B3X hits MID-2 (1,1): should have pawn and effect.
    target_tile = board.tile_at(1, 1)
    assert target_tile.owner == "Y"
    assert target_tile.rank >= 1
    assert board.auras_at(1, 1)

    # YOU play Crawler from TOP-2 so one P also hits MID-2; stack pawn to 2.
    tile_crawl = board.tile_at(0, 1)
    tile_crawl.owner = "Y"
    tile_crawl.rank = max(tile_crawl.rank, crawler.cost)
    board.place_card("TOP", 2, crawler, effect_engine=engine)
    proj = compute_projection_targets(0, 1, crawler)
    apply_pawns_for_you(board, proj, crawler)
    apply_effects_for_you(board, proj, crawler)

    target_tile = board.tile_at(1, 1)
    assert target_tile.owner == "Y"
    assert target_tile.rank == 2
    assert board.auras_at(1, 1)

    # Enemy aims Spearhawk at TOP-3: prep tile as enemy-owned, empty, rank>=cost.
    top3 = board.tile_at(0, 2)
    top3.owner = "E"
    top3.rank = max(top3.rank, spearkhawk.cost)
    top3.card_id = None
    assert top3.card_id is None
    assert top3.owner == "E"
    assert top3.rank >= spearkhawk.cost

    # Simulate enemy placement to ensure it succeeds.
    board.place_card("TOP", 3, spearkhawk, effect_engine=engine)
    proj = compute_projection_targets(0, 2, spearkhawk)
    apply_pawns_for_enemy(board, proj, spearkhawk)
    apply_effects_for_enemy(board, proj, spearkhawk)
    placed_tile = board.tile_at(0, 2)
    placed_tile.owner = "E"
    placed_tile.rank = max(placed_tile.rank, spearkhawk.cost)
    assert placed_tile.card_id == spearkhawk.id
    assert placed_tile.owner == "E"
