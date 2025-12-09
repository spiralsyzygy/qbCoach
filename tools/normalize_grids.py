from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List


def normalize_grid(grid: Any) -> Any:
    """
    Convert nested list grids to a compact inline form:
    [
      [".", ".", ".", ".", "."],
      ...
    ]
    Leaves non-list grids unchanged.
    """
    if not isinstance(grid, list):
        return grid
    if len(grid) != 5 or any(not isinstance(row, list) or len(row) != 5 for row in grid):
        return grid
    return [[str(cell) for cell in row] for row in grid]


def normalize_file(path: Path) -> None:
    data = json.load(path.open())
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and "grid" in entry:
                entry["grid"] = normalize_grid(entry["grid"])
    elif isinstance(data, dict) and "grid" in data:
        data["grid"] = normalize_grid(data["grid"])

    def is_inline_grid(value: Any) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 5
            and all(isinstance(row, list) and len(row) == 5 for row in value)
        )

    def format_value(val: Any, indent: int) -> str:
        pad = " " * indent
        if is_inline_grid(val):
            rows = []
            for row in val:
                row_repr = ", ".join(json.dumps(cell, ensure_ascii=False) for cell in row)
                rows.append(f"{pad}  [{row_repr}]")
            return "[\n" + ",\n".join(rows) + f"\n{pad}]"
        if isinstance(val, dict):
            items = []
            for idx, (k, v) in enumerate(val.items()):
                rendered = f'{pad}  {json.dumps(k, ensure_ascii=False)}: {format_value(v, indent + 2)}'
                items.append(rendered)
            return "{\n" + ",\n".join(items) + f"\n{pad}}}"
        if isinstance(val, list):
            items = [format_value(item, indent + 2) for item in val]
            if not items:
                return "[]"
            return "[\n" + ",\n".join(f"{' ' * (indent + 2)}{item}" for item in items) + f"\n{pad}]"
        return json.dumps(val, ensure_ascii=False)

    rendered = format_value(data, 0) + "\n"
    path.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize 5x5 grids to inline readable rows in a JSON file.")
    parser.add_argument("json_path", type=Path, help="Path to the JSON file to normalize.")
    args = parser.parse_args()

    json_path = args.json_path
    if not json_path.exists():
        raise SystemExit(f"File not found: {json_path}")

    normalize_file(json_path)
    print(f"Normalized grids in {json_path}")


if __name__ == "__main__":
    main()
