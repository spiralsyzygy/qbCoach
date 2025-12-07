#!/usr/bin/env python3
"""
Create lean, phase-aware snapshots for ChatGPT/Codex handoffs.

Defaults:
- Includes active engine/docs/data and pytest.ini.
- Excludes archives, virtualenvs, git, __pycache__, previous snapshots, and OS junk.
- Names archives qbCoach_snapshot_YYYYMMDD_HHMMSS[_phase-<PHASE>][_<label>].zip

Usage examples:
- python tools/archive_state.py --phase D --label post-enemy-observation
- python tools/archive_state.py --dry-run
- python tools/archive_state.py --include-extra notes/todo.md
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import zipfile


DEFAULT_INCLUDE_PATHS = [
    Path("data/qb_DB_Complete_v2.json"),
    Path("data/qb_effects_v1.1.json"),
    Path("docs/qb_rules_v2.2.4.md"),
    Path("docs/qb_engine_v2.1.0.md"),
    Path("docs/scoring_design_spec.md"),
    Path("docs/simulation_design_spec.md"),
    Path("docs/enemy_observation_design_spec.md"),
    Path("docs/qb_engine_test_playbook_v1.0.0.md"),
    Path("docs/qb_visualization_conventions_v1.0.0.md"),
    Path("docs/qb_developer_notes_v1.0.0.md"),
    Path("docs/workflow_primer.md"),
    Path("docs/roadmap.md"),
    Path("docs/PROJECT_INDEX.md"),
    Path("qb_engine"),
    Path("pytest.ini"),
    Path("tools/archive_state.py"),
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "stateCurrent_snapshots",
    "snapshots",
    "archive",
    "docs_archive",
}

EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create lean project snapshots.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("stateCurrent_snapshots"),
        help="Directory to write snapshots (default: stateCurrent_snapshots/).",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="Phase tag for naming (e.g., C, D, E).",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional label appended to the archive name.",
    )
    parser.add_argument(
        "--include-extra",
        action="append",
        dest="extras",
        default=[],
        help="Additional paths to include (relative to repo root). Can be repeated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be included without creating an archive.",
    )
    return parser.parse_args()


def should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix in {".pyc"}:
        return True
    return False


def collect_files(root: Path, include_paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for rel in include_paths:
        abs_path = root / rel
        if not abs_path.exists():
            continue
        if abs_path.is_file():
            if not should_exclude(abs_path.relative_to(root)):
                files.append(abs_path)
            continue
        # Directory walk
        for p in abs_path.rglob("*"):
            if p.is_dir():
                if should_exclude(p.relative_to(root)):
                    # skip walking excluded directories
                    continue
                continue
            rel_p = p.relative_to(root)
            if should_exclude(rel_p):
                continue
            files.append(p)
    return sorted(set(files))


def build_snapshot_name(stamp: str, phase: str | None, label: str | None) -> str:
    name = f"qbCoach_snapshot_{stamp}"
    if phase:
        name += f"_phase-{phase}"
    if label:
        name += f"_{label}"
    return name


def create_archive(root: Path, files: list[Path], output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{name}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.relative_to(root))
    return archive_path


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = build_snapshot_name(stamp, args.phase, args.label)

    include_paths = list(DEFAULT_INCLUDE_PATHS)
    for extra in args.extras:
        include_paths.append(Path(extra))

    files = collect_files(project_root, include_paths)

    if args.dry_run:
        print(f"[dry-run] Would include {len(files)} files:")
        for f in files:
            print(f"  {f.relative_to(project_root)}")
        return

    archive_path = create_archive(project_root, files, args.output_dir, snapshot_name)
    print(f"Snapshot created: {archive_path}")
    print(f"Files included: {len(files)}")


if __name__ == "__main__":
    main()
