"""
Export a flat qb_uxGPT Phase H bundle for the ChatGPT Custom GPT Knowledge Base.
Notes:
- Custom GPT Knowledge uploads are capped at 20 files, so this export flattens
  everything to depth 1 (basename only) and errors on name collisions.
- Phase H onboarding is merged into a single phase_H_onboarding_packet.md to stay
  within the limit while keeping the packet available by default.
- v0.4 of the live coaching protocol is the canonical reference; v0.3 is excluded
  to prevent downgrades.
- Directories are disallowed in the output to satisfy the Knowledge uploader.

Example usage:
python tools/export_qb_uxGPT_kb.py --list
python tools/export_qb_uxGPT_kb.py --verify --latest
python tools/export_qb_uxGPT_kb.py --latest
python tools/export_qb_uxGPT_kb.py --out stateCurrent_snapshots/qb_uxgpt_kb_custom.zip
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path, PurePosixPath
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent

# Required Phase H defaults (flattened to basename in the bundle).
REQUIRED_CORE_PATHS = [
    Path("docs/qb_rules_v2.2.4.md"),
    Path("data/qb_DB_Complete_v2.json"),
    Path("data/qb_effects_v1.1.json"),
    Path("docs/qb_visualization_conventions_v1.0.0.md"),
    Path("docs/qb_engine_v2.1.0.md"),
    Path("docs/qbcoach_gpt_primer.md"),
    Path("docs/GPT_layer/gpt_layer_design_overview.md"),
    Path("docs/GPT_layer/gpt_live_coaching_protocol_v0.4.md"),
    Path("docs/GPT_layer/phase_H_onboarding_packet.md"),
    Path("qb_engine/cli/README_live_cli.md"),
    Path("docs/GPT_layer/qb_uxGPT_KNOWLEDGE_INDEX.md"),
]

# Optional defaults: included if present but never fail verification.
OPTIONAL_DEFAULT_PATHS = [
    Path("docs/coaching_design_spec.md"),
]

DEFAULT_INCLUDE_PATHS = REQUIRED_CORE_PATHS + OPTIONAL_DEFAULT_PATHS

# Live coaching protocol v0.4 is canonical; v0.3 and effects note are excluded to
# avoid regressions. Any archive content is also excluded to keep the bundle lean.
DEFAULT_EXCLUDE_GLOBS = [
    "docs/GPT_layer/gpt_live_coaching_protocol_v0.3.md",  # superseded by v0.4
    "docs/GPT_layer/gpt_effects_layer_note.md",  # deprecated effects note
    "docs/qb_engine_test_playbook_v1.0.0.md",
    "docs/docs_archive/**",
    "docs/GPT_layer/GPT_layer_archive/**",
    "**/__pycache__/**",
    "**/*.pyc",
]


def build_default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "stateCurrent_snapshots" / f"qb_uxgpt_kb_{timestamp}.zip"


def build_latest_output_path() -> Path:
    return REPO_ROOT / "stateCurrent_snapshots" / "qb_uxgpt_kb_latest.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bundle qb_uxGPT-facing docs and data into a flat zip.")
    parser.add_argument("--out", type=str, help="Optional output zip path, relative to the repo root.")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Write to stateCurrent_snapshots/qb_uxgpt_kb_latest.zip (overwrite if exists).",
    )
    parser.add_argument("--list", dest="list_only", action="store_true", help="Print resolved file list only.")
    parser.add_argument("--verify", action="store_true", help="Fail if required core content is missing.")
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional file or directory to include (repeatable).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob to exclude after defaults and includes are gathered (repeatable).",
    )
    return parser.parse_args()


def resolve_output_path(out_arg: str | None, latest: bool) -> Path:
    if out_arg and latest:
        raise SystemExit("Use either --out or --latest, not both.")
    if latest:
        return build_latest_output_path()
    if out_arg:
        out_path = Path(out_arg)
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        return out_path
    return build_default_output_path()


def normalize_to_repo(path_value: str | Path) -> Path:
    path = Path(path_value)
    resolved = (path if path.is_absolute() else REPO_ROOT / path).resolve(strict=False)
    try:
        return resolved.relative_to(REPO_ROOT)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Path {resolved} is outside the repository root {REPO_ROOT}") from exc


def collect_files(requested_paths: list[Path]) -> tuple[set[Path], list[Path]]:
    files: set[Path] = set()
    missing: list[Path] = []
    for rel_path in requested_paths:
        absolute = REPO_ROOT / rel_path
        if absolute.is_file():
            files.add(rel_path)
        elif absolute.is_dir():
            for child in absolute.rglob("*"):
                if child.is_file():
                    files.add(child.relative_to(REPO_ROOT))
        else:
            missing.append(rel_path)
    return files, missing


def should_exclude(path: Path, exclude_globs: list[str]) -> bool:
    posix_path = path.as_posix()
    if "archive" in posix_path.lower():
        return True
    return any(PurePosixPath(posix_path).match(glob) for glob in exclude_globs)


def apply_excludes(paths: set[Path], exclude_globs: list[str]) -> tuple[set[Path], set[Path]]:
    kept: set[Path] = set()
    excluded: set[Path] = set()
    for path in paths:
        if should_exclude(path, exclude_globs):
            excluded.add(path)
        else:
            kept.add(path)
    return kept, excluded


def flatten_files(paths: set[Path]) -> dict[str, Path]:
    flat: dict[str, Path] = {}
    for path in paths:
        name = path.name
        if name in flat and flat[name] != path:
            raise SystemExit(
                f"Name collision when flattening: {name} from {flat[name]} conflicts with {path}. "
                "Rename one of the files or exclude one entry."
            )
        flat[name] = path
    return dict(sorted(flat.items(), key=lambda item: item[0]))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_zip(output_path: Path, flat_files: dict[str, Path]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, rel_path in flat_files.items():
            absolute = REPO_ROOT / rel_path
            zf.write(absolute, arcname=arcname)
    return len(flat_files)


def print_summary(
    included_files: dict[str, Path],
    required_missing: list[Path],
    excluded_files: set[Path],
    output_path: Path,
    list_only: bool,
    output_written: bool,
) -> None:
    print(f"Included files: {len(included_files)}")
    print(f"Required missing: {len(required_missing) if required_missing else 'none'}")
    print(f"Excluded files: {len(excluded_files)}")
    print("Flattening: enabled (depth = 1)")
    if list_only:
        print("Output: n/a (--list)")
    elif not output_written:
        print(f"Output: {display_path(output_path)} (not written)")
    else:
        print(f"Output: {display_path(output_path)}")


def main() -> None:
    args = parse_args()
    output_path = resolve_output_path(args.out, args.latest)
    exclude_globs = DEFAULT_EXCLUDE_GLOBS + args.exclude

    requested_paths: list[Path] = list(DEFAULT_INCLUDE_PATHS)
    try:
        requested_paths.extend(normalize_to_repo(path_str) for path_str in args.include)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    included_files, missing_requested = collect_files(requested_paths)
    filtered_files, excluded_files = apply_excludes(included_files, exclude_globs)
    flat_files = flatten_files(filtered_files)

    required_missing = [path for path in REQUIRED_CORE_PATHS if path not in filtered_files]
    optional_missing = {path for path in OPTIONAL_DEFAULT_PATHS if path in missing_requested}
    missing_non_optional = [path for path in missing_requested if path not in optional_missing]

    if missing_non_optional:
        print("Missing requested paths:")
        for rel in missing_non_optional:
            print(f" - {rel}")

    if required_missing:
        print("Missing required core files:")
        for rel in required_missing:
            print(f" - {rel}")

    if not flat_files:
        print("Error: no files to include after applying filters.")
        sys.exit(1)

    verification_failed = args.verify and bool(required_missing)

    output_written = False
    if args.list_only:
        for arcname in flat_files.keys():
            print(arcname)
    elif not verification_failed:
        write_zip(output_path, flat_files)
        output_written = True
    else:
        print("Skipping zip write because --verify failed.")

    print_summary(
        flat_files,
        required_missing,
        excluded_files,
        output_path,
        args.list_only,
        output_written,
    )

    if verification_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
