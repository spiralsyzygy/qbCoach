from qb_engine.cli.qb_live_cli import (
    PendingResolution,
    _handle_resolution_input,
    resolve_card_token,
)


def _make_index():
    return [
        {"id": "001", "name": "Security Officer"},
        {"id": "008", "name": "Grasslands Wolf"},
        {"id": "009", "name": "Grasslands Wisp"},
        {"id": "014", "name": "Quetzalcoatl"},
        {"id": "111", "name": "Magic Pot"},
    ]


def test_single_token_resolution_accepts_y(monkeypatch, capsys):
    card_index = _make_index()
    tokens = ["Quetzalcoatl?"]
    status, cands = resolve_card_token(card_index, tokens[0])
    assert status in {"ambiguous", "resolved"}

    executed = []

    def exec_fn(p):
        executed.append((p.command, list(p.tokens)))

    pending = PendingResolution(
        command="draw",
        tokens=tokens,
        raw_input="draw Quetzalcoatl?",
        token_index=0,
        candidates=cands,
        token=tokens[0],
        extra={},
    )
    pending = _handle_resolution_input("y", pending, exec_fn, card_index)
    assert pending is None
    assert executed and executed[0][1][0] == "014"


def test_numeric_selection_resolves_second_candidate():
    card_index = _make_index()
    tokens = ["grasslands"]
    status, cands = resolve_card_token(card_index, tokens[0])
    assert status == "ambiguous"
    executed = []

    def exec_fn(p):
        executed.append((p.command, list(p.tokens)))

    pending = PendingResolution(
        command="play",
        tokens=tokens,
        raw_input="play grasslands top 2",
        token_index=0,
        candidates=cands,
        token=tokens[0],
        extra={"row": 0, "col": 1},
    )
    pending = _handle_resolution_input("2", pending, exec_fn, card_index)
    assert pending is None
    assert executed
    assert executed[0][1][0] == "009"  # second candidate after sort


def test_batch_resolution_left_to_right(monkeypatch):
    card_index = _make_index()
    tokens = ["Security Officer", "Grasslands Wolf", "quetzalcoatl?"]
    # only the last token needs resolution
    status, cands = resolve_card_token(card_index, tokens[2])
    executed = []

    def exec_fn(p):
        executed.append(list(p.tokens))

    pending = PendingResolution(
        command="set_hand",
        tokens=tokens,
        raw_input='set_hand crawler "queen bee" quetzalcoatl?',
        token_index=2,
        candidates=cands,
        token=tokens[2],
        extra={},
    )
    pending = _handle_resolution_input("y", pending, exec_fn, card_index)
    assert pending is None
    assert executed
    assert executed[0][-1] == "014"


def test_cancel_aborts_without_execution():
    card_index = _make_index()
    tokens = ["magic pot?"]
    status, cands = resolve_card_token(card_index, tokens[0])
    executed = []

    def exec_fn(p):
        executed.append(True)

    pending = PendingResolution(
        command="enemy",
        tokens=tokens,
        raw_input="enemy magic pot bot 3",
        token_index=0,
        candidates=cands,
        token=tokens[0],
        extra={"row": 2, "col": 2},
    )
    pending = _handle_resolution_input("n", pending, exec_fn, card_index)
    assert pending is None
    assert not executed


def test_resolution_mode_blocks_other_commands(capsys):
    card_index = _make_index()
    tokens = ["quetzalcoatl?"]
    status, cands = resolve_card_token(card_index, tokens[0])

    def exec_fn(p):
        raise AssertionError("Should not execute during resolution")

    pending = PendingResolution(
        command="draw",
        tokens=tokens,
        raw_input="draw quetzalcoatl?",
        token_index=0,
        candidates=cands,
        token=tokens[0],
        extra={},
    )
    still_pending = _handle_resolution_input("state", pending, exec_fn, card_index)
    assert still_pending is not None
    captured = capsys.readouterr()
    assert "Finish resolution first" in captured.out
