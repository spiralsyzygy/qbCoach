from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    Path("docs/PROJECT_INDEX.md"),
    Path("docs/qb_rules_v2.2.4.md"),
    Path("docs/qb_engine_v2.1.0.md"),
    Path("docs/qb_effects_v1.1_status.md"),
    Path("docs/scoring_design_spec.md"),
    Path("docs/simulation_design_spec.md"),
    Path("docs/enemy_observation_design_spec.md"),
    Path("docs/prediction_design_spec_phase_E.md"),
    Path("docs/coaching_design_spec.md"),
    Path("docs/qb_engine_test_playbook_v1.0.0.md"),
    Path("docs/qb_visualization_conventions_v1.0.0.md"),
    Path("docs/qbcoach_gpt_primer.md"),
    Path("docs/roadmap.md"),
    Path("docs/phase_G_milestone_map.md"),
    Path("docs/gpt_layer_design_overview.md"),
    Path("docs/GPT_layer/chatGPT+Codex_dual_initialization.md"),
    Path("docs/GPT_layer/gpt_live_coaching_protocol_v0.2.md"),
    Path("docs/GPT_layer/gpt_effects_layer_note.md"),
    Path("data/qb_DB_Complete_v2.json"),
    Path("data/qb_effects_v1.1.json"),
]


def build_default_output_path() -> Path:
    """Create the default snapshot path under stateCurrent_snapshots/."""
    snapshots_dir = REPO_ROOT / "stateCurrent_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return snapshots_dir / f"chatgpt_docs_{timestamp}.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bundle ChatGPT-facing docs and data into a zip.")
    parser.add_argument(
        "--out",
        type=str,
        help="Optional output zip path, relative to the repo root.",
    )
    return parser.parse_args()


def resolve_output_path(out_arg: str | None) -> Path:
    if out_arg:
        output_path = Path(out_arg)
        if not output_path.is_absolute():
            output_path = REPO_ROOT / output_path
    else:
        output_path = build_default_output_path()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def check_required_files() -> list[Path]:
    """Return a list of missing required files."""
    missing = []
    for rel_path in REQUIRED_PATHS:
        absolute = REPO_ROOT / rel_path
        if not absolute.is_file():
            missing.append(rel_path)
    return missing


def make_zip(output_path: Path) -> int:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in REQUIRED_PATHS:
            absolute = REPO_ROOT / rel_path
            zf.write(absolute, arcname=str(rel_path))
    return len(REQUIRED_PATHS)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    output_path = resolve_output_path(args.out)

    missing = check_required_files()
    if missing:
        print("Error: missing required files:")
        for rel_path in missing:
            print(f" - {rel_path}")
        sys.exit(1)

    count = make_zip(output_path)
    print(f"Bundled {count} files into {display_path(output_path)}")


if __name__ == "__main__":
    main()
