from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from qb_engine.card_hydrator import CardHydrator
from qb_engine.coaching import CoachingEngine
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.enemy_observation import EnemyObservationState
from qb_engine.game_state import GameState
from qb_engine.prediction import PredictionEngine


class LiveSessionEngineBridge:
    """
    Thin wrapper around the deterministic engine for live-coaching sessions.

    This is the Python-level API that the upcoming CLI will call. It does not
    reimplement any rules; it simply orchestrates engine components and returns
    serializable snapshots.
    """

    def __init__(self, session_mode: str = "live_coaching") -> None:
        self.session_mode = session_mode
        self.session_id = self._generate_session_id()
        self.enemy_deck_tag: Optional[str] = None
        self.log_path: Optional[Path] = None

        # Core engine components are initialized in init_match.
        self._hydrator: Optional[CardHydrator] = None
        self._effect_engine: Optional[EffectEngine] = None
        self._game_state: Optional[GameState] = None
        self._enemy_obs: Optional[EnemyObservationState] = None
        self._prediction_engine: Optional[PredictionEngine] = None
        self._coaching_engine: Optional[CoachingEngine] = None
        self._card_index: Dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def init_match(
        self,
        you_deck_ids: Optional[List[str]] = None,
        enemy_deck_tag: Optional[str] = None,
    ) -> None:
        """
        Initialize engine components and start a session.

        In this skeleton we fall back to a deterministic deck built from the
        first 15 card IDs in the DB when explicit decks are not provided.
        """
        self.enemy_deck_tag = enemy_deck_tag
        self._hydrator = CardHydrator()
        self._card_index = self._hydrator.index
        self._effect_engine = EffectEngine(Path("data/qb_effects_v1.1.json"), self._hydrator)

        default_ids = self._default_deck_ids()
        player_ids = you_deck_ids or default_ids
        enemy_ids = default_ids

        player_deck = Deck(player_ids)
        enemy_deck = Deck(enemy_ids)

        self._game_state = GameState(
            player_deck=player_deck,
            enemy_deck=enemy_deck,
            hydrator=self._hydrator,
            effect_engine=self._effect_engine,
        )
        self._enemy_obs = EnemyObservationState()
        self._prediction_engine = PredictionEngine(hydrator=self._hydrator, effect_engine=self._effect_engine)
        self._coaching_engine = CoachingEngine(hydrator=self._hydrator, prediction_engine=self._prediction_engine)

    def get_state(self) -> Dict[str, Any]:
        """Return a minimal serializable snapshot for the CLI/logging."""
        if self._game_state is None:
            return {}
        board_repr = self._serialize_board(self._game_state)
        hand_ids = self._game_state.player_hand.as_card_ids()
        session_info = {
            "mode": self.session_mode,
            "session_id": self.session_id,
            "turn": self._game_state.turn,
            "side_to_act": self._game_state.side_to_act,
            "enemy_deck_tag": self.enemy_deck_tag,
        }
        return {
            "session": session_info,
            "board": board_repr,
            "you_hand": hand_ids,
            "engine_output": {},
            "chosen_move": None,
        }

    def create_turn_snapshot(
        self,
        engine_output: Optional[Dict[str, Any]] = None,
        chosen_move: Optional[Dict[str, Any]] = None,
    ) -> TurnSnapshot:
        """
        Build a TurnSnapshot from current state plus optional engine_output and chosen_move.
        """
        base = self.get_state()
        base["engine_output"] = engine_output or {}
        base["chosen_move"] = chosen_move
        return base

    def sync_you_hand_from_ids(self, card_ids: List[str]) -> None:
        if not self._game_state:
            raise RuntimeError("Session not initialized.")
        self._game_state.player_hand.sync_from_ids(card_ids)

    def resolve_card_id(self, identifier: str) -> str:
        """
        Resolve either a card_id or a case-insensitive card name to a canonical card_id.
        Raises ValueError on unknown or ambiguous identifiers.
        """
        if not self._card_index:
            raise RuntimeError("Session not initialized.")

        cleaned = identifier.strip().strip('"').strip("'")
        if cleaned in self._card_index:
            return cleaned

        # Case-insensitive name lookup
        lowered = cleaned.lower()
        matches = [
            card_id
            for card_id, entry in self._card_index.items()
            if isinstance(entry, dict)
            and entry.get("name", "").lower() == lowered
        ]
        if not matches:
            raise ValueError(f"Unknown card identifier '{identifier}'.")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous card identifier '{identifier}'. Matches: {matches}")
        return matches[0]

    def register_enemy_play(self, card_id: str, row: int, col: int) -> None:
        """
        Mirror an enemy play onto the board. This is a placeholder that should
        eventually mirror the live-coaching enemy play semantics.
        """
        if not self._game_state or not self._hydrator:
            raise RuntimeError("Session not initialized.")
        tile = self._game_state.board.tile_at(row, col)
        card = self._hydrator.get_card(card_id)
        if tile.card_id is not None or tile.owner != "E" or tile.rank < card.cost:
            raise ValueError("Illegal enemy placement.")

        # Temporarily set side_to_act to enemy to reuse play_card_from_hand logic.
        original_side = self._game_state.side_to_act
        self._game_state.side_to_act = "E"
        try:
            self._game_state.enemy_hand.add_card(card_id)
            hand_idx = len(self._game_state.enemy_hand.cards) - 1
            self._game_state.play_card_from_hand("E", hand_idx, row, col)
        finally:
            self._game_state.side_to_act = original_side

    def apply_you_move(self, card_id: str, row: int, col: int) -> Dict[str, Any]:
        """
        Apply a YOU move. Skeleton implementation wires to play_card_from_hand
        after locating the card in hand.
        """
        if not self._game_state:
            raise RuntimeError("Session not initialized.")

        try:
            hand_index = self._game_state.player_hand.as_card_ids().index(card_id)
        except ValueError as exc:
            raise ValueError(f"Card id {card_id} not found in hand.") from exc

        self._game_state.play_card_from_hand("Y", hand_index, row, col)
        return self.get_state()

    def recommend_moves(self, top_n: int = 3) -> List[Dict[str, Any]]:
        if not self._coaching_engine or not self._game_state or not self._enemy_obs:
            raise RuntimeError("Session not initialized.")
        rec = self._coaching_engine.recommend_moves(self._game_state, self._enemy_obs, top_n=top_n)
        # Basic serialization of move recommendations
        return [
            {
                "move": {
                    "card_id": move.card.id,
                    "lane_index": move.lane,
                    "col_index": move.col,
                },
                "expected_margin": move.expected_margin,
            }
            for move in rec.moves
        ]

    def get_prediction(self) -> Dict[str, Any]:
        if not self._prediction_engine or not self._game_state or not self._enemy_obs:
            raise RuntimeError("Session not initialized.")
        threat_map = self._prediction_engine.full_enemy_prediction(self._game_state, self._enemy_obs)
        return {
            "best_enemy_score": threat_map.best_enemy_score,
            "expected_enemy_score": threat_map.expected_enemy_score,
            "lane_pressure": threat_map.lane_pressure,
            "tile_pressure": threat_map.tile_pressure,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _default_deck_ids(self) -> List[str]:
        assert self._hydrator is not None
        ids = [cid for cid in sorted(self._hydrator.index.keys()) if cid != "_meta"]
        return ids[:15]

    def _serialize_board(self, state: GameState) -> List[List[Dict[str, Any]]]:
        board_rows: List[List[Dict[str, Any]]] = []
        for lane_idx, row in enumerate(state.board.tiles):
            lane: List[Dict[str, Any]] = []
            for col_idx, tile in enumerate(row):
                lane.append(
                    {
                        "lane": lane_idx,
                        "col": col_idx,
                        "owner": tile.owner,
                        "rank": tile.rank,
                        "card_id": tile.card_id,
                    }
                )
            board_rows.append(lane)
        return board_rows

    @staticmethod
    def _generate_session_id() -> str:
        return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    def _ensure_log_path(self) -> Path:
        """
        Ensure a log path exists for this session, creating directories if needed.
        """
        if self.log_path:
            return self.log_path
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_tag = (self.enemy_deck_tag or "").replace(" ", "_") if self.enemy_deck_tag else ""
        filename = f"{timestamp}_live"
        if safe_tag:
            filename += f"_{safe_tag}"
        filename += ".jsonl"
        logs_dir = Path("logs/live")
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = logs_dir / filename
        return self.log_path

    def append_turn_snapshot(self, snapshot: TurnSnapshot) -> None:
        """
        Append a TurnSnapshot as a JSON line to the session log file.
        """
        path = self._ensure_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot))
            f.write(os.linesep)


TurnSnapshot = Dict[str, Any]


def format_turn_snapshot_for_ux(snapshot: TurnSnapshot) -> str:
    """
    Render the `[SESSION]`, `[BOARD]`, `[YOU_HAND]`, `[ENGINE_OUTPUT]` block.
    This is a best-effort formatter; it only displays fields present in the snapshot.
    """
    lines: List[str] = []

    # SESSION
    session = snapshot.get("session", {})
    lines.append("[SESSION]")
    lines.append(f"mode: {session.get('mode', '')}")
    lines.append(f"session_id: {session.get('session_id', '')}")
    lines.append(f"turn: {session.get('turn', '')}")
    lines.append(f"side_to_act: {session.get('side_to_act', '')}")
    enemy_tag = session.get("enemy_deck_tag")
    if enemy_tag is not None:
        lines.append(f"enemy_deck_tag: {enemy_tag}")
    lines.append("")

    # BOARD
    lines.append("[BOARD]")
    board = snapshot.get("board", [])
    header = "      1        2        3        4        5"
    lines.append(header)
    row_labels = ["Top", "Mid", "Bot"]
    for row_idx, row in enumerate(board):
        cells: List[str] = []
        for tile in row:
            owner = tile.get("owner", "?")
            rank = tile.get("rank", 0)
            card_id = tile.get("card_id")
            if card_id:
                cells.append(f"[{owner}{rank}:{card_id}]")
            else:
                cells.append(f"[{owner}{rank}]")
        lines.append(f"{row_labels[row_idx]:<4} " + " ".join(f"{c:<8}" for c in cells))
    lines.append("")

    # YOU_HAND
    lines.append("[YOU_HAND]")
    hand = snapshot.get("you_hand", [])
    lines.append(f"card_ids: [{', '.join(hand)}]")
    lines.append("")

    # ENGINE_OUTPUT
    lines.append("[ENGINE_OUTPUT]")
    engine_output = snapshot.get("engine_output", {})
    recs = engine_output.get("recommend_moves", [])
    if recs:
        lines.append("recommend_moves:")
        for idx, rec in enumerate(recs, start=1):
            move = rec.get("move", {})
            cid = move.get("card_id", "")
            lane = move.get("lane_index", "")
            col = move.get("col_index", "")
            margin = rec.get("you_margin_after_move") or rec.get("expected_margin", "")
            lines.append(f"- {idx}) {cid} @ lane {lane}, col {col} | margin {margin}")
    pred = engine_output.get("prediction", {})
    if pred:
        lines.append("prediction:")
        best = pred.get("expected_final_margin_best_line") or pred.get("best_enemy_score")
        if best is not None:
            lines.append(f"- expected_final_margin_best_line: {best}")
        lane_summary = pred.get("lane_summary")
        if lane_summary:
            lines.append("- lane_summary:")
            for lane_name, val in lane_summary.items():
                lines.append(f"  {lane_name.upper()}: {val}")

    return "\n".join(lines)
