import json
import os

from qb_engine.board_state import BoardState
from qb_engine.interface_layer import BoardContext


def load_db() -> dict:
    path = "data/qb_DB_Complete_v2.json"
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {c["id"]: c for c in json.load(f) if isinstance(c, dict) and "id" in c}
    except Exception:
        return {}


def main() -> None:
    print("--- qbCoach Interface Test (With Recommendations) ---")
    card_db = load_db()
    board = BoardState.create_initial_board()

    # Mock engine data
    mock_lanes = {"top": {"you_power": 0, "enemy_power": 0, "net_power": 0}}
    mock_hand = [{"name": "Security Officer"}]

    # Mock Engine Output (with explanation tags)
    mock_engine_out = {
        "recommend_moves": [
            {
                "move": {"card_name": "Security Officer", "lane_index": 1, "col_index": 1},
                "you_margin_after_move": 4.0,
                "explanation_tags": ["tempo_pawn_flip", "secures_territory"],
            }
        ]
    }

    ctx = BoardContext.from_engine(board, card_db, mock_lanes, mock_hand, mock_engine_out)

    print(f"\n{ctx.score_state}")
    print("\nLANES:")
    for l in ctx.lane_summaries:
        print(f"  {l}")

    print("\nRECOMMENDATION:")
    print(f"  {ctx.top_recommendation}")
    # Expect: PLAY Security Officer AT [mid 2]. [Strategy: tempo_pawn_flip, secures_territory]


if __name__ == "__main__":
    main()
