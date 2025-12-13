from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qb_engine.card_hydrator import CardHydrator
from qb_engine.card_resolver import CardResolveError, resolve_card_identifier, resolve_cards_from_tokens
from qb_engine.coaching import CoachingEngine
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.enemy_observation import EnemyObservationState
from qb_engine.game_state import GameState
from qb_engine.prediction import PredictionEngine
from qb_engine.scoring import compute_lane_power, compute_match_score

_UX_HYDRATOR = CardHydrator()


class LiveSessionEngineBridge:
    """
    Thin wrapper around the deterministic engine for live-coaching sessions.

    This is the Python-level API that the upcoming CLI will call. It does not
    reimplement any rules; it simply orchestrates engine components and returns
    serializable snapshots.
    """

    def __init__(self, session_mode: str = "live_coaching", coaching_mode: str = "strict") -> None:
        self.session_mode = session_mode
        self.session_id = self._generate_session_id()
        self.enemy_deck_tag: Optional[str] = None
        self.log_path: Optional[Path] = None
        self.phase: str = "YOU_TURN_READY_FOR_REC_OR_PLAY"
        self.turn_counter: int = 1
        self.side_to_act: str = "Y"
        self.coaching_mode: str = self._validate_coaching_mode(coaching_mode)

        # Hydrator is available immediately for card resolution prior to init_match.
        self._hydrator: Optional[CardHydrator] = CardHydrator()
        self._card_index: Dict[str, dict] = self._hydrator.index if self._hydrator else {}

        # Core engine components are initialized in init_match.
        self._effect_engine: Optional[EffectEngine] = None
        self._game_state: Optional[GameState] = None
        self._enemy_obs: Optional[EnemyObservationState] = None
        self._prediction_engine: Optional[PredictionEngine] = None
        self._coaching_engine: Optional[CoachingEngine] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def init_match(
        self,
        you_deck_ids: Optional[List[str]] = None,
        enemy_deck_tag: Optional[str] = None,
        coaching_mode: Optional[str] = None,
    ) -> None:
        """
        Initialize engine components and start a session.

        In this skeleton we fall back to a deterministic deck built from the
        first 15 card IDs in the DB when explicit decks are not provided.
        """
        self.enemy_deck_tag = enemy_deck_tag
        if coaching_mode is not None:
            self.coaching_mode = self._validate_coaching_mode(coaching_mode)
        if self._hydrator is None:
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
        self.phase = "YOU_TURN_READY_FOR_REC_OR_PLAY"
        self.turn_counter = 1
        self.side_to_act = "Y"

    def get_state(self) -> Dict[str, Any]:
        """Return a minimal serializable snapshot for the CLI/logging."""
        if self._game_state is None:
            return {}
        board_repr = self._serialize_board(self._game_state)
        hand_entries = [self._card_summary(cid) for cid in self._game_state.player_hand.as_card_ids()]
        session_info = {
            "mode": self.session_mode,
            "coaching_mode": self.coaching_mode,
            "session_id": self.session_id,
            "turn": self.turn_counter,
            "side_to_act": self.side_to_act,
            "phase": self.phase,
            "enemy_deck_tag": self.enemy_deck_tag,
        }
        effect_tiles = sorted(self._compute_effect_tiles())
        lanes_snapshot, global_snapshot = self._compute_lane_and_global_snapshot()
        return {
            "session": session_info,
            "board": board_repr,
            "you_hand": hand_entries,
            "lanes": lanes_snapshot,
            "global": global_snapshot,
            "engine_output": {},
            "chosen_move": None,
            "effect_tiles": effect_tiles,
        }

    def create_turn_snapshot(
        self,
        engine_output: Optional[Dict[str, Any]] = None,
        chosen_move: Optional[Dict[str, Any]] = None,
        last_event: Optional[str] = None,
    ) -> TurnSnapshot:
        """
        Build a TurnSnapshot from current state plus optional engine_output and chosen_move.
        """
        base = self.get_state()
        base["engine_output"] = engine_output or {}
        base["chosen_move"] = chosen_move
        base["last_event"] = last_event
        return base

    def mulligan_output(self) -> Dict[str, Any]:
        """Return a simple mulligan payload for the current hand (placeholder evaluator)."""
        if not self._game_state:
            raise RuntimeError("Session not initialized.")
        hand_ids = self._game_state.player_hand.as_card_ids()
        return {
            "mulligan": {
                "hand_ids": hand_ids,
                "hand": [self._card_summary(cid) for cid in hand_ids],
                "note": "Mulligan evaluation not implemented; hand is authoritative input.",
            }
        }

    def sync_you_hand_from_ids(self, card_ids: List[str]) -> None:
        if not self._game_state:
            raise RuntimeError("Session not initialized.")
        self._game_state.player_hand.sync_from_ids(card_ids)
        # After a full-hand sync, keep phase unchanged but ensure side metadata reflects current state.
        self.side_to_act = self._game_state.side_to_act

    def resolve_card_id(self, identifier: str) -> str:
        """
        Resolve either a card_id or a case-insensitive card name to a canonical card_id.
        Raises ValueError on unknown or ambiguous identifiers.
        """
        try:
            return resolve_card_identifier(identifier).id
        except CardResolveError as exc:
            raise ValueError(str(exc)) from exc

    def resolve_cards_from_tokens(self, tokens: List[str]) -> List[str]:
        """Resolve a list of raw tokens to canonical card ids."""
        try:
            return [card.id for card in resolve_cards_from_tokens(tokens)]
        except CardResolveError as exc:
            raise ValueError(str(exc)) from exc

    def apply_draw(self, card_id: str) -> None:
        if not self._game_state or not self._hydrator:
            raise RuntimeError("Session not initialized.")
        if self.phase != "YOU_TURN_AWAITING_DRAW":
            raise ValueError("Cannot draw now; wait for the start of your turn.")
        self._game_state.player_hand.add_card(card_id)
        self.phase = "YOU_TURN_READY_FOR_REC_OR_PLAY"

    def register_enemy_play(self, card_id: str, row: int, col: int) -> None:
        """
        Mirror an enemy play onto the board. This is a placeholder that should
        eventually mirror the live-coaching enemy play semantics.
        """
        if not self._game_state or not self._hydrator:
            raise RuntimeError("Session not initialized.")
        if self.phase != "ENEMY_TURN_AWAITING_PLAY":
            raise ValueError("Not enemy turn; cannot register enemy play now.")
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
        # Enemy turn complete -> back to YOU draw phase
        self._game_state.side_to_act = "Y"
        self.side_to_act = "Y"
        self.phase = "YOU_TURN_AWAITING_DRAW"
        self.turn_counter += 1

    def apply_you_move(self, card_id: str, row: int, col: int) -> Dict[str, Any]:
        """
        Apply a YOU move. Skeleton implementation wires to play_card_from_hand
        after locating the card in hand.
        """
        if not self._game_state:
            raise RuntimeError("Session not initialized.")
        if self.phase == "YOU_TURN_AWAITING_DRAW":
            raise ValueError("You must sync your draw before playing.")
        if self.phase == "ENEMY_TURN_AWAITING_PLAY":
            raise ValueError("It is currently the enemy's turn.")

        try:
            hand_index = self._game_state.player_hand.as_card_ids().index(card_id)
        except ValueError as exc:
            raise ValueError(f"Card id {card_id} not found in hand.") from exc

        self._game_state.play_card_from_hand("Y", hand_index, row, col)
        self._game_state.side_to_act = "E"
        self.side_to_act = "E"
        self.phase = "ENEMY_TURN_AWAITING_PLAY"
        return self.get_state()

    def pass_you_turn(self) -> Dict[str, Any]:
        """
        Skip your turn and hand control to the enemy.
        """
        if not self._game_state:
            raise RuntimeError("Session not initialized.")
        if self.phase == "ENEMY_TURN_AWAITING_PLAY":
            raise ValueError("It is currently the enemy's turn.")
        # Advance underlying state
        self._game_state.pass_turn()
        self.side_to_act = self._game_state.side_to_act
        self.turn_counter = self._game_state.turn
        self.phase = "ENEMY_TURN_AWAITING_PLAY" if self.side_to_act == "E" else self.phase
        return self.get_state()

    def recommend_moves(self, top_n: int = 3) -> List[Dict[str, Any]]:
        if not self._coaching_engine or not self._game_state or not self._enemy_obs:
            raise RuntimeError("Session not initialized.")
        if self.phase == "YOU_TURN_AWAITING_DRAW":
            raise ValueError("You must draw before requesting recommendations.")
        if self.phase == "ENEMY_TURN_AWAITING_PLAY":
            raise ValueError("It is currently the enemy's turn.")
        rec = self._coaching_engine.recommend_moves(self._game_state, self._enemy_obs, top_n=top_n)
        moves: List[Dict[str, Any]] = []
        for mv in rec.moves:
            moves.append(self._enrich_move_recommendation(mv))
        return moves

    def legal_moves(self) -> List[Dict[str, Any]]:
        if not self._coaching_engine or not self._game_state:
            raise RuntimeError("Session not initialized.")
        candidates = self._coaching_engine.enumerate_you_moves(self._game_state)
        moves = [
            {
                "card_id": mc.card_id,
                "hand_index": mc.hand_index,
                "lane_index": mc.lane_index,
                "col_index": mc.col_index,
            }
            for mc in candidates
        ]
        moves.append({"card_id": "_PASS_", "action": "PASS"})
        return moves

    def get_prediction(self) -> Dict[str, Any]:
        if not self._prediction_engine or not self._game_state or not self._enemy_obs:
            raise RuntimeError("Session not initialized.")
        threat_map = self._prediction_engine.full_enemy_prediction(self._game_state, self._enemy_obs)
        lane_pressure = {str(k): v for k, v in threat_map.lane_pressure.items()}
        tile_pressure = {f"{k[0]},{k[1]}": v for k, v in threat_map.tile_pressure.items()}
        return {
            "best_enemy_score": threat_map.best_enemy_score,
            "expected_enemy_score": threat_map.expected_enemy_score,
            "lane_pressure": lane_pressure,
            "tile_pressure": tile_pressure,
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
            for col_idx, _ in enumerate(row):
                desc = state.board.describe_tile(lane_idx, col_idx)
                cid = desc.get("card_id")
                if cid and self._hydrator:
                    try:
                        desc["card_name"] = self._hydrator.get_card(cid).name
                    except KeyError:
                        pass
                lane.append(desc)
            board_rows.append(lane)
        return board_rows

    def _compute_effect_tiles(self) -> set[tuple[int, int]]:
        if not self._game_state:
            return set()
        positions: set[tuple[int, int]] = set()
        for aura in self._game_state.board.effect_auras:
            positions.add((aura.lane_index, aura.col_index))
        for pos in self._game_state.board.direct_effects.keys():
            positions.add(pos)
        return positions

    def _compute_lane_and_global_snapshot(self) -> tuple[Dict[str, Dict[str, int]], Dict[str, Optional[float]]]:
        if not self._game_state or not self._effect_engine:
            return {}, {}
        lanes: Dict[str, Dict[str, int]] = {}
        for lane_idx, name in enumerate(["top", "mid", "bot"]):
            lane_score = compute_lane_power(self._game_state.board, self._effect_engine, lane_idx)
            lanes[name] = {
                "you_power": lane_score.power_you,
                "enemy_power": lane_score.power_enemy,
                "net_power": lane_score.power_you - lane_score.power_enemy,
            }
        match_score = compute_match_score(self._game_state.board, self._effect_engine)
        global_info: Dict[str, Optional[float]] = {
            "you_score_estimate": float(match_score.total_you),
            "enemy_score_estimate": float(match_score.total_enemy),
            "win_expectancy": None,
        }
        return lanes, global_info

    @staticmethod
    def _generate_session_id() -> str:
        return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S")

    def _card_summary(self, card_id: str) -> Dict[str, str]:
        entry: Dict[str, str] = {"id": card_id}
        if self._hydrator:
            try:
                entry["name"] = self._hydrator.get_card(card_id).name
            except KeyError:
                pass
        return entry

    def _ensure_log_path(self) -> Path:
        """
        Ensure a log path exists for this session, creating directories if needed.
        """
        if self.log_path:
            return self.log_path
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        safe_tag = (self.enemy_deck_tag or "").replace(" ", "_") if self.enemy_deck_tag else ""
        filename = f"{timestamp}_live"
        if safe_tag:
            filename += f"_{safe_tag}"
        filename += ".jsonl"
        logs_dir = Path("logs/live")
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = logs_dir / filename
        return self.log_path

    @staticmethod
    def _validate_coaching_mode(mode: str) -> str:
        mode_norm = mode.strip().lower()
        if mode_norm not in {"strict", "strategy", "reflective"}:
            raise ValueError("coaching_mode must be 'strict', 'strategy', or 'reflective'.")
        return mode_norm

    def append_turn_snapshot(self, snapshot: TurnSnapshot) -> None:
        """
        Append a TurnSnapshot as a JSON line to the session log file.
        """
        path = self._ensure_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot))
            f.write(os.linesep)

    def _lane_name_from_index(self, idx: int) -> str:
        return ["top", "mid", "bot"][idx] if 0 <= idx <= 2 else str(idx)

    def _enrich_move_recommendation(self, mv: Any) -> Dict[str, Any]:
        """
        Convert a MoveEvaluation into a GPT-facing enriched recommendation entry.
        """
        mc = mv.move
        move = {
            "card_id": mc.card_id,
            "hand_index": mc.hand_index,
            "lane_index": mc.lane_index,
            "col_index": mc.col_index,
            "lane": self._lane_name_from_index(mc.lane_index),
            "col": mc.col_index + 1,
            "side": "you",
        }
        if self._hydrator:
            try:
                move["card_name"] = self._hydrator.get_card(mc.card_id).name
            except KeyError:
                pass

        lane_delta, projection_summary = self._compute_move_projection_summary(mc)
        move_strength = mv.you_margin_after_enemy_best if hasattr(mv, "you_margin_after_enemy_best") else 0.0

        return {
            "move": move,
            "move_strength": move_strength,
            "lane_delta": lane_delta,
            "projection_summary": projection_summary,
            "you_margin_after_move": mv.you_margin_after_move,
            "you_margin_after_enemy_best": mv.you_margin_after_enemy_best,
            "you_margin_after_enemy_expected": mv.you_margin_after_enemy_expected,
            "quality_rank": mv.quality_rank,
            "quality_label": mv.quality_label,
            "explanation_tags": mv.explanation_tags,
            "explanation_lines": mv.explanation_lines,
        }

    def _compute_move_projection_summary(self, mc: Any) -> Tuple[Dict[str, int], Dict[str, Any]]:
        """
        Simulate a candidate move on a cloned GameState to derive lane deltas
        and a projection summary of tile-level changes.
        """
        if not self._game_state or not self._effect_engine:
            return {}, {"tile_deltas": []}
        before = self._snapshot_board_state()
        lane_before = self._lane_power_snapshot()

        gs_clone = self._game_state.clone()
        gs_clone.side_to_act = "Y"
        try:
            gs_clone.play_card_from_hand("Y", mc.hand_index, mc.lane_index, mc.col_index)
        except Exception:
            return {}, {"tile_deltas": []}

        lane_after = self._lane_power_snapshot(gs_clone)
        lane_delta = {name: lane_after[name] - lane_before[name] for name in lane_before.keys()}

        after_snapshot = self._snapshot_board_state(gs_clone)
        tile_deltas: List[Dict[str, Any]] = []
        effect_before = self._effect_positions_from_board(before["effect_positions"])
        effect_after = self._effect_positions_from_board(after_snapshot["effect_positions"])
        for pos, before_tile in before["tiles"].items():
            after_tile = after_snapshot["tiles"].get(pos)
            if after_tile is None:
                continue
            changed = (
                before_tile["owner"] != after_tile["owner"]
                or before_tile["rank"] != after_tile["rank"]
                or before_tile.get("card_id") != after_tile.get("card_id")
                or ((pos in effect_before) != (pos in effect_after))
            )
            if not changed:
                continue
            tile_delta: Dict[str, Any] = {
                "row": self._lane_name_from_index(pos[0]),
                "col": pos[1] + 1,
                "owner_before": before_tile["owner"],
                "owner_after": after_tile["owner"],
                "rank_before": before_tile["rank"],
                "rank_after": after_tile["rank"],
                "card_before": before_tile.get("card_id"),
                "card_after": after_tile.get("card_id"),
                "effects_added": [] if (pos in effect_before) and (pos in effect_after) else [],
                "effects_removed": [],
            }
            if pos not in effect_before and pos in effect_after:
                tile_delta["effects_added"] = ["effect_present"]
            if pos in effect_before and pos not in effect_after:
                tile_delta["effects_removed"] = ["effect_removed"]
            tile_deltas.append(tile_delta)

        return lane_delta, {"tile_deltas": tile_deltas}

    def _lane_power_snapshot(self, gs: Optional[GameState] = None) -> Dict[str, int]:
        if gs is None:
            gs = self._game_state
        assert gs is not None and self._effect_engine is not None
        snapshot: Dict[str, int] = {}
        for lane_idx, name in enumerate(["top", "mid", "bot"]):
            lane_score = compute_lane_power(gs.board, self._effect_engine, lane_idx)
            snapshot[name] = lane_score.power_you - lane_score.power_enemy
        return snapshot

    def _snapshot_board_state(self, gs: Optional[GameState] = None) -> Dict[str, Any]:
        if gs is None:
            gs = self._game_state
        assert gs is not None
        tiles: Dict[Tuple[int, int], Dict[str, Any]] = {}
        effect_positions = set()
        for aura in gs.board.effect_auras:
            effect_positions.add((aura.lane_index, aura.col_index))
        for pos in gs.board.direct_effects.keys():
            effect_positions.add(pos)
        for lane_idx, row in enumerate(gs.board.tiles):
            for col_idx, tile in enumerate(row):
                tiles[(lane_idx, col_idx)] = {
                    "owner": tile.owner,
                    "rank": tile.rank,
                    "card_id": tile.card_id,
                }
        return {"tiles": tiles, "effect_positions": effect_positions}

    @staticmethod
    def _effect_positions_from_board(effect_positions: set[tuple[int, int]]) -> set[tuple[int, int]]:
        return set(effect_positions)


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
    coaching_mode = session.get("coaching_mode", "strict")
    lines.append(f"coaching_mode: {coaching_mode}")
    lines.append(f"session_id: {session.get('session_id', '')}")
    lines.append(f"turn: {session.get('turn', '')}")
    lines.append(f"side_to_act: {session.get('side_to_act', '')}")
    phase = session.get("phase")
    if phase:
        lines.append(f"phase: {phase}")
    enemy_tag = session.get("enemy_deck_tag")
    if enemy_tag is not None:
        lines.append(f"enemy_deck_tag: {enemy_tag}")
    lines.append("")

    # BOARD
    lines.append("[BOARD]")
    board = snapshot.get("board", [])
    effect_tiles = set()
    for pos in snapshot.get("effect_tiles", []):
        try:
            lane_idx, col_idx = pos
            effect_tiles.add((lane_idx, col_idx))
        except Exception:
            continue
    header = "      1        2        3        4        5"
    lines.append(header)
    row_labels = ["Top", "Mid", "Bot"]
    for row_idx, row in enumerate(board):
        cells: List[str] = []
        for col_idx, tile in enumerate(row):
            owner = tile.get("owner", "?")
            rank = tile.get("rank", 0)
            card_id = tile.get("card_id")
            if card_id:
                token = f"[{owner}{rank}:{card_id}]"
            else:
                token = f"[{owner}{rank}]"
            if (row_idx, col_idx) in effect_tiles:
                if token.endswith("]"):
                    token = token[:-1] + "★]"
            cells.append(token)
        lines.append(f"{row_labels[row_idx]:<4} " + " ".join(f"{c:<8}" for c in cells))
    lines.append("")

    # YOU_HAND
    lines.append("[YOU_HAND]")
    hand = snapshot.get("you_hand", [])
    if hand and isinstance(hand[0], dict):
        cards_formatted = ", ".join(f"{c.get('name','')}({c.get('id','')})".strip() for c in hand)
    else:
        cards_formatted = ", ".join(str(x) for x in hand)
    lines.append(f"cards: [{cards_formatted}]")
    lines.append("")

    # ENGINE_OUTPUT
    lines.append("[ENGINE_OUTPUT]")
    engine_output = snapshot.get("engine_output", {})
    mull = engine_output.get("mulligan")
    if mull:
        lines.append("mulligan:")
        hand_ids = mull.get("hand_ids", [])
        note = mull.get("note")
        lines.append(f"- hand_ids: {', '.join(hand_ids)}")
        if note:
            lines.append(f"- note: {note}")
    recs = engine_output.get("recommend_moves", [])
    if recs:
        lines.append("recommend_moves:")
        for idx, rec in enumerate(recs, start=1):
            move = rec.get("move", {})
            cid = move.get("card_id", "")
            cname = ""
            if cid:
                if "card_name" in move:
                    cname = move.get("card_name", "")
                else:
                    try:
                        cname = _UX_HYDRATOR.get_card(cid).name
                    except KeyError:
                        cname = ""
            lane = move.get("lane_index", "")
            col = move.get("col_index", "")
            margin = rec.get("you_margin_after_move") or rec.get("expected_margin", "")
            label = f"{cid}"
            if cname:
                label = f"{cname} ({cid})"
            lines.append(f"- {idx}) {label} @ lane {lane}, col {col} | margin {margin}")
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
