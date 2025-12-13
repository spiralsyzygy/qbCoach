from __future__ import annotations

from pathlib import Path
from typing import List

from qb_engine.card_hydrator import CardHydrator, parse_pattern
from qb_engine.models import ProjectionCell


def pattern_to_grid(pattern: str | None) -> list[list[str]]:
    """Render a 5x5 visual grid from a pattern string."""
    grid = [["."] * 5 for _ in range(5)]
    grid[2][2] = "W"
    for cell in parse_pattern(pattern):
        if cell.symbol == "W":
            continue
        row_index = 2 + cell.row_offset
        col_index = 2 + cell.col_offset
        if 0 <= row_index < 5 and 0 <= col_index < 5:
            grid[row_index][col_index] = cell.symbol
    return grid


def validate_db(db_path: Path | None = None) -> None:
    """
    Validate that every card's grid agrees with its pattern on non-dot cells
    and that the center is W.
    Raises ValueError on first mismatch.
    """
    hydrator = CardHydrator(db_path.as_posix() if db_path else None)
    for card_id, entry in hydrator.index.items():
        grid = entry["grid"]
        if grid[2][2] != "W":
            raise ValueError(f"Card {card_id} center is not W")
        expected = pattern_to_grid(entry.get("pattern"))
        for r in range(5):
            for c in range(5):
                if expected[r][c] != "." and grid[r][c] != expected[r][c]:
                    raise ValueError(
                        f"Card {card_id} pattern/grid mismatch at ({r},{c}): "
                        f"expected {expected[r][c]} got {grid[r][c]}"
                    )


__all__ = ["pattern_to_grid", "validate_db"]
