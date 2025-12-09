from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent

# Requested files for the qb_uxGPT knowledge bundle.
REQUESTED_PATHS = [
    Path("docs/coaching_design_spec.md"),
    Path("docs/enemy_observation_design_spec.md"),
    Path("docs/GPT_layer/gpt_effects_layer_note.md"),
    Path("docs/gpt_layer_design_overview.md"),
    Path("docs/prediction_design_spec_phase_E.md"),
    Path("data/qb_DB_Complete_v2.json"),
    Path("docs/qb_engine_test_playbook_v1.0.0.md"),
    Path("docs/qb_engine_v2.1.0.md"),
    Path("docs/qb_opponent_profile_red_xiii_v1.0.0.md"),
    Path("docs/qb_rules_v2.2.4.md"),
    Path("docs/qb_startup_self_diagnostic_v1.0.4.md"),
    Path("docs/red_xiii_rematch_deck_profile.md"),
    Path("docs/scoring_design_spec.md"),
    Path("docs/simulation_design_spec.md"),
    Path("docs/qb_uxGPT-Engine_interaction_contract_v1.0.md"),
    Path("docs/phase_G_self_test_v1.0.md"),
    Path("qb_engine/cli/README_live_cli.md"),
    Path("docs/qb_visualization_conventions_v1.0.0.md"),
    Path("docs/GPT_layer/gpt_live_coaching_protocol_v0.3.md"),
]


def build_default_output_path() -> Path:
    snapshots_dir = REPO_ROOT / "stateCurrent_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return snapshots_dir / f"qb_uxgpt_kb_{timestamp}.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bundle qb_uxGPT-facing docs and data into a zip.")
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


def split_existing_requested() -> tuple[list[Path], list[Path]]:
    present: list[Path] = []
    missing: list[Path] = []
    for rel_path in REQUESTED_PATHS:
        absolute = REPO_ROOT / rel_path
        if absolute.is_file():
            present.append(rel_path)
        else:
            missing.append(rel_path)
    return present, missing


def make_zip(output_path: Path, rel_paths: list[Path]) -> int:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in rel_paths:
            absolute = REPO_ROOT / rel_path
            zf.write(absolute, arcname=str(rel_path))
    return len(rel_paths)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    output_path = resolve_output_path(args.out)

    present, missing = split_existing_requested()
    if not present:
        print("Error: no requested files were found; nothing to bundle.")
        if missing:
            print("Missing files:")
            for rel in missing:
                print(f" - {rel}")
        sys.exit(1)

    count = make_zip(output_path, present)
    print(f"Bundled {count} files into {display_path(output_path)}")
    if missing:
        print("Skipped missing files:")
        for rel in missing:
            print(f" - {rel}")


if __name__ == "__main__":
    main()
