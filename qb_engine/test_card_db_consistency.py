from qb_engine.card_hydrator import CardHydrator
from qb_engine.card_db_validator import pattern_to_grid


def test_all_cards_center_w():
    hydrator = CardHydrator()
    for entry in hydrator.db:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        grid = entry["grid"]
        assert grid[2][2] == "W", f"Card {entry['id']} center is not W"


def test_pattern_matches_grid_for_all_cards():
    hydrator = CardHydrator()
    for entry in hydrator.db:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        expected = pattern_to_grid(entry.get("pattern"))
        grid = entry["grid"]
        for r in range(5):
            for c in range(5):
                if expected[r][c] != ".":
                    assert grid[r][c] == expected[r][c], f"Card {entry['id']} mismatch at ({r},{c})"


def test_archdragon_pattern_grid_match():
    hydrator = CardHydrator()
    card = hydrator.get_card("020")
    expected = pattern_to_grid(card.pattern)
    for r in range(5):
        for c in range(5):
            if expected[r][c] != ".":
                assert card.grid[r][c] == expected[r][c]
