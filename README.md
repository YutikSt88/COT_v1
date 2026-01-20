# COT_v1: Commitment of Traders Data Processing Pipeline

**Clean rebuild** of COT-MVP pipeline with modular structure and smoke tests.

## 📋 Project Overview

**COT_v1** — аналітична платформа для CFTC Legacy COT (Commitment of Traders) даних.

**Архітектура:** `canonical → semantic compute → wide view → UI`

**UI = viewer-only** — інтерфейс тільки для читання та візуалізації обчислених метрик. Жодних розрахунків у UI-шарі.

??????????: ?????? `Run compute` ? Overview (admin) ????????? ????????? ? ???? ???????? compute; UI ?? ??????? ??????-??????????? ? ?? ?????? ???? ???????.

## 🚀 Quick Start

### 1. Setup Environment

```powershell
# Create venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Pipeline

```powershell
# Step 1: Ingest (download raw data)
python -m src.ingest.run_ingest --root . --log-level INFO

# Step 2: Normalize (parse and QA)
python -m src.normalize.run_normalize --root . --log-level INFO

# Step 3: Compute (build metrics and semantic tables)
python -m src.compute.run_compute --root . --log-level INFO

# Step 4: UI (Streamlit dashboard)
streamlit run src/app/app.py
```

### 3. Streamlit Community Cloud Deploy

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
  - ??: `python -m src.compute.run_compute` ??' ??????? semantic tables + wide metrics + QA OK
  - `positions_weekly.parquet` ? ?????? ??????? (nc/comm/nr: long, short, total, net)
  - `changes_weekly.parquet` ? ????? ?? ??????? (chg_1w)
  - `flows_weekly.parquet` ? flow/rotation (gross, net_abs, rotation, shares)
  - `rolling_weekly.parquet` ? 13-??????? ??????? (ma_13w)
  - `extremes_weekly.parquet` ? all-time ?? 5Y=260w
  - `moves_weekly.parquet` ? move percentiles (all-time)
  - `metrics_weekly.parquet` ? wide view ??? UI
  - `data/compute/qa_report.txt` ? QA ???? (ERROR/WARN)

- ✅ `streamlit run src/app/app.py` → dashboard opens and shows EUR/GBP/JPY/XAU

## 🧪 Smoke Tests

```powershell
# Run all smoke tests
pytest tests/ -v

# Run specific test
pytest tests/test_ingest_smoke.py -v
pytest tests/test_normalize_smoke.py -v
pytest tests/test_compute_smoke.py -v
```

## 📝 Commands Reference

### Ingest
```powershell
python -m src.ingest.run_ingest --root . --start-year 2016 --end-year 2025 --log-level INFO
```

### Normalize
```powershell
python -m src.normalize.run_normalize --root . --log-level INFO
```

Normalize output (canonical):
- File: `data/canonical/cot_weekly_canonical_full.parquet`
- Keys: `market_key`, `report_date`, `contract_code`
- Numeric fields: `open_interest_all`, `nc_long`, `nc_short`, `nc_net`, `comm_long`, `comm_short`, `comm_net`, `nr_long`, `nr_short`, `nr_net`
- Dates are true datetime (sortable), missing numeric values are filled with `0`
- Duplicates per (market_key, report_date, contract_code) are merged by sum over numeric fields
- Contracts list is auto-synced from `configs/contracts_meta.yaml` (enabled=true only)
- Normalize stops if any required column is missing in the raw file

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
??????????: ?????? `Run compute` ? Overview (admin) ????????? ????????? ? ???? ???????? compute; UI ?? ??????? ??????-??????????? ? ?? ?????? ???? ???????.
UI (`src/app/**`) **ніколи не міняє** дані. Тільки читання з `data/compute/` та відображення.

## 📊 Data Contracts

## Compute (semantic + wide)

**Основний файл для UI:** `data/compute/metrics_weekly.parquet`

**Ключі:** `market_key`, `report_date`

**Артефакти Compute:**
- `data/compute/positions_weekly.parquet` — long/short/total/net для nc/comm/nr.
- `data/compute/changes_weekly.parquet` — тижневі зміни (*_chg_1w).
- `data/compute/flows_weekly.parquet` — gross/net_abs/rotation/shares.
- `data/compute/rolling_weekly.parquet` — 13-тижневі середні.
- `data/compute/extremes_weekly.parquet` — all-time та 5Y (260w) min/max/pos, pos=0.5 при min==max.
- `data/compute/moves_weekly.parquet` — перцентилі абсолютних змін.
- `data/compute/metrics_weekly.parquet` — wide join для UI.
- `data/compute/qa_report.txt` — QA звіт (ERROR/WARN).

**Ключові групи колонок у metrics_weekly.parquet:**
- Positions: `nc_*`, `comm_*`, `nr_*` (long/short/total/net)
- Changes: `*_chg_1w`
- Flows: `*_gross_chg_1w`, `*_net_abs_chg_1w`, `*_rotation_1w`, `*_rotation_share_1w`, `*_net_share_1w`
- Rolling: `*_ma_13w`
- Extremes: `*_min_all`, `*_max_all`, `*_pos_all`, `*_min_5y`, `*_max_5y`, `*_pos_5y`
- Moves: `*_move_pct_all`
- OI: `open_interest`, `open_interest_chg_1w`, `open_interest_chg_1w_pct`, `open_interest_pct_all`, `open_interest_pct_5y`
- OI change: `open_interest_chg_pct_rank_all`, `open_interest_chg_pct_rank_5y`, `open_interest_chg_z_52w`, `open_interest_chg_z_260w`
- OI regime: `open_interest_regime_all`, `open_interest_regime_5y`, `open_interest_regime_strength_all`, `open_interest_regime_strength_5y`
- Deprecated (still present): `open_interest_pos_all`, `open_interest_pos_5y`
- OI-%: `nc_net_pct_oi`, `comm_net_pct_oi`, `nr_net_pct_oi`, `nc_flow_pct_oi_1w` + pos_all/pos_5y
- Додатково: `category`, `contract_code`, `spec_vs_hedge_net`, `spec_vs_hedge_net_chg_1w`
  
**UI heatline + shared scale:**
- Heatline для `*_chg_1w`: `*_chg_1w_min_all`, `*_chg_1w_max_all`, `*_chg_1w_pos_all`, `*_chg_1w_min_5y`, `*_chg_1w_max_5y`, `*_chg_1w_pos_5y`
- Спільна шкала `nc_net + comm_net`: `fc_net_min_all`, `fc_net_max_all`, `fc_net_pos_nc_all`, `fc_net_pos_comm_all`, `fc_net_min_5y`, `fc_net_max_5y`, `fc_net_pos_nc_5y`, `fc_net_pos_comm_5y`
- Спільна шкала `nc_net_chg_1w + comm_net_chg_1w`: `fc_net_chg_min_all`, `fc_net_chg_max_all`, `fc_net_chg_pos_nc_all`, `fc_net_chg_pos_comm_all`, `fc_net_chg_min_5y`, `fc_net_chg_max_5y`, `fc_net_chg_pos_nc_5y`, `fc_net_chg_pos_comm_5y`


## 📊 Data Flow (детально)

### Крок 1: Ingest (raw)
```
CFTC Website → ZIP Snapshot → data/raw/legacy_futures_only/YYYY/deacotYYYY__YYYYMMDD_HHMMSS.zip
```

**Відповідальність:** `src/ingest/`
- Завантаження ZIP файлів з CFTC
- Створення snapshots з timestamp
- Manifest: `data/raw/manifest.csv`
- Manifest fields: `downloaded_at_utc` = last update, `checked_at_utc` = check time
- **Результат:** Raw ZIP файли (immutable snapshots)

### Крок 2: Normalize (canonical)
```
Raw ZIP → Parser → QA Checks → Canonical Parquet → data/canonical/cot_weekly_canonical_full.parquet
```

**Відповідальність:** `src/normalize/`
- Парсинг RAW CSV з ZIP
- Нормалізація структури (COMM/NONCOMM/NONREPT)
- QA перевірки (день тижня, формати)
- **Результат:** Canonical parquet (normalized, immutable)

### Крок 3: Compute (metrics)
```
Canonical Parquet → Metrics Builder → Aggregations → Metrics Parquet → data/compute/metrics_weekly.parquet
```

**Відповідальність:** `src/compute/`
- Розрахунок всіх метрик (net, totals, 13W avg, extremes)
- Агрегації за market_key, report_date
- Валідація результатів
- **Результат:** Metrics parquet (all calculations done, immutable)

### Крок 4: UI (presentation)
```
Metrics Parquet → Read → Filter → Format → Display → Streamlit Dashboard
```

**Відповідальність:** `src/app/**`
- **ТІЛЬКИ читання** з `data/compute/metrics_weekly.parquet`
- Фільтрація за week, asset, category
- Форматування для відображення
- **Результат:** UI Dashboard (read-only presentation)

## 📋 File Responsibility Map

### `src/ingest/*` → Завантаження, Snapshots, Manifest
- `cftc_downloader.py` — завантаження ZIP з CFTC
- `manifest.py` — керування manifest (список snapshotів)
- `run_ingest.py` — entrypoint для ingest пайплайну
- **Відповідальність:** Створення raw snapshots, оновлення manifest

### `src/normalize/*` → Парсинг, QA, Canonical Parquet
- `cot_parser.py` — парсинг CSV з RAW ZIP
- `canonical_full_schema.py` — схема canonical даних
- `qa_checks.py` — QA перевірки (день тижня, формати)
- `run_normalize.py` — entrypoint для normalize пайплайну
- **Відповідальність:** Трансформація RAW → Canonical, QA перевірки

### `src/compute/*` → **ВСІ РОЗРАХУНКИ**
- `run_compute.py` — entrypoint для compute пайплайну
- `validations.py` — валідація результатів compute
- **Відповідальність:** **ЄДИНЕ місце для всіх обчислень** (net, extremes, 13W, all-time, 5Y)

### `src/app/pages/overview_mvp.py` → Тільки Читання Compute + UI
- Завантаження `data/compute/metrics_weekly.parquet`
- Фільтрація за week, asset
- Відображення: карточки, таблиці, графіки
- **Відповідальність:** **ТІЛЬКИ читання + presentation** (ніяких розрахунків!)

### `src/app/ui_state.py` → Session State, Version
- Керування `st.session_state` (category, asset, week_idx)
- Версія додатку (`APP_VERSION`)
- **Відповідальність:** UI state management, versioning

### `src/app/app.py` → Entrypoint, Routing
- Streamlit entrypoint
- Роутинг між сторінками (Market, Overview)
- **Відповідальність:** Запуск додатку, навігація

## ⚠️ Де МОЖНА і НЕ МОЖНА рахувати

### ❌ НЕ МОЖНА рахувати (UI Layer)

**`src/app/**` (всі файли)**
- `src/app/pages/overview_mvp.py` — тільки агрегації / presentation
- `src/app/components/*` — тільки UI компоненти
- `src/app/ui_state.py` — тільки session state

**Правило:** UI ніколи не робить обчислень. Тільки читання з `data/compute/` та відображення.

### ✅ МОЖНА рахувати (Compute Layer)

**`src/compute/**` (всі файли)**
- `src/compute/run_compute.py` — оркестрація compute пайплайну
- `src/compute/validations.py` — валідація результатів

**Правило:** Всі обчислення мають бути в `src/compute/`. UI читає готові результати.

### 📝 Приклади Правильних і Неправильних Підходів

#### ✅ Правильно (Compute Layer)
```python
def calculate_net_positions(df):
    df['nc_net'] = df['nc_long'] - df['nc_short']
    return df
```

#### ❌ Неправильно (UI Layer)
```python
# src/app/pages/overview_mvp.py
# ❌ НЕ робити так!
df['nc_net'] = df['nc_long'] - df['nc_short']  # Це має бути в compute!
```

#### ✅ Правильно (UI Layer)
```python
# src/app/pages/overview_mvp.py
# ✅ Читати готові результати
df = pd.read_parquet('data/compute/metrics_weekly.parquet')
net_val = df['nc_net'].iloc[0]  # Вже розраховано в compute
```

## 🎨 UI Layer Rules

### UI = Visualization Only

**Дозволено:**
- ✅ Читання з `data/compute/metrics_weekly.parquet`
- ✅ Slicing даних (фільтрація за week, asset, category)
- ✅ Форматування для відображення (rounding, thousand separators)
- ✅ Sparklines (візуалізація даних slice, не обчислення метрик)
- ✅ Агрегація готових метрик (sum, mean вже розрахованих колонок)

**Заборонено:**
- ❌ Розрахунок історичних метрик (rolling, extremes, net позиції)
- ❌ Обчислення змін за тиждень (chg_1w)
- ❌ Модифікація файлів у `data/`
- ❌ Створення нових parquet файлів

### Будь-який новий показник → Compute First

**Процес додавання нової метрики:**

1. **Додай розрахунок у `src/compute/`:**
   - Створи/онови модуль у `src/compute/build_*.py`
   - Розрахуй метрику з canonical або positions даних

2. **Онови `src/compute/run_compute.py`:**
   - Додай виклик нового модуля
   - Переконайся, що метрика потрапляє в `metrics_weekly.parquet`

3. **Запусти compute:**
   ```powershell
   python -m src.compute.run_compute --root . --log-level INFO
   ```

4. **Використовуй у UI:**
   - Читай готову колонку з `metrics_weekly.parquet`
   - Відображай у UI без додаткових обчислень

### Приклади Правильних і Неправильних Підходів

#### ✅ Правильно (UI Layer)
```python
# src/app/pages/overview_sections/snapshot.py
df = pd.read_parquet('data/compute/metrics_weekly.parquet')
row = df[df['market_key'] == 'EUR'].iloc[0]
net_val = row['nc_net']  # Вже розраховано в compute
```

#### ❌ Неправильно (UI Layer)
```python
# src/app/pages/overview_mvp.py
# ❌ НЕ робити так!
df['nc_net'] = df['nc_long'] - df['nc_short']  # Має бути в compute!
df['nc_net_13w'] = df.groupby('market_key')['nc_net'].rolling(13).mean()  # Має бути в compute!
```

## 🔖 Versioning

### Де зберігається версія
`src/app/ui_state.py`:
```python
APP_VERSION = "COT_v1.2.9"
```

### Коли міняється
Версія міняється після:
1. Завершення фічі (нові метрики, UI покращення)
2. Smoke-check UI (перевірка, що все працює)
3. Backup (створення ZIP з новою версією)

### Формат версій
`COT_v1.X.Y`
- `1` — major version (immutable data pipeline)
- `X` — minor version (нові метрики, UI покращення)
- `Y` — patch version (багфікси, поліпшення)

### Процес оновлення версії
1. Завершити фічу
2. Запустити smoke tests: `pytest tests/ -v`
3. Створити backup: `python scripts/backup_version.py`
4. Оновити `APP_VERSION` в `src/app/ui_state.py`
5. Commit / tag (якщо є git)

## 🎯 Key Features

- **Modular structure**: Each step is independent and testable
- **Smoke tests**: Quick validation that modules work
- **Clean imports**: `from src.ingest.run_ingest import main`
- **Canonical data**: `cot_weekly_canonical_full.parquet` (COMM/NONCOMM/NONREPT)
- **Metrics**: 144+ columns with positioning, OI, net metrics, extremes, 13W averages
- **Immutable pipeline**: No hidden mutations, all transformations explicit
- **Separation of concerns**: Compute vs UI layers strictly separated
- **Flow vs Rotation decomposition**: Weekly positioning structure analysis (v1.2.2)

## 📊 Weekly Positioning Structure (Flow vs Rotation)

**Секція "Weekly Positioning Structure (Flow vs Rotation)"** показує склад тижневої зміни позицій для кожної групи (Funds / Commercials / Non-Reported).

### Що показує блок

Для кожної групи (nc, comm, nr) відображається двосегментний бар:
- **Net component** (зелений/червоний) — напрямлений рух позицій
- **Rotation component** (жовтий) — внутрішній перелив long↔short без зміни загального напрямку

### Величини

- **Net Δ1w** — напрямлений рух (чистий прихід/вихід позицій)
- **Gross activity** — загальна активність (`|ΔLong| + |ΔShort|`)
- **Rotation** — частина gross без зміни net-напрямку (внутрішня ротація)

### Важливо

**UI нічого не рахує** — всі метрики обчислюються в compute шарі (`src/compute/build_flows.py`) та зберігаються в `metrics_weekly.parquet`. UI тільки читає готові значення та рендерить візуалізацію.

**Джерело даних:** `data/compute/metrics_weekly.parquet` (колонки `*_gross_chg_1w`, `*_net_abs_chg_1w`, `*_rotation_1w`, `*_net_share_1w`, `*_rotation_share_1w`)

## 🤖 Cursor Rules (для AI Assistant)

### Patch-only підхід
**ЗАВЖДИ** робити мінімальні зміни для досягнення мети. Виправляти тільки проблему, яку потрібно вирішити. НЕ рефакторити весь файл "з нуля".

### Не чіпати не зазначені файли
Якщо завдання чіпає `src/app/pages/overview_mvp.py`, то змінювати тільки цей файл. НЕ змінювати інші файли "на всяк випадок".

### Один logical change = один task
Розбивати складні задачі на менші:
- ✅ Задача 1: Додати метрику X в compute
- ✅ Задача 2: Відобразити метрику X в UI
- ❌ Задача: "Додати метрику X та зробити UI красивішим"

### Ніяких "refactor all"
**ЗАБОРОНЕНО:** "Refactor all UI code", "Clean up all files", "Optimize everything"  

### Завжди повертати Acceptance Checklist
Після виконання завдання обов'язково перевірити зміни та відповідність вимогам.

## 📐 Style Guide

### Мінімалізм
Код має бути простим і зрозумілим, без зайвих абстракцій. Явні рішення кращі за "елегантні".

### Читабельність
Код має бути читабельним без документації. Змінні та функції мають самодокументувальні назви.

### Без магії
Явні перетворення, без прихованої логіки. `int()` завжди явно, ніколи приховано.

### Без прихованих side-effects
Функції мають передбачувану поведінку. Якщо функція міняє `session_state`, це має бути явно.

---

## 📚 Related Documentation

- **README.md** (цей файл) — Quick start, architecture overview, data contracts, UI rules
- **_backup/RESTORE.md** — Backup & restore procedures, release flow, emergency restore (single source of truth)
- **docs/DEV_HANDOFF.md** — Developer handoff guide, Cursor rules, style guide
- **docs/ARCHITECTURE.md** — Detailed architecture, compute philosophy, UI vs compute rules
- **docs/COMPUTE_METRICS.md** — Compute metrics reference, Flow/Rotation metrics (v1.2.2)

---

**Rebuilt from:** cot-mvp (2026-01-08)  
**Current version:** v1.2.9 (2026-01-20)

## 📝 Release Notes



### v1.2.9 (2026-01-20)

- **Entrypoint fix**: `app.py` calls `src.app.app.main()` without import side effects.
- **Overview fix**: Consistent routing between `app.py` and `src/app/app.py`.

### v1.2.8 (2026-01-20)

- **Production lock**: main uses `data/` only, no demo/fallback paths.
- **Entry point**: `app.py` is the single Streamlit entrypoint.
- **Backups**: code/data archives created in `_backup/` (v1.2.8 naming)

### v1.2.7 (2026-01-20)

- **Version bump**: APP_VERSION updated to COT_v1.2.7
- **Backups**: code/data archives created in `_backup/` (v1.2.7 naming)

### v1.2.6 (2026-01-20)

- **Version bump**: APP_VERSION updated to COT_v1.2.6
- **Backups**: code/data archives created in `_backup/` (v1.2.6 naming)

### v1.2.5 (2026-01-19)

- **Version bump**: APP_VERSION updated to COT_v1.2.5
- **Backups**: code/data archives created in `_backup/` (v1.2.5 naming)

### v1.2.4 (2026-01-15)

- **UI version bump**: APP_VERSION updated to COT_v1.2.4
- **Backup archives**: Code/data archives created in `_backup/` (v1.2.4 naming)
- **UI compute button**: Exception documented for temporary admin use

### v1.2.3.1 (2026-01-13)

- **Market Open Interest card refined**: Improved visual hierarchy with gauge and sparkline alignment
- **UI improvements**: Enhanced Open Interest tab layout and positioning
- **Backup policy**: All backups stored in `_backup/` directory

### v1.2.3 (2026-01-11)

- **Market Traffic Light restored and finalized**: Added back to Positions tab with Funds/Commercials/Consensus cards
- **UI navigation reordered**: Positions → Open Interest → Charts → Table
- **Backup policy**: All backups stored in `_backup/` directory

**Backup rule:** All backups stored in `_backup/` directory with naming format `COT_v1_code_dataYYYY-MM-DD_vX.Y.Z.zip` and `COT_v1_data_dataYYYY-MM-DD_vX.Y.Z.zip`

