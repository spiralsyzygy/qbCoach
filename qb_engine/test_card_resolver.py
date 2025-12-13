from qb_engine.card_resolver import CardResolveError, parse_card_list, resolve_card_identifier


def test_resolve_by_id():
    card = resolve_card_identifier("020")
    assert card.id == "020"
    assert card.name.lower() == "archdragon"


def test_resolve_by_exact_name():
    card = resolve_card_identifier("Archdragon")
    assert card.id == "020"


def test_resolve_by_case_insensitive_name():
    card = resolve_card_identifier("archdragon")
    assert card.id == "020"


def test_unknown_name_raises_with_suggestion():
    try:
        resolve_card_identifier("Elphaduck")
    except CardResolveError as exc:
        msg = str(exc).lower()
        assert "elphadunk" in msg  # close match suggestion
    else:
        raise AssertionError("Expected CardResolveError")


def test_list_parsing_basic():
    cards = parse_card_list("queen bee, archdragon, levrikon, crawler, flan")
    ids = [c.id for c in cards]
    assert ids == ["005", "020", "007", "019", "018"]


def test_quantity_syntax():
    cards = parse_card_list("Queen Bee x2, Archdragon")
    ids = [c.id for c in cards]
    assert ids == ["005", "005", "020"]
