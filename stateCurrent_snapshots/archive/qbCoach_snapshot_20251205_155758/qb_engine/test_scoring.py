import copy

from qb_engine.board_state import BoardState
from qb_engine.scoring import compute_lane_power, compute_match_score


class StubEffectEngine:
    def __init__(self, power_map=None, coord_map=None):
        self.power_map = power_map or {}
        self.coord_map = coord_map or {}
        self.calls = []

    def compute_effective_power(self, board, lane, col):
        self.calls.append((lane, col))
        if (lane, col) in self.coord_map:
            return self.coord_map[(lane, col)]

        tile = board.tile_at(lane, col)
        if tile.card_id and tile.card_id in self.power_map:
            return self.power_map[tile.card_id]

        return 0


def test_simple_lane_no_effects():
    board = BoardState.create_initial_board()
    tile = board.tile_at(0, 0)
    tile.owner = "Y"
    tile.card_id = "Y001"

    engine = StubEffectEngine(power_map={"Y001": 3})

    lane_score = compute_lane_power(board, engine, 0)
    assert lane_score.power_you == 3
    assert lane_score.power_enemy == 0
    assert lane_score.winner == "Y"
    assert lane_score.lane_points == 3

    match_score = compute_match_score(board, engine)
    assert match_score.total_you == 3
    assert match_score.total_enemy == 0
    assert match_score.winner == "Y"
    assert match_score.margin == 3


def test_effects_change_lane_winner():
    board = BoardState.create_initial_board()

    weak_tile = board.tile_at(0, 1)
    weak_tile.owner = "Y"
    weak_tile.card_id = "Yweak"

    strong_tile = board.tile_at(0, 4)
    strong_tile.owner = "E"
    strong_tile.card_id = "Estr"

    engine = StubEffectEngine(
        power_map={"Yweak": 1, "Estr": 5},
        coord_map={(0, 1): 6, (0, 4): 2},  # effects swing the lane to YOU
    )

    lane_score = compute_lane_power(board, engine, 0)
    assert lane_score.power_you == 6
    assert lane_score.power_enemy == 2
    assert lane_score.winner == "Y"
    assert lane_score.lane_points == 6

    match_score = compute_match_score(board, engine)
    assert match_score.total_you == 6
    assert match_score.total_enemy == 0
    assert match_score.winner == "Y"
    assert match_score.margin == 6


def test_draw_lane_zero_points():
    board = BoardState.create_initial_board()

    you_tile = board.tile_at(1, 0)
    you_tile.owner = "Y"
    you_tile.card_id = "Ydraw"

    enemy_tile = board.tile_at(1, 4)
    enemy_tile.owner = "E"
    enemy_tile.card_id = "Edraw"

    engine = StubEffectEngine(power_map={"Ydraw": 4, "Edraw": 4})

    lane_score = compute_lane_power(board, engine, 1)
    assert lane_score.power_you == 4
    assert lane_score.power_enemy == 4
    assert lane_score.winner is None
    assert lane_score.lane_points == 0

    match_score = compute_match_score(board, engine)
    assert match_score.total_you == 0
    assert match_score.total_enemy == 0
    assert match_score.winner is None
    assert match_score.margin == 0


def test_multi_lane_match_aggregation():
    board = BoardState.create_initial_board()

    board.tile_at(0, 0).card_id = "Y0"
    board.tile_at(0, 0).owner = "Y"
    board.tile_at(0, 4).card_id = "E0"
    board.tile_at(0, 4).owner = "E"

    board.tile_at(1, 0).card_id = "Y1"
    board.tile_at(1, 0).owner = "Y"
    board.tile_at(1, 4).card_id = "E1"
    board.tile_at(1, 4).owner = "E"

    board.tile_at(2, 1).card_id = "Y2"
    board.tile_at(2, 1).owner = "Y"

    engine = StubEffectEngine(
        power_map={
            "Y0": 4,
            "E0": 1,
            "Y1": 2,
            "E1": 5,
            "Y2": 3,
        }
    )

    match_score = compute_match_score(board, engine)

    assert match_score.lanes[0].winner == "Y"
    assert match_score.lanes[0].lane_points == 4
    assert match_score.lanes[1].winner == "E"
    assert match_score.lanes[1].lane_points == 5
    assert match_score.lanes[2].winner == "Y"
    assert match_score.lanes[2].lane_points == 3

    assert match_score.total_you == 7
    assert match_score.total_enemy == 5
    assert match_score.winner == "Y"
    assert match_score.margin == 2


def test_scoring_is_pure_and_non_mutating():
    board = BoardState.create_initial_board()

    board.tile_at(0, 0).card_id = "Ypure"
    board.tile_at(0, 0).owner = "Y"
    board.tile_at(0, 4).card_id = "Epure"
    board.tile_at(0, 4).owner = "E"

    original = copy.deepcopy(board)
    engine = StubEffectEngine(power_map={"Ypure": 2, "Epure": 3})

    _ = compute_match_score(board, engine)

    assert board == original
