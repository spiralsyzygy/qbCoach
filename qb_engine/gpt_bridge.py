from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from qb_engine.board_state import BoardState
from qb_engine.card_hydrator import CardHydrator
from qb_engine.deck import Deck
from qb_engine.effect_engine import EffectEngine
from qb_engine.enemy_observation import EnemyObservation, EnemyObservationState
from qb_engine.game_state import GameState
from qb_engine.legality import is_legal_placement
from qb_engine.prediction import PredictionEngine
from qb_engine.coaching import CoachingEngine, CoachingRecommendation, MoveEvaluation, PositionEvaluation, LaneStatus
from qb_engine.scoring import MatchScore, LaneScore, compute_match_score


@dataclass
class BridgeSession:
    game_state: GameState
    enemy_obs: EnemyObservation
    scoring_engine: Any
    prediction_engine: Any
    coaching_engine: Any
    metadata: Dict[str, Any]
    session_mode: str


class EngineBridge:
    def __init__(self, card_db: Any):
        """
        card_db: already-loaded card DB (from qb_DB_Complete_v2.json). Stored for future use.
        """
        self._card_db = card_db
        self._sessions: Dict[str, BridgeSession] = {}

    # ------------------------------------------------------------------ #
    # Public entrypoint
    # ------------------------------------------------------------------ #
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        session_id = request.get("session_id")
        op = request.get("op")
        payload = request.get("payload", {}) or {}

        if not session_id or not op:
            return self._error_response(session_id, "BadRequest", "session_id and op are required.")

        if op == "init_match":
            return self._op_init_match(session_id, payload)

        # All other ops require an existing session
        session = self._sessions.get(session_id)
        if session is None:
            return self._error_response(session_id, "InvalidSession", f"Unknown session_id '{session_id}'.")

        if op == "get_state":
            return self._op_get_state(session_id, session)

        if op == "apply_you_move":
            return self._op_apply_you_move(session_id, session, payload)

        if op == "recommend_moves":
            return self._op_recommend_moves(session_id, session, payload)

        if op == "get_prediction":
            return self._op_get_prediction(session_id, session, payload)

        if op == "sync_you_hand_from_ids":
            return self._op_sync_you_hand(session_id, session, payload)

        if op == "register_enemy_play":
            return self._op_register_enemy_play(session_id, session, payload)

        return self._error_response(session_id, "BadRequest", f"Unsupported op '{op}'.")

    # ------------------------------------------------------------------ #
    # Ops
    # ------------------------------------------------------------------ #
    def _op_init_match(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        you_deck_ids = payload.get("you_deck_ids")
        enemy_deck_ids = payload.get("enemy_deck_ids")
        seed = payload.get("seed")
        opponent_id = payload.get("opponent_id")
        session_mode = payload.get("session_mode", "self_play")

        if session_mode not in {"live_coaching", "self_play", "analysis"}:
            return self._error_response(session_id, "BadRequest", "Invalid session_mode.")

        if not isinstance(you_deck_ids, list) or not isinstance(enemy_deck_ids, list):
            return self._error_response(session_id, "BadRequest", "you_deck_ids and enemy_deck_ids must be provided.")
        if len(you_deck_ids) != 15 or len(enemy_deck_ids) != 15:
            return self._error_response(session_id, "BadRequest", "Each deck must contain exactly 15 card IDs.")

        try:
            player_deck = Deck(you_deck_ids, seed=seed)
            enemy_deck = Deck(enemy_deck_ids, seed=seed)
        except Exception as exc:  # pragma: no cover - defensive
            return self._error_response(session_id, "BadRequest", f"Failed to build decks: {exc}")

        hydrator = CardHydrator()  # uses default DB path
        effect_engine = EffectEngine(db_registry_path(), hydrator)

        game_state = GameState(
            player_deck=player_deck,
            enemy_deck=enemy_deck,
            hydrator=hydrator,
            effect_engine=effect_engine,
            seed=seed,
        )

        enemy_obs = EnemyObservation(known_enemy_deck_ids=enemy_deck_ids)
        prediction_engine = PredictionEngine(hydrator=hydrator, effect_engine=effect_engine)
        coaching_engine = CoachingEngine(hydrator=hydrator, prediction_engine=prediction_engine)

        session = BridgeSession(
            game_state=game_state,
            enemy_obs=enemy_obs,
            scoring_engine=None,
            prediction_engine=prediction_engine,
            coaching_engine=coaching_engine,
            metadata={"you_deck_name": None, "opponent_id": opponent_id},
            session_mode=session_mode,
        )
        self._sessions[session_id] = session

        snapshot = serialize_game_snapshot(game_state, enemy_obs.state, session.metadata, session_mode=session_mode)
        obs_json = serialize_enemy_observation(enemy_obs.state)

        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": snapshot,
            "enemy_observation": obs_json,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    def _op_recommend_moves(self, session_id: str, session: BridgeSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        top_n = payload.get("top_n")
        if not isinstance(top_n, int) or top_n < 1:
            return self._error_response(session_id, "BadRequest", "top_n must be an integer >= 1.")

        # read-only: clone state/obs to avoid mutation
        state_clone = session.game_state.clone()
        obs_clone = copy.deepcopy(session.enemy_obs)

        rec = session.coaching_engine.recommend_moves(state_clone, obs_clone, top_n=top_n, allow_pass=True)
        coaching_json = serialize_coaching_recommendation(rec)

        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": None,
            "enemy_observation": None,
            "match_score": None,
            "coaching": coaching_json,
            "threat_map": None,
            "log_events": [],
        }

    def _op_get_prediction(self, session_id: str, session: BridgeSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = payload.get("mode", "full")
        if mode != "full":
            return self._error_response(session_id, "BadRequest", "Unsupported prediction mode.")

        state_clone = session.game_state.clone()
        obs_clone = copy.deepcopy(session.enemy_obs.state)

        threat_map = session.prediction_engine.full_enemy_prediction(state_clone, obs_clone)
        threat_json = serialize_threat_map(threat_map)

        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": None,
            "enemy_observation": None,
            "match_score": None,
            "coaching": None,
            "threat_map": threat_json,
            "log_events": [],
        }

    def _op_sync_you_hand(self, session_id: str, session: BridgeSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        card_ids = payload.get("card_ids")
        if not isinstance(card_ids, list):
            return self._error_response(session_id, "BadRequest", "card_ids must be provided as a list.")
        if session.session_mode != "live_coaching":
            return self._error_response(
                session_id,
                "BadRequest",
                "sync_you_hand_from_ids is only valid in live_coaching mode.",
            )

        # Overwrite hand deterministically
        try:
            session.game_state.player_hand.sync_from_ids(card_ids)
        except Exception as exc:
            return self._error_response(session_id, "BadRequest", f"Failed to sync hand: {exc}")

        snapshot = serialize_game_snapshot(session.game_state, session.enemy_obs.state, session.metadata, session_mode=session.session_mode)
        obs_json = serialize_enemy_observation(session.enemy_obs.state)

        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": snapshot,
            "enemy_observation": obs_json,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    def _op_register_enemy_play(self, session_id: str, session: BridgeSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        if session.session_mode != "live_coaching":
            return self._error_response(
                session_id,
                "BadRequest",
                "register_enemy_play is only valid in live_coaching mode.",
            )

        card_id = payload.get("card_id")
        lane_index = payload.get("lane_index")
        col_index = payload.get("col_index")
        origin = payload.get("origin", "deck")

        if not isinstance(card_id, str) or not isinstance(lane_index, int) or not isinstance(col_index, int):
            return self._error_response(session_id, "BadRequest", "card_id (str), lane_index (int), col_index (int) required.")

        # Attempt the play
        state_before = session.game_state.clone()
        obs_before = copy.deepcopy(session.enemy_obs.state)
        try:
            session.game_state.apply_enemy_play_from_card_id(card_id, lane_index, col_index, origin=origin)
        except Exception as exc:
            # Restore previous state if mutated
            session.game_state = state_before
            session.enemy_obs.state = obs_before
            return {
                "session_id": session_id,
                "ok": False,
                "error": {
                    "type": "IllegalEnemyPlay",
                    "message": str(exc),
                    "details": {
                        "lane_index": lane_index,
                        "col_index": col_index,
                        "reason": "IllegalPlacement",
                    },
                },
                "state": None,
                "enemy_observation": None,
                "match_score": None,
                "coaching": None,
                "threat_map": None,
                "log_events": [],
            }

        # Update observation
        session.enemy_obs.register_enemy_play(card_id, lane_index, col_index, turn=session.game_state.turn, origin=origin)

        snapshot = serialize_game_snapshot(session.game_state, session.enemy_obs.state, session.metadata, session_mode=session.session_mode)
        obs_json = serialize_enemy_observation(session.enemy_obs.state)
        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": snapshot,
            "enemy_observation": obs_json,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    def _op_get_state(self, session_id: str, session: BridgeSession) -> Dict[str, Any]:
        snapshot = serialize_game_snapshot(session.game_state, session.enemy_obs.state, session.metadata, session_mode=session.session_mode)
        obs_json = serialize_enemy_observation(session.enemy_obs.state)
        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": snapshot,
            "enemy_observation": obs_json,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    def _op_apply_you_move(self, session_id: str, session: BridgeSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        move = payload.get("move")
        if not isinstance(move, dict):
            return self._error_response(session_id, "BadRequest", "Missing or invalid move payload.")

        card_id = move.get("card_id")
        hand_index = move.get("hand_index")
        lane_index = move.get("lane_index")
        col_index = move.get("col_index")

        if not isinstance(card_id, str) or not isinstance(hand_index, int) or not isinstance(lane_index, int) or not isinstance(col_index, int):
            return self._error_response(session_id, "BadRequest", "Move must include card_id (str), hand_index (int), lane_index (int), col_index (int).")

        hand = session.game_state.player_hand
        if hand_index < 0 or hand_index >= len(hand.cards):
            return self._error_response(session_id, "BadRequest", "hand_index out of range.")
        card = hand.cards[hand_index]
        if card.id != card_id:
            return self._error_response(session_id, "BadRequest", "card_id does not match card at hand_index.")

        # Bounds check
        board = session.game_state.board
        num_lanes = len(board.tiles)
        num_cols = len(board.tiles[0]) if num_lanes > 0 else 0
        if lane_index < 0 or lane_index >= num_lanes or col_index < 0 or col_index >= num_cols:
            return self._illegal_move(session_id, lane_index, col_index, "OutOfBounds", "Tile out of bounds.")

        tile = board.tile_at(lane_index, col_index)
        reason = None
        if tile.card_id is not None:
            reason = "TileOccupied"
            msg = "Tile is already occupied."
        elif tile.owner != "Y":
            reason = "TileNotOwnedByYou"
            msg = "Tile is not owned by YOU."
        elif tile.rank < card.cost:
            reason = "InsufficientRank"
            msg = "Tile rank is insufficient for card cost."
        elif session.game_state.side_to_act != "Y":
            reason = "WrongTurn"
            msg = "It is not YOUR turn."
        else:
            msg = ""

        if reason:
            return self._illegal_move(session_id, lane_index, col_index, reason, msg)

        # As an extra safeguard, use legality helper
        if not is_legal_placement(board, lane_index, col_index, card):
            return self._illegal_move(session_id, lane_index, col_index, "IllegalPlacement", "Placement rejected by legality checker.")

        # Perform the move
        try:
            session.game_state.play_card_from_hand("Y", hand_index, lane_index, col_index)
        except Exception as exc:
            return self._illegal_move(session_id, lane_index, col_index, "IllegalPlacement", f"Engine rejected move: {exc}")

        # Update observation
        session.enemy_obs.update_from_game_state(session.game_state)

        snapshot = serialize_game_snapshot(session.game_state, session.enemy_obs.state, session.metadata, session_mode=session.session_mode)
        obs_json = serialize_enemy_observation(session.enemy_obs.state)

        return {
            "session_id": session_id,
            "ok": True,
            "error": None,
            "state": snapshot,
            "enemy_observation": obs_json,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _error_response(self, session_id: Optional[str], err_type: str, message: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "ok": False,
            "error": {"type": err_type, "message": message},
            "state": None,
            "enemy_observation": None,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }

    def _illegal_move(
        self, session_id: str, lane_index: int, col_index: int, reason: str, message: str
    ) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "ok": False,
            "error": {
                "type": "IllegalMove",
                "message": message,
                "details": {"lane_index": lane_index, "col_index": col_index, "reason": reason},
            },
            "state": None,
            "enemy_observation": None,
            "match_score": None,
            "coaching": None,
            "threat_map": None,
            "log_events": [],
        }


def db_path_registry_path() -> str:
    # Centralized helper to build effect engine with default registry path.
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    return str(repo_root / "data" / "qb_effects_v1.1.json")


def db_registry_path():
    from pathlib import Path

    return Path(db_path_registry_path())


# ---------------------------------------------------------------------- #
# Serialization helpers
# ---------------------------------------------------------------------- #
def serialize_game_snapshot(
    state: GameState, enemy_obs: EnemyObservationState, metadata: Dict[str, Any], session_mode: str
) -> Dict[str, Any]:
    board_json = serialize_board_state(state.board, state.effect_engine)
    you_hand = serialize_hand(state.player_hand)
    snapshot = {
        "turn_number": state.turn,
        "you_turns_taken": state._turns_taken.get("Y", 0),
        "enemy_turns_taken": state._turns_taken.get("E", 0),
        "side_to_act": state.side_to_act,
        "is_game_over": state.is_game_over(),
        "winner": None,  # filled by scoring/end-of-game logic later
        "board": board_json,
        "you_hand": you_hand,
        "enemy_hand_size": len(state.enemy_hand.cards),
        "you_deck_size": state.player_deck.cards_remaining(),
        "enemy_deck_size": state.enemy_deck.cards_remaining(),
        "you_mulligan_used": state._mulligan_used.get("Y", False),
        "enemy_mulligan_used": state._mulligan_used.get("E", False),
        "match_score": None,
        "metadata": metadata or {},
        "session_mode": session_mode,
    }
    return snapshot


def serialize_board_state(board_state: BoardState, effect_engine: EffectEngine) -> Dict[str, Any]:
    lanes: List[List[Dict[str, Any]]] = []
    for lane_idx, row in enumerate(board_state.tiles):
        lane_tiles: List[Dict[str, Any]] = []
        for col_idx, tile in enumerate(row):
            card_json: Optional[Dict[str, Any]] = None
            if tile.card_id is not None:
                card = effect_engine._card_hydrator.get_card(tile.card_id)
                eff_power = effect_engine.compute_effective_power(board_state, lane_idx, col_idx)
                card_json = {
                    "card_id": card.id,
                    "name": card.name,
                    "cost": card.cost,
                    "base_power": card.power,
                    "effect_id": card.effect_id,
                    "effect_description": card.effect_description,
                    "origin": tile.origin,
                    "spawned_by": tile.spawned_by,
                    "power_delta": tile.power_delta,
                    "scale_delta": tile.scale_delta,
                    "effective_power": eff_power,
                }
            lane_tiles.append(
                {
                    "lane_index": lane_idx,
                    "col_index": col_idx,
                    "owner": tile.owner,
                    "rank": tile.rank,
                    "card": card_json,
                }
            )
        lanes.append(lane_tiles)
    return {"lanes": lanes}


def serialize_hand(hand_state) -> Dict[str, Any]:
    cards_json: List[Dict[str, Any]] = []
    for idx, card in enumerate(hand_state.cards):
        cards_json.append(
            {
                "hand_index": idx,
                "card_id": card.id,
                "name": card.name,
                "cost": card.cost,
                "base_power": card.power,
                "effect_id": card.effect_id,
                "effect_description": card.effect_description,
            }
        )
    return {"cards": cards_json}


def serialize_enemy_observation(obs: EnemyObservationState) -> Dict[str, Any]:
    obs_list: List[Dict[str, Any]] = []
    for o in obs.enemy_observations:
        obs_list.append(
            {
                "card_id": o.card_id,
                "origin": o.origin,
                "turn_observed": o.turn_observed,
                "lane_index": o.lane_index,
                "col_index": o.col_index,
                "destroyed_on_turn": o.destroyed_on_turn,
            }
        )
    remaining = list(obs.enemy_deck_knowledge.remaining_ids) if obs.enemy_deck_knowledge else []
    return {
        "observations": obs_list,
        "remaining_ids": remaining,
        "last_updated_turn": obs.last_updated_turn,
    }


def serialize_match_score(match_score: MatchScore) -> Dict[str, Any]:
    def map_winner(w):
        if w == "Y":
            return "YOU"
        if w == "E":
            return "ENEMY"
        return None

    lanes_json = []
    for lane in match_score.lanes:
        lanes_json.append(
            {
                "lane_index": lane.lane_index,
                "power_you": lane.power_you,
                "power_enemy": lane.power_enemy,
                "winner": map_winner(lane.winner),
                "lane_points": lane.lane_points,
            }
        )
    return {
        "lanes": lanes_json,
        "total_you": match_score.total_you,
        "total_enemy": match_score.total_enemy,
        "winner": map_winner(match_score.winner),
        "margin": match_score.margin,
    }


def serialize_lane_status(lane: LaneStatus) -> Dict[str, Any]:
    return {
        "lane_index": lane.lane_index,
        "you_power": lane.you_power,
        "enemy_power": lane.enemy_power,
        "winner": lane.winner,
        "lane_points": lane.lane_points,
    }


def serialize_position(position: PositionEvaluation) -> Dict[str, Any]:
    return {
        "match_score": serialize_match_score(position.match_score),
        "lanes": [serialize_lane_status(l) for l in position.lanes],
        "you_margin": position.you_margin,
        "enemy_best_margin": position.enemy_best_margin,
        "enemy_expected_margin": position.enemy_expected_margin,
        "is_clearly_winning": position.is_clearly_winning,
        "is_clearly_losing": position.is_clearly_losing,
        "is_even": position.is_even,
    }


def serialize_move_eval(move_eval: MoveEvaluation) -> Dict[str, Any]:
    move = move_eval.move
    move_json = {
        "card_id": move.card_id,
        "hand_index": move.hand_index,
        "lane_index": move.lane_index,
        "col_index": move.col_index,
    }
    return {
        "move": move_json,
        "you_margin_after_move": move_eval.you_margin_after_move,
        "you_margin_after_enemy_best": move_eval.you_margin_after_enemy_best,
        "you_margin_after_enemy_expected": move_eval.you_margin_after_enemy_expected,
        "position_after_move": serialize_position(move_eval.position_after_move)
        if move_eval.position_after_move
        else None,
        "quality_rank": move_eval.quality_rank,
        "quality_label": move_eval.quality_label,
        "explanation_tags": move_eval.explanation_tags or [],
        "explanation_lines": move_eval.explanation_lines or [],
    }


def serialize_coaching_recommendation(rec: CoachingRecommendation) -> Dict[str, Any]:
    return {
        "position": serialize_position(rec.position),
        "moves": [serialize_move_eval(m) for m in rec.moves],
        "top_n": rec.top_n,
        "primary_message": rec.primary_message,
        "secondary_messages": rec.secondary_messages,
    }


def serialize_threat_map(threat_map) -> Dict[str, Any]:
    lane_pressure = {str(k): v for k, v in threat_map.lane_pressure.items()}
    tile_pressure = {f"{lane},{col}": v for (lane, col), v in threat_map.tile_pressure.items()}
    return {
        "best_enemy_score": threat_map.best_enemy_score,
        "expected_enemy_score": threat_map.expected_enemy_score,
        "lane_pressure": lane_pressure,
        "tile_pressure": tile_pressure,
    }
