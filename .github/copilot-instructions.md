# Copilot / AI Agent Instructions for COT_v1

Purpose: minimal, project-specific knowledge to be productive quickly.

## Big picture
- Architecture: INGEST → NORMALIZE → COMPUTE → WIDE VIEW → UI.
- Single source of truth for UI: `data/compute/metrics_weekly.parquet`.
- Data is immutable: each pipeline step writes new files/snapshots.

## Key entrypoints (run in repo root)
- Setup: `python -m venv .venv` + `.venv\Scripts\Activate.ps1` + `pip install -r requirements.txt`
- Ingest: `python -m src.ingest.run_ingest --root . --log-level INFO`
- Normalize: `python -m src.normalize.run_normalize --root . --log-level INFO`
- Compute: `python -m src.compute.run_compute --root . --log-level INFO`
- UI (local): `streamlit run src/app/app.py`
- UI (Cloud): `streamlit run app.py`
- Tests (smoke): `pytest tests/ -v`

## Project rules (do not change)
- All heavy calculations belong in `src/compute/`.
- UI code (`src/app/**`) is read-only for data (no metric calculations).
- Ingest produces immutable ZIP snapshots under `data/raw/` + updates `data/raw/manifest.csv`.
- Normalize produces canonical parquet in `data/canonical/`.
- Compute produces semantic tables + `metrics_weekly.parquet` in `data/compute/`.
- Markets config is generated from `configs/contracts_meta.yaml` via `src/common/markets_sync.py`.

## Files & responsibilities (quick map)
- `src/ingest/` — downloading, snapshots, manifest
- `src/normalize/` — parsing + QA to canonical parquet
- `src/compute/` — all metric calculations + validations
- `src/app/` — Streamlit UI
- `configs/` — `markets.yaml`, `contracts_meta.yaml`

## Metric changes (workflow)
1) Update or add logic in `src/compute/build_*.py`.
2) Update validations in `src/compute/validations.py`.
3) Run compute and inspect `data/compute/metrics_weekly.parquet`.
4) Update smoke tests if needed.

## Quick do / don’t
- ✅ Compute: `df['nc_net'] = df['nc_long'] - df['nc_short']` inside `src/compute/*`.
- ❌ UI: computing `nc_net` inside `src/app/pages/*`.
