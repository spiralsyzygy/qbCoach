from __future__ import annotations

from typing import Callable, List, Tuple, Optional, Dict

from dataclasses import dataclass
from difflib import get_close_matches

from qb_engine.card_resolver import (
    CardResolveError,
    parse_card_list,
    resolve_card_identifier,
)
from qb_engine.card_resolver import _QUANTITY_RE  # type: ignore
from qb_engine.live_session import (
    LiveSessionEngineBridge,
    TurnSnapshot,
    format_turn_snapshot_for_ux,
    parse_resync_board_lines,
)


@dataclass
class PendingResolution:
    command: str
    tokens: List[str]
    raw_input: str
    token_index: int
    candidates: List[Dict[str, str]]  # {"id","name"}
    token: str
    extra: Dict[str, object]


def _print_header() -> None:
    print("qb_live_cli — Phase G / Track A.5 Live Coaching")


def _prompt_yes_no(prompt: str) -> bool:
    resp = input(f"{prompt} [y/N]: ").strip().lower()
    return resp.startswith("y")


def _prompt_enemy_deck_tag() -> str | None:
    tag = input("Enter enemy deck tag (optional): ").strip()
    return tag or None


def _choose_deck_mode() -> str:
    while True:
        choice = input("Provide your deck: (a) deck tag  (b) explicit 15-card list. Choice [a/b]: ").strip().lower()
        if choice in {"a", "b"}:
            return choice
        print("Please enter 'a' or 'b'.")


def _parse_identifiers_line(line: str) -> List[str]:
    # Accept comma- or space-separated identifiers.
    if "," in line:
        tokens = [t.strip() for t in line.split(",") if t.strip()]
    else:
        tokens = [t.strip() for t in line.split() if t.strip()]
    return tokens


def _resolve_hand_with_corrections(user_raw: str) -> List[str]:
    """
    Resolve a hand entry with interactive correction on unknown tokens.
    If a suggestion is offered, allow the user to accept it; otherwise prompt
    for a replacement until resolved (or aborts if blank).
    """
    tokens = _parse_identifiers_line(user_raw)
    resolved_ids: List[str] = []
    for tok in tokens:
        qty = 1
        tok_clean = tok.strip()
        m = _QUANTITY_RE.match(tok_clean)
        if m:
            tok_clean = m.group("name").strip()
            qty = int(m.group("count"))

        while True:
            try:
                card = resolve_card_identifier(tok_clean)
                resolved_ids.extend([card.id] * qty)
                break
            except CardResolveError as exc:
                msg = str(exc)
                suggestion = None
                if "Did you mean:" in msg:
                    suggestion_part = msg.split("Did you mean:", 1)[1].strip().rstrip("?")
                    suggestion = suggestion_part.split(",")[0].strip() if suggestion_part else None
                if suggestion:
                    resp = input(f"{msg} Accept '{suggestion}'? [y/N]: ").strip().lower()
                    if resp.startswith("y"):
                        card = resolve_card_identifier(suggestion)
                        resolved_ids.extend([card.id] * qty)
                        break
                replacement = input(f"Enter replacement for '{tok_clean}' (or leave blank to cancel hand entry): ").strip()
                if not replacement:
                    raise CardResolveError(msg)
                tok_clean = replacement
    return resolved_ids


def _collect_deck_ids_from_input(bridge: LiveSessionEngineBridge) -> List[str]:
    while True:
        raw = input(
            "Enter your 15-card deck as IDs and/or names, separated by commas or spaces:\n"
            "Example: 003, 005, Levrikon, \"Grasslands Wolf\", 018, ...\nDeck: "
        )
        try:
            cards = parse_card_list(raw)
        except CardResolveError as exc:
            print(f"Error: {exc}")
            continue
        if len(cards) != 15:
            print("Deck must have exactly 15 entries. Please try again.")
            continue
        ids = [c.id for c in cards]
        names = ", ".join(f"{c.name} ({c.id})" for c in cards)
        print(f"Parsed deck: {names}")
        return ids


def _print_help() -> None:
    print(
        "Commands:\n"
        "  draw <ids/names...>           sync your current draw (append)\n"
        "  set_hand <ids/names...>       replace your hand (escape hatch)\n"
        "  resolve <name/id>             resolve a card to its canonical id/name\n"
        "  enemy <id/name> <row> <col>   register enemy play\n"
        "  rec                           compute recommendations + prediction\n"
        "  play <id/name> <row> <col>    apply your move\n"
        "  pass                          skip your turn and hand off to enemy\n"
        "  resync_board                  manual board override (debug)\n"
        "  state                         show board & your hand\n"
        "  log                           print the current session log path\n"
        "  help                          show this menu again\n"
        "  quit                          end session\n"
    )


def _parse_id_tokens(args: List[str]) -> List[str]:
    """
    Normalize tokens that may include commas or quoted names into a clean list of identifiers.
    """
    if not args:
        return []
    raw = " ".join(args)
    return _parse_identifiers_line(raw)


def _resolve_card_interactive(token: str) -> None:
    try:
        card = resolve_card_identifier(token)
        print(f"{card.name} ({card.id})")
    except CardResolveError as exc:
        print(f"Could not resolve '{token}': {exc}")


def _diff_summary(before, after) -> List[str]:
    lines: List[str] = []
    lane_names = ["TOP", "MID", "BOT"]
    for lane_index, row in enumerate(before.tiles):
        for col_index, _ in enumerate(row):
            b_desc = before.describe_tile(lane_index, col_index)
            a_desc = after.describe_tile(lane_index, col_index)
            if b_desc != a_desc:
                before_token = f"{b_desc['owner']}{b_desc['rank']}"
                if b_desc.get("card_id"):
                    before_token = f"{b_desc['card_id']}"
                after_token = f"{a_desc['owner']}{a_desc['rank']}"
                if a_desc.get("card_id"):
                    after_token = f"{a_desc['card_id']}"
                lines.append(f"{lane_names[lane_index]}-{col_index+1}: {before_token} -> {after_token}")
    return lines


def _build_card_index() -> List[Dict[str, str]]:
    from qb_engine.card_hydrator import CardHydrator

    hydrator = CardHydrator()
    cards: List[Dict[str, str]] = []
    for cid, entry in hydrator.index.items():
        if cid == "_meta":
            continue
        cards.append({"id": cid, "name": entry["name"]})
    cards.sort(key=lambda c: c["id"])
    return cards


def resolve_card_token(card_index: List[Dict[str, str]], token: str) -> tuple[str, List[Dict[str, str]]]:
    tok = token.strip()
    tok_lower = tok.lower()

    def sort_unique(cands: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen = set()
        out = []
        for c in cands:
            key = c["id"]
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        out.sort(key=lambda c: c["id"])
        return out

    by_id = {c["id"]: c for c in card_index}
    if tok in by_id:
        return "resolved", [by_id[tok]]

    exact = [c for c in card_index if c["name"].lower() == tok_lower]
    if exact:
        return ("resolved" if len(exact) == 1 else "ambiguous", sort_unique(exact))

    prefix = [c for c in card_index if c["name"].lower().startswith(tok_lower)]
    substring = [c for c in card_index if tok_lower in c["name"].lower()]
    close: List[Dict[str, str]] = []
    if not prefix and not substring:
        names = [c["name"].lower() for c in card_index]
        for name in get_close_matches(tok_lower, names, n=3, cutoff=0.6):
            for c in card_index:
                if c["name"].lower() == name:
                    close.append(c)
    candidates = sort_unique(prefix + substring + close)
    if not candidates:
        return "unknown", []
    if len(candidates) == 1:
        return "resolved", candidates
    return "ambiguous", candidates


def _handle_opening_hand(bridge: LiveSessionEngineBridge) -> None:
    """
    Turn 0 helper: prompt for opening hand, suggest mulligan path, confirm start of turn 1.
    """
    gs = bridge._game_state
    dealt = []
    if gs:
        dealt = gs.player_hand.as_card_ids()
    if dealt:
        print(f"Engine dealt opening hand (for reference): {', '.join(dealt)}")
    user_raw = input("Enter your opening hand (IDs/names, comma/space separated), or press Enter to accept engine hand: ").strip()
    if user_raw:
        try:
            ids = _resolve_hand_with_corrections(user_raw)
            bridge.sync_you_hand_from_ids(ids)
            print(f"Opening hand synced to: {', '.join(ids)}")
        except CardResolveError as exc:
            print(f"Error syncing opening hand: {exc}. Keeping engine hand.")
    # Mulligan suggestion
    mulligan_raw = input("If you mulliganed, enter your post-mulligan hand now (or press Enter to keep current): ").strip()
    if mulligan_raw:
        try:
            ids = _resolve_hand_with_corrections(mulligan_raw)
            bridge.sync_you_hand_from_ids(ids)
            print(f"Post-mulligan hand set to: {', '.join(ids)}")
        except CardResolveError as exc:
            print(f"Error syncing mulligan hand: {exc}. Keeping current hand.")
    # Emit a mulligan snapshot for logs/GPT
    try:
        mull_snapshot = bridge.create_turn_snapshot(
            engine_output=bridge.mulligan_output(),
            last_event="mulligan_snapshot",
        )
        bridge.append_turn_snapshot(mull_snapshot)
        print("ENGINE_OUTPUT (mulligan):")
        print(format_turn_snapshot_for_ux(mull_snapshot))
    except Exception:
        print("Note: Mulligan evaluation not available.")
    print("=== TURN 1 BEGINS (side_to_act=YOU) ===")


def _parse_row_col(row_token: str, col_token: str) -> Tuple[int, int]:
    row_map = {"top": 0, "t": 0, "mid": 1, "m": 1, "bot": 2, "b": 2}
    row = row_map.get(row_token.lower())
    if row is None:
        raise ValueError("Invalid row. Use top/mid/bot.")
    try:
        col_int = int(col_token)
    except ValueError as exc:
        raise ValueError("Column must be an integer 1-5.") from exc
    if not 1 <= col_int <= 5:
        raise ValueError("Column must be between 1 and 5.")
    return row, col_int - 1


def _print_resolution_prompt(pending: PendingResolution) -> None:
    choices = ", ".join(f"[{idx+1}] {c['name']} ({c['id']})" for idx, c in enumerate(pending.candidates))
    print(f'Ambiguous card token: "{pending.token}"')
    print(f"Choose: {choices}")
    print("Enter 1-{}, or 'y' to accept [1], or 'n' to cancel:".format(len(pending.candidates)))


def _handle_resolution_input(
    line: str,
    pending: PendingResolution,
    execute_fn: Callable[[PendingResolution], None],
    card_index: List[Dict[str, str]],
) -> Optional[PendingResolution]:
    if not pending.candidates:
        print(f"Cannot resolve token '{pending.token}'. Command aborted.")
        return None
    lower = line.strip().lower()
    if not lower:
        _print_resolution_prompt(pending)
        return pending
    if lower in {"help"}:
        print("Resolution mode: respond with 1..N, 'y' to accept first, 'n' to cancel.")
        _print_resolution_prompt(pending)
        return pending
    if lower in {"n", "no", "cancel"}:
        print("Resolution canceled; command aborted.")
        return None
    choice_idx = None
    if lower in {"y", "yes"}:
        choice_idx = 0
    else:
        try:
            num = int(lower)
            if 1 <= num <= len(pending.candidates):
                choice_idx = num - 1
        except ValueError:
            pass
    if choice_idx is None:
        print("Finish resolution first.")
        _print_resolution_prompt(pending)
        return pending

    chosen = pending.candidates[choice_idx]
    pending.tokens[pending.token_index] = chosen["id"]
    pending.extra.setdefault("resolution_log", []).append(
        {
            "event": "card_resolved",
            "command": pending.command,
            "token": pending.token,
            "chosen_id": chosen["id"],
            "chosen_name": chosen["name"],
        }
    )

    # Advance to next token if any need resolution
    idx = pending.token_index + 1
    while idx < len(pending.tokens):
        status, cands = resolve_card_token(card_index, pending.tokens[idx])
        if status == "resolved":
            pending.tokens[idx] = cands[0]["id"]
            idx += 1
            continue
        pending.token_index = idx
        pending.candidates = cands
        pending.token = pending.tokens[idx]
        _print_resolution_prompt(pending)
        return pending

    execute_fn(pending)
    return None


def main() -> None:
    _print_header()
    if not _prompt_yes_no("Start new live coaching session?"):
        print("Bye.")
        return
    coaching_mode = input("Coaching mode [strict/strategy] (default strict): ").strip().lower() or "strict"
    try:
        bridge_coaching_mode = coaching_mode if coaching_mode else "strict"
    except Exception:
        bridge_coaching_mode = "strict"

    bridge = LiveSessionEngineBridge(session_mode="live_coaching", coaching_mode=bridge_coaching_mode)
    card_index = _build_card_index()
    enemy_deck_tag = _prompt_enemy_deck_tag()
    deck_choice = _choose_deck_mode()

    you_deck_ids: List[str] | None = None
    if deck_choice == "b":
        you_deck_ids = _collect_deck_ids_from_input(bridge)
    # For deck tag path ("a"), we leave you_deck_ids as None for now.

    bridge.init_match(you_deck_ids=you_deck_ids, enemy_deck_tag=enemy_deck_tag, coaching_mode=bridge_coaching_mode)

    _handle_opening_hand(bridge)

    print("Session initialized. Enter 'help' for commands.")
    _print_help()
    pending: Optional[PendingResolution] = None

    def _execute_pending(p: PendingResolution) -> None:
        if p.command == "draw":
            for cid in p.tokens:
                bridge.apply_draw(cid)
            snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                engine_output={"legal_moves": bridge.legal_moves()},
                last_event="you_draw",
                card_resolution=p.extra.get("resolution_log"),
            )
            bridge.append_turn_snapshot(snapshot)
            print("Draw applied.")
            return
        if p.command == "set_hand":
            bridge.sync_you_hand_from_ids(p.tokens)
            print(f"Hand replaced: {', '.join(p.tokens)}")
            return
        if p.command == "play":
            row = p.extra["row"]
            col = p.extra["col"]
            cid = p.tokens[0]
            bridge.apply_you_move(cid, row, col)
            snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                engine_output={"legal_moves": bridge.legal_moves()},
                chosen_move={"card_id": cid, "row": row, "col": col},
                last_event="you_play",
                card_resolution=p.extra.get("resolution_log"),
            )
            bridge.append_turn_snapshot(snapshot)
            print("Move applied. === ENEMY TURN BEGINS ===")
            return
        if p.command == "enemy":
            row = p.extra["row"]
            col = p.extra["col"]
            cid = p.tokens[0]
            bridge.register_enemy_play(cid, row, col)
            snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                engine_output={"legal_moves": bridge.legal_moves()},
                last_event="enemy_play_registered",
                card_resolution=p.extra.get("resolution_log"),
            )
            bridge.append_turn_snapshot(snapshot)
            print(f"Enemy play registered. === YOUR TURN BEGINS (turn {bridge.turn_counter}) ===")
            return
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if pending:
            pending = _handle_resolution_input(raw, pending, _execute_pending, card_index)
            continue
        if not raw:
            continue
        cmd_parts = raw.split()
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:]

        if cmd == "quit":
            print("Ending session.")
            break
        if cmd == "help":
            _print_help()
            continue
        if cmd == "draw":
            if not args:
                print("Usage: draw <ids/names...>")
                continue
            tokens = _parse_identifiers_line(" ".join(args))
            unresolved_idx = None
            for idx, tok in enumerate(tokens):
                status, cands = resolve_card_token(card_index, tok)
                if status == "resolved":
                    tokens[idx] = cands[0]["id"]
                    continue
                pending = PendingResolution(
                    command="draw",
                    tokens=tokens,
                    raw_input=raw,
                    token_index=idx,
                    candidates=cands,
                    token=tok,
                    extra={},
                )
                _print_resolution_prompt(pending)
                unresolved_idx = idx
                break
            if pending:
                continue
            if len(tokens) != 1:
                print("Draw expects exactly one card. Use set_hand to overwrite.")
                continue
            _execute_pending(
                PendingResolution(
                    command="draw",
                    tokens=tokens,
                    raw_input=raw,
                    token_index=0,
                    candidates=[],
                    token=tokens[0],
                    extra={},
                )
            )
            continue
        if cmd == "resolve":
            if not args:
                print("Usage: resolve <id/name>")
                continue
            _resolve_card_interactive(" ".join(args))
            continue
        if cmd == "set_hand":
            if not args:
                print("Usage: set_hand <ids/names...>")
                continue
            tokens = _parse_identifiers_line(" ".join(args))
            for idx, tok in enumerate(tokens):
                status, cands = resolve_card_token(card_index, tok)
                if status == "resolved":
                    tokens[idx] = cands[0]["id"]
                    continue
                pending = PendingResolution(
                    command="set_hand",
                    tokens=tokens,
                    raw_input=raw,
                    token_index=idx,
                    candidates=cands,
                    token=tok,
                    extra={},
                )
                _print_resolution_prompt(pending)
                break
            if pending:
                continue
            _execute_pending(
                PendingResolution(
                    command="set_hand",
                    tokens=tokens,
                    raw_input=raw,
                    token_index=0,
                    candidates=[],
                    token=tokens[0],
                    extra={},
                )
            )
            continue
        if cmd == "enemy":
            if len(args) < 3:
                print("Usage: enemy <id/name> <row> <col>")
                continue
            tok = " ".join(args[:-2])
            row_tok, col_tok = args[-2], args[-1]
            try:
                row, col = _parse_row_col(row_tok, col_tok)
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
                continue
            status, cands = resolve_card_token(card_index, tok)
            if status == "resolved":
                _execute_pending(
                    PendingResolution(
                        "enemy",
                        [cands[0]["id"]],
                        raw,
                        0,
                        [],
                        tok,
                        {"row": row, "col": col},
                    )
                )
            else:
                pending = PendingResolution(
                    command="enemy",
                    tokens=[tok],
                    raw_input=raw,
                    token_index=0,
                    candidates=cands,
                    token=tok,
                    extra={"row": row, "col": col},
                )
                _print_resolution_prompt(pending)
            continue
        if cmd == "rec":
            try:
                recs = bridge.recommend_moves(top_n=3)
                pred = bridge.get_prediction()
                state = bridge.get_state()
                snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                    engine_output={"recommend_moves": recs, "prediction": pred, "legal_moves": bridge.legal_moves()},
                    last_event="recommend",
                )
                bridge.append_turn_snapshot(snapshot)
                print(format_turn_snapshot_for_ux(snapshot))
            except Exception as exc:  # noqa: BLE001
                print(f"Error during rec: {exc}")
            continue
        if cmd == "play":
            if len(args) < 3:
                print("Usage: play <id/name> <row> <col>")
                continue
            tok = " ".join(args[:-2])
            row_tok, col_tok = args[-2], args[-1]
            try:
                row, col = _parse_row_col(row_tok, col_tok)
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
                continue
            status, cands = resolve_card_token(card_index, tok)
            if status == "resolved":
                _execute_pending(
                    PendingResolution(
                        "play",
                        [cands[0]["id"]],
                        raw,
                        0,
                        [],
                        tok,
                        {"row": row, "col": col},
                    )
                )
            else:
                pending = PendingResolution(
                    command="play",
                    tokens=[tok],
                    raw_input=raw,
                    token_index=0,
                    candidates=cands,
                    token=tok,
                    extra={"row": row, "col": col},
                )
                _print_resolution_prompt(pending)
            continue
        if cmd == "resync_board":
            if bridge._game_state is None or bridge._hydrator is None:
                print("Session not initialized.")
                continue
            print(
                "Enter three rows (TOP, MID, BOT) with 5 bracketed tokens each.\n"
                "Examples: [Y1] [N0] [Y:001] [N0] [E1] or [001:5★].\n"
                "Occupied neutral tiles must specify side using [Y:ID] or [E:ID]."
            )
            row_labels = ["TOP", "MID", "BOT"]
            lines: List[str] = []
            for label in row_labels:
                lines.append(input(f"{label}: ").strip())
            try:
                preview = parse_resync_board_lines(lines, bridge._game_state.board, bridge._hydrator)
                diff_lines = _diff_summary(bridge._game_state.board, preview)
                if diff_lines:
                    print("Proposed changes:")
                    for entry in diff_lines:
                        print(f"- {entry}")
                else:
                    print("No changes detected.")
            except Exception as exc:  # noqa: BLE001
                print(f"Error parsing board: {exc}")
                continue
            if not _prompt_yes_no("Apply resync_board override?"):
                print("Resync cancelled.")
                continue
            try:
                snapshot = bridge.manual_resync_board(lines)
                print("Board resynced and logged.")
                print(format_turn_snapshot_for_ux(snapshot))
            except Exception as exc:  # noqa: BLE001
                print(f"Error applying resync: {exc}")
            continue
        if cmd == "pass":
            try:
                bridge.pass_you_turn()
                snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                    engine_output={"legal_moves": bridge.legal_moves()},
                    chosen_move={"action": "PASS"},
                    last_event="you_pass",
                )
                bridge.append_turn_snapshot(snapshot)
                print("Turn passed. === ENEMY TURN BEGINS ===")
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
            continue
        if cmd == "state":
            snapshot: TurnSnapshot = bridge.create_turn_snapshot(last_event="state")
            print(format_turn_snapshot_for_ux(snapshot))
            continue
        if cmd == "log":
            # Ensure log path exists
            if bridge.log_path is None:
                path = bridge._ensure_log_path()  # type: ignore[attr-defined]
            else:
                path = bridge.log_path
            print(f"Log file: {path}")
            continue

        print("Unknown command. Type 'help' for available commands.")


if __name__ == "__main__":
    main()
