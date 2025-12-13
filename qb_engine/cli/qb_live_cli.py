from __future__ import annotations

from typing import List, Tuple

from qb_engine.card_resolver import (
    CardResolveError,
    parse_card_list,
    resolve_card_identifier,
)
from qb_engine.card_resolver import _QUANTITY_RE  # type: ignore
from qb_engine.live_session import LiveSessionEngineBridge
from qb_engine.live_session import TurnSnapshot, format_turn_snapshot_for_ux


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
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
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
            try:
                cards = parse_card_list(" ".join(args))
                if len(cards) != 1:
                    print("Draw expects exactly one card. Use set_hand to overwrite.")
                    continue
                bridge.apply_draw(cards[0].id)
                snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                    engine_output={"legal_moves": bridge.legal_moves()},
                    last_event="you_draw",
                )
                bridge.append_turn_snapshot(snapshot)
                print("Draw applied. You can now request rec/play.")
            except CardResolveError as exc:
                print(f"Error: {exc}")
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
            try:
                cards = parse_card_list(" ".join(args))
                ids = [c.id for c in cards]
                bridge.sync_you_hand_from_ids(ids)
                print("Hand replaced.")
            except CardResolveError as exc:
                print(f"Error: {exc}")
            continue
        if cmd == "enemy":
            if len(args) != 3:
                print("Usage: enemy <id/name> <row> <col>")
                continue
            try:
                cid = bridge.resolve_card_id(args[0])
                row, col = _parse_row_col(args[1], args[2])
                bridge.register_enemy_play(cid, row, col)
                snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                    engine_output={"legal_moves": bridge.legal_moves()},
                    last_event="enemy_play_registered",
                )
                bridge.append_turn_snapshot(snapshot)
                print(f"Enemy play registered. === YOUR TURN BEGINS (turn {bridge.turn_counter}) ===")
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
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
            if len(args) != 3:
                print("Usage: play <id/name> <row> <col>")
                continue
            try:
                cid = bridge.resolve_card_id(args[0])
                row, col = _parse_row_col(args[1], args[2])
                bridge.apply_you_move(cid, row, col)
                snapshot: TurnSnapshot = bridge.create_turn_snapshot(
                    engine_output={"legal_moves": bridge.legal_moves()},
                    chosen_move={"card_id": cid, "row": row, "col": col},
                    last_event="you_play",
                )
                bridge.append_turn_snapshot(snapshot)
                print("Move applied. === ENEMY TURN BEGINS ===")
            except Exception as exc:  # noqa: BLE001
                print(f"Illegal move or error: {exc}")
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
