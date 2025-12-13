from qb_engine.board_state import BoardState
from qb_engine.legality import is_legal_placement
from qb_engine.models import Card
from qb_engine.live_session import format_turn_snapshot_for_ux


def _dummy_card(cost: int = 1) -> Card:
    return Card(
        id="DUMMY",
        name="Dummy",
        category="Test",
        cost=cost,
        power=0,
        pattern="",
        grid=[["."] * 5 for _ in range(5)],
    )


def _snapshot_board(board: BoardState):
    return [[board.describe_tile(r, c) for c in range(5)] for r in range(3)]


def test_legality_matches_rendered_board_simple():
    board = BoardState.create_initial_board()
    # Make MID-3 a legal YOU tile (owner Y, rank 2, empty)
    tile = board.tile_at(1, 2)
    tile.owner = "Y"
    tile.rank = 2
    tile.card_id = None

    snap = {
        "session": {"mode": "test", "session_id": "s", "turn": 1, "side_to_act": "Y"},
        "board": _snapshot_board(board),
        "you_hand": [],
        "engine_output": {},
        "effect_tiles": [],
    }
    rendered = format_turn_snapshot_for_ux(snap)
    assert "[Y2]" in rendered

    card = _dummy_card(cost=2)
    assert is_legal_placement(board, 1, 2, card) is True

    # Now mark insufficient rank
    tile.rank = 1
    assert is_legal_placement(board, 1, 2, card) is False

    # Occupied should be illegal
    tile.rank = 2
    tile.card_id = "OCC"
    assert is_legal_placement(board, 1, 2, card) is False


def test_enemy_tile_consistency():
    board = BoardState.create_initial_board()
    # Enemy tile should be illegal for YOU even if rank high
    tile = board.tile_at(0, 4)
    tile.owner = "E"
    tile.rank = 3
    tile.card_id = None

    card = _dummy_card(cost=1)
    assert is_legal_placement(board, 0, 4, card) is False
