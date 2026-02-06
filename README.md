# COT_v1: Commitment of Traders Data Processing Pipeline

Clean rebuild of the COT-MVP pipeline with a modular structure and smoke tests.

## 📋 Project Overview

**COT_v1** — аналітична платформа для CFTC Legacy COT (Commitment of Traders) даних.

**Архітектура:** `canonical → semantic compute → wide view → UI`

**UI = viewer-only** — інтерфейс лише для читання та візуалізації обчислених метрик. Жодних розрахунків у UI-шарі.

⚠️ Виняток: у `Overview` є **admin** кнопка **Run compute**, яка локально запускає `ingest → normalize → compute`. Вона існує лише для ручного адміністрування.

## 🚀 Quick Start

### 1) Setup Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Run Pipeline

```powershell
python -m src.ingest.run_ingest --root . --log-level INFO
python -m src.normalize.run_normalize --root . --log-level INFO
python -m src.compute.run_compute --root . --log-level INFO
streamlit run src/app/app.py
```

### 3) Streamlit Community Cloud Deploy

Entry point for deploy:

```powershell
streamlit run app.py
```

Data directory:
- Uses `data/` only (production parquet).

Streamlit Cloud:
1) Push repo to GitHub (public).
2) New app → select repo/branch.
3) Main file path = `app.py`.
4) No environment variables required.

## 🏗️ Architecture Overview

```
INGEST (immutable)
  ↓
  Raw ZIP snapshots (data/raw/)

NORMALIZE (canonical parquet)
  ↓
  Canonical parquet (data/canonical/cot_weekly_canonical_full.parquet)

COMPUTE (semantic tables)
  ↓
  - positions_weekly.parquet
  - changes_weekly.parquet
  - flows_weekly.parquet
  - rolling_weekly.parquet
  - extremes_weekly.parquet
  - moves_weekly.parquet
  - metrics_weekly.parquet (wide view for UI)
  - data/compute/qa_report.txt (ERROR/WARN/INFO)

UI (read-only)
  ↓
  Streamlit dashboard
```

## 🧪 Smoke Tests

```powershell
pytest tests/ -v
pytest tests/test_ingest_smoke.py -v
pytest tests/test_normalize_smoke.py -v
pytest tests/test_compute_smoke.py -v
```

## 📌 Commands Reference

### Ingest
```powershell
python -m src.ingest.run_ingest --root . --start-year 2016 --end-year 2025 --log-level INFO
```

### Normalize
```powershell
python -m src.normalize.run_normalize --root . --log-level INFO
```

### Compute
```powershell
python -m src.compute.run_compute --root . --log-level INFO
```

### UI
```powershell
streamlit run src/app/app.py
```

### Recovery
Recovery instructions: see `_backup/RESTORE.md`

## 🔧 Dependencies

See `requirements.txt`:
- pandas>=2.2
- pyarrow>=16.0
- pyyaml>=6.0
- streamlit>=1.28.0
- requests>=2.31
- tenacity>=8.2
- numpy>=1.26

## 🧠 Project Philosophy

### Immutable Data
Дані завжди **read-only** після створення. Жодних мутацій у існуючих файлах.

### Snapshot-based Ingest
Ingest downloads CFTC ZIPs into immutable snapshots under `data/raw/legacy_futures_only/YYYY/` and records every attempt in `data/raw/manifest.csv`. For refresh years (current and previous), it checks for changes and writes `UNCHANGED` when the hash matches; for older years it skips unless the file is missing. `downloaded_at_utc` is the last successful update, `checked_at_utc` is the time of the check.

### No Hidden Mutations
Всі трансформації даних — явні:
- `ingest` → новий файл у `data/raw/`
- `normalize` → новий файл у `data/canonical/`
- `compute` → новий файл у `data/compute/`

### UI = Read-only до Compute
UI (`src/app/**`) **ніколи не міняє** дані. Тільки читання з `data/compute/`.
⚠️ Виняток: admin кнопка **Run compute** в `Overview` для локального запуску пайплайну.

## 📊 Data Contracts (Compute)

**Основний файл для UI:** `data/compute/metrics_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Артефакти Compute:**
- `data/compute/positions_weekly.parquet`
- `data/compute/changes_weekly.parquet`
- `data/compute/flows_weekly.parquet`
- `data/compute/rolling_weekly.parquet`
- `data/compute/extremes_weekly.parquet`
- `data/compute/moves_weekly.parquet`
- `data/compute/metrics_weekly.parquet`
- `data/compute/qa_report.txt`
- `data/compute/market_radar_latest.parquet`
- `data/compute/market_positioning_latest.parquet`

## 📊 Data Flow (детально)

### Крок 1: Ingest (raw)
```
CFTC Website → ZIP Snapshot → data/raw/legacy_futures_only/YYYY/deacotYYYY__YYYYMMDD_HHMMSS.zip
```
**Відповідальність:** `src/ingest/`

### Крок 2: Normalize (canonical)
```
Raw ZIP → Parser → QA Checks → Canonical Parquet → data/canonical/cot_weekly_canonical_full.parquet
```
**Відповідальність:** `src/normalize/`

### Крок 3: Compute (metrics)
```
Canonical Parquet → Semantic Tables → Wide Metrics → data/compute/metrics_weekly.parquet
```
**Відповідальність:** `src/compute/`

### Крок 4: UI (presentation)
```
Metrics → Read → Filter → Display → Streamlit
```
**Відповідальність:** `src/app/**`  
**UI reads:** `metrics_weekly.parquet`, `market_radar_latest.parquet`, `market_positioning_latest.parquet`

## 📋 File Responsibility Map

### `src/ingest/*` → Завантаження, Snapshots, Manifest
- `cftc_downloader.py` — завантаження ZIP з CFTC
- `manifest.py` — manifest (історія snapshot-ів)
- `run_ingest.py` — entrypoint ingest

### `src/normalize/*` → Парсинг, QA, Canonical Parquet
- `cot_parser.py` — парсинг CSV з RAW ZIP
- `qa_checks.py` — QA перевірки
- `run_normalize.py` — entrypoint normalize

### `src/compute/*` → **ВСІ РОЗРАХУНКИ**
- `run_compute.py` — entrypoint compute
- `build_*.py` — обчислення семантичних таблиць
- `validations.py` — валідації

### `src/app/*` → UI (read-only)
- `src/app/app.py` — main app + routing
- `src/app/pages/overview_mvp.py` — Overview сторінка
- `src/app/pages/market.py` — Market Radar сторінка

## 🔒 Versioning

Version constant: `src/app/ui_state.py` → `APP_VERSION = "COT_v1.2.9"`

## 📚 Related Documentation

- `README.md` — quick start, architecture overview, data contracts
- `_backup/RESTORE.md` — backup & restore procedures
- `docs/DEV_HANDOFF.md` — developer handoff guide
- `docs/ARCHITECTURE.md` — detailed architecture
- `docs/COMPUTE_METRICS.md` — compute metrics reference

---

**Rebuilt from:** cot-mvp (2026-01-08)  
**Current version:** v1.2.9 (2026-01-20)

## 📎 Release Notes

### v1.2.9 (2026-01-20)
- Entrypoint fix: `app.py` calls `src.app.app.main()` without import side effects.
- Overview fix: consistent routing between `app.py` and `src/app/app.py`.

### v1.2.8 (2026-01-20)
- Production lock: main uses `data/` only, no demo/fallback paths.
- Entry point: `app.py` is the Streamlit entrypoint for Cloud.
- Backups: code/data archives created in `_backup/` (v1.2.8 naming)

**Backup rule:** All backups stored in `_backup/` directory with naming format  
`COT_v1_code_YYYY-MM-DD__vX.Y.Z.zip` and `COT_v1_data_YYYY-MM-DD__vX.Y.Z.zip`

## Authentication Setup (DB + Roles/Statuses)

User accounts are stored in SQLite database (`data/app/auth.db` by default).

1) Set your admin email (this account gets admin permissions):

```powershell
$env:COT_ADMIN_EMAIL = "your_email@example.com"
```

2) Start app and register via UI (`Sign In -> Register`).
   If registered email equals `COT_ADMIN_EMAIL`, status is `active` and role is `admin`.
   Other new users are created with status `pending` and role `user`.

3) Admin opens sidebar `Admin` section to change user role/status:
   - Roles: `user`, `admin`
   - Statuses: `pending`, `active`, `disabled`

4) Optional Google login (requires Streamlit OIDC provider setup):

```powershell
$env:COT_ENABLE_GOOGLE_LOGIN = "true"
```
