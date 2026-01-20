# Copilot / AI Agent Instructions for COT_v1 🔧

Purpose: Give an AI agent the minimal, project-specific knowledge to be productive quickly—what to read, where to run things, and what rules to follow.

## Big picture
- Architecture: INGEST → NORMALIZE → COMPUTE → WIDE VIEW → UI (Streamlit). See `README.md` top-level diagram.
- Single-source-of-truth for UI: `data/compute/metrics_weekly.parquet` (UI reads only this file).
- Data is immutable: each pipeline step writes new files/snapshots (no in-place mutation).

## Key entrypoints (run locally in project root)
- Setup: `python -m venv .venv` + `.venv\Scripts\Activate.ps1` + `pip install -r requirements.txt`
- Ingest: `python -m src.ingest.run_ingest --root . --log-level INFO`
- Normalize: `python -m src.normalize.run_normalize --root . --log-level INFO`
- Compute: `python -m src.compute.run_compute --root . --log-level INFO`
- UI: `streamlit run src/app/app.py`
- Tests (smoke): `pytest tests/ -v` (or run a specific smoke test file)

## Project rules you must enforce (do not change)
- All heavy data calculations belong in `src/compute/`. Example: `src/compute/build_metrics.py`.
- UI code (`src/app/**`) is read-only: do not add calculations there. Example of forbidden edit: computing `nc_net` in `src/app/pages/overview_mvp.py` (should be present in compute outputs already).
- Ingest produces immutable timestamped ZIP snapshots under `data/raw/` and updates `data/raw/manifest.csv` (`src/ingest/*`).
- Normalization produces canonical parquet in `data/canonical/` (`src/normalize/*`).
- Compute produces semantic tables and the wide `metrics_weekly.parquet` in `data/compute/` (`src/compute/*`).

## Files & responsibilities (quick map)
- src/ingest/ — downloading, snapshot creation, manifest (`cftc_downloader.py`, `manifest.py`, `run_ingest.py`)
- src/normalize/ — parsing & QA to canonical parquet (`cot_parser.py`, `qa_checks.py`, `run_normalize.py`)
- src/compute/ — all metric calculations and validations (`build_metrics.py`, `validations.py`, `run_compute.py`)
- src/app/ — Streamlit UI, components & session state (`ui_state.py`, `pages/*.py`, `components/*`)
- configs/ — `markets.yaml`, `contracts_meta.yaml` (market/contract metadata used when joining/labeling)

## Typical development workflow for a metric change
1. Modify/add calculation logic in `src/compute/build_metrics.py` (or a new module under `src/compute/`).
2. Add/adjust validations in `src/compute/validations.py`.
3. Run `python -m src.compute.run_compute --root . --log-level INFO` and inspect `data/compute/metrics_weekly.parquet`.
4. Add or update a smoke test in `tests/` (follow existing smoke test pattern). Run `pytest tests/ -v`.
5. Open PR with code, tests, and a note describing the expected file outputs and any manifest/schema changes.

## Naming & data conventions to follow
- Semantic tables: `positions_weekly.parquet`, `changes_weekly.parquet`, `flows_weekly.parquet`, `rolling_weekly.parquet`, `extremes_weekly.parquet`, `moves_weekly.parquet`, `metrics_weekly.parquet`.
- Keys: `market_key`, `report_date` (Timestamp).
- Common column patterns (from README): `*_long`, `*_short`, `*_total`, `*_net`, `*_chg_1w`, `*_ma_13w`, `*_min_all`, `*_max_all`.

## Tests & debugging tips
- Smoke tests live in `tests/` and are intended to validate pipeline end-to-end for small sample data.
- Use `--log-level INFO/DEBUG` on run scripts for more verbose traceability.
- To inspect intermediate data, read parquet files in `data/canonical/` or `data/compute/`.

## Integration points & external deps
- External downloads: CFTC data via `src/ingest/cftc_downloader.py` (network dependency).
- Configs: `configs/markets.yaml` and `configs/contracts_meta.yaml` used to enrich/whitelist assets.
- Requirements: see `requirements.txt` (pandas, pyarrow, streamlit, tenacity, etc.).

## Quick examples (do / don’t)
- ✅ Correct: Add net calc in compute: `df['nc_net'] = df['nc_long'] - df['nc_short']` inside `src/compute/*.py`.
- ❌ Incorrect: computing `nc_net` inside `src/app/pages/*` (UI must read precomputed columns).

## When you are uncertain
- Look at `README.md` first — it contains architecture, commands, and data contracts.
- Inspect `src/compute/validations.py` for project validation rules and expected invariants.
- Ask maintainers about whether generated parquet should be committed or only produced by CI/local runs.

---
If anything here is unclear or incomplete, tell me which sections you'd like expanded (e.g., examples for adding a new semantic file, PR checklist, or sample smoke tests) and I will iterate. ✅
