# qb_engine/test_hydration.py

from qb_engine.card_hydrator import CardHydrator


def test_hydrates_security_officer():
    hydrator = CardHydrator()

    card = hydrator.get_card("001")

    assert card.id == "001"
    assert card.name == "Security Officer"
    assert card.cost == 1
    assert card.power == 1
    assert card.pattern == "B3P,C2P,C4P,D3P"
    assert card.effect == ""

    # Ensure the projected grid shape and key cells match the DB record.
    assert len(card.grid) == 5
    assert all(len(row) == 5 for row in card.grid)
    assert card.grid[1][2] == "P"
    assert card.grid[2][2] == "W"
    assert card.grid[2][1] == "P"
    assert card.grid[2][3] == "P"
    assert card.grid[3][2] == "P"


if __name__ == "__main__":
    test_hydrates_security_officer()
    print("test_hydrates_security_officer: PASS")
