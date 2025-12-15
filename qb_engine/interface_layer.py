from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from qb_engine.board_state import BoardState


class CoordinateTranslator:
    """
    Standardizes communication between engine (0-based) and LLM-facing (1-based) coordinates.
    Internal: (row=0, col=0)
    External: "[top 1]"
    """

    LANE_MAP = {0: "top", 1: "mid", 2: "bot"}

    @staticmethod
    def engine_to_human(row: int, col: int) -> str:
        """Converts (0, 0) -> "[top 1]"."""
        lane = CoordinateTranslator.LANE_MAP.get(row, "unknown")
        return f"[{lane} {col + 1}]"


@dataclass
class BoardContext:
    """
    Semantic snapshot for the LLM. Strictly uses [lane col] notation.
    """

    score_state: str
    lane_summaries: List[str]
    threats: List[str]
    opportunities: List[str]
    hand_summary: List[str]
    top_recommendation: str

    @staticmethod
    def from_engine(
        board: BoardState,
        card_db: Dict[str, Any],
        lanes_data: Dict[str, Any],
        hand_data: List[Dict[str, Any]],
        engine_output: Optional[Dict[str, Any]] = None,
    ) -> "BoardContext":
        # 1) Summarize lanes
        summaries: List[str] = []
        total_net = 0
        for lane_idx in [0, 1, 2]:
            lane_name = CoordinateTranslator.LANE_MAP[lane_idx]
            stats = lanes_data.get(lane_name, {"you_power": 0, "enemy_power": 0, "net_power": 0})
            y = stats.get("you_power", 0)
            e = stats.get("enemy_power", 0)
            net = stats.get("net_power", 0)
            total_net += net
            status = "WINNING" if net > 0 else "LOSING" if net < 0 else "TIED"
            summaries.append(f"{lane_name.upper()}: {status} ({y} vs {e})")

        # 2) Scan board for threats/opportunities
        threats: List[str] = []
        opportunities: List[str] = []
        for r_idx, row in enumerate(board.tiles):
            for c_idx, tile in enumerate(row):
                pos = CoordinateTranslator.engine_to_human(r_idx, c_idx)
                if tile.owner == "E" and tile.card_id:
                    cname = tile.card_id
                    if card_db and tile.card_id in card_db:
                        cname = card_db[tile.card_id].get("name", tile.card_id)
                    threats.append(f"Enemy {cname} at {pos}")
                if tile.owner == "Y" and tile.card_id is None:
                    opportunities.append(f"Open slot at {pos} (Rank {tile.rank})")

        # 3) Hand summary
        hand = [c.get("name", c.get("id", "Unknown")) for c in hand_data]

        # 4) Parse recommendation (top move + tags)
        rec_str = "No recommendation available."
        if engine_output and "recommend_moves" in engine_output:
            recs = engine_output.get("recommend_moves") or []
            if recs:
                top = recs[0]
                move = top.get("move", {})
                card_name = move.get("card_name") or move.get("card_id") or "Unknown card"
                pos = CoordinateTranslator.engine_to_human(
                    move.get("lane_index", 0), move.get("col_index", 0)
                )
                tags = top.get("explanation_tags") or []
                tag_str = ", ".join(tags) if tags else "Standard Play"
                rec_str = f"PLAY {card_name} AT {pos}. [Strategy: {tag_str}]"

        # 4) Score state
        status_str = "AHEAD" if total_net > 0 else "BEHIND" if total_net < 0 else "EVEN"

        return BoardContext(
            score_state=f"You are {status_str} by {abs(total_net)} points.",
            lane_summaries=summaries,
            threats=threats,
            opportunities=opportunities,
            hand_summary=hand,
            top_recommendation=rec_str,
        )
