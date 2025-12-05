#!/usr/bin/env python3
import os
import shutil
from datetime import datetime

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Where we store handoff snapshots
    handoff_root = os.path.join(project_root, "stateCurrent_codex_handoff")
    os.makedirs(handoff_root, exist_ok=True)

    # Timestamped folder & zip name
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(handoff_root, f"qbCoach_snapshot_{stamp}")
    os.makedirs(snapshot_dir, exist_ok=True)

    print(f"Creating snapshot at: {snapshot_dir}")

    # What to include
    items_to_copy = [
        "qb_engine",
        "data/qb_DB_Complete_v2.json",
        "docs",
    ]

    for item in items_to_copy:
        src = os.path.join(project_root, item)
        dst = os.path.join(snapshot_dir, item)

        if not os.path.exists(src):
            print(f"WARNING: {src} does not exist, skipping.")
            continue

        if os.path.isdir(src):
            print(f"Copying directory: {src} -> {dst}")
            shutil.copytree(src, dst)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            print(f"Copying file: {src} -> {dst}")
            shutil.copy2(src, dst)

    # Create a zip archive of the snapshot directory
    zip_base = os.path.join(handoff_root, f"qbCoach_snapshot_{stamp}")
    print(f"Creating zip archive: {zip_base}.zip")
    shutil.make_archive(zip_base, "zip", snapshot_dir)

    print("Done. Snapshot and zip created.")
    print("You can upload the zip file to a new ChatGPT/Codex session or store it as a handoff state.")

if __name__ == "__main__":
    main()
