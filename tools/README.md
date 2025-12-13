# Tools Directory

Helper scripts for packaging, debugging, and data hygiene. Commands assume repo root as CWD; add `python3` if `python` is unavailable.

## analyze_live_jsonl_tile_timeline.py
Trace a single board tile across a live session JSONL log and show only the snapshots where it changed (or all snapshots on request).
- Example: `python tools/analyze_live_jsonl_tile_timeline.py logs/live/<file>.jsonl --tile BOT-3 --show-delta --show-events`
- JSON output: `--format json`; show all snapshots: `--show-all`; limit rows: `--limit N`.
- Alternative coords: `--lane 2 --col 2` (engine indices).

## analyze_live_jsonl_board_diff.py
Diff consecutive board states in a live JSONL to find divergence points and multi-tile changes.
- Example: `python tools/analyze_live_jsonl_board_diff.py logs/live/<file>.jsonl`
- Focus a tile: `--focus-tile BOT-3`; filter by lane: `--focus-lane BOT`; only owner flips to Y/E/N: `--focus-owner Y`.
- Show no-ops and hand/session deltas: `--show-all --include-nonboard`; JSON output: `--format json`; cap rows: `--limit N`.

## archive_state.py
Create a lean, phase-aware snapshot zip for handoff.
- Default: includes core engine/docs/data; skips archives, venvs, git, cached files.
- Examples:
  - `python tools/archive_state.py --dry-run`
  - `python tools/archive_state.py --phase H --label live-cli-sync`
  - `python tools/archive_state.py --include-extra notes/todo.md`

## export_chatgpt_docs.py
Bundle legacy ChatGPT-facing docs/data (Phase G defaults) into a zip.
- Default output: `stateCurrent_snapshots/chatgpt_docs_<timestamp>.zip`
- Custom path: `--out my_bundle.zip`

## export_qb_uxGPT_kb.py
Export the Phase H qb_uxGPT KB as a flat (depth=1) zip for Custom GPT Knowledge (20-file cap).
- Examples:
  - `python tools/export_qb_uxGPT_kb.py --verify --list` (show flattened filenames)
  - `python tools/export_qb_uxGPT_kb.py --latest` (writes `qb_uxgpt_kb_latest.zip`)
  - `python tools/export_qb_uxGPT_kb.py --include extra.md --exclude '*.tmp'`
- Required core must exist under `--verify`; directories are flattened to basenames; name collisions abort.

## fix_pattern_grid_mismatches.py
Align each card’s 5×5 grid with its pattern-derived grid, overwriting mismatches.
- Default DB: `data/qb_DB_Complete_v2.json`; custom via positional arg.
- Log corrections: `--log logs/grid_fixes.txt`

## normalize_grids.py
Normalize 5×5 grids in a JSON file to consistent inline list form for readability/diffs.
- Example: `python tools/normalize_grids.py data/qb_DB_Complete_v2.json`
