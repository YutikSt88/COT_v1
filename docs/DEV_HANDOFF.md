# COT_v1: Developer Handoff Guide

**Internal playbook** для розробників, які працюють з проєктом COT_v1.

## 🎯 Мета документації

Цей документ створений, щоб:
- Новий розробник не зламав compute
- UI не перетворився на data-kitchen
- Проєкт можна було підтримувати роками

---

## 🧩 Cursor Rules (для AI Assistant)

### Patch-only підхід

**ЗАВЖДИ** робити мінімальні зміни для досягнення мети:
- Виправляти тільки проблему, яку потрібно вирішити
- НЕ рефакторити весь файл "з нуля"
- НЕ видаляти існуючий код без явної причини

### Не чіпати не зазначені файли

Якщо завдання чіпає `src/app/pages/overview_mvp.py`, то:
- ✅ Змінювати тільки `overview_mvp.py`
- ❌ НЕ рефакторити інші файли "для чистого коду"

### Один logical change = один task

Розбивати складні задачі на менші:
- ✅ Задача 1: Додати метрику X в compute
- ✅ Задача 2: Відобразити метрику X в UI
- ❌ Задача: "Додати метрику X та зробити UI красивішим"

### Ніяких "refactor all"

**ЗАБОРОНЕНО:**
- "Refactor all UI code"
- "Clean up all files"
- "Optimize everything"

**ДОЗВОЛЕНО:**
- "Fix bug in overview_mvp.py: line 342"

### Завжди повертати Acceptance Checklist

Після виконання завдання **обов'язково** перевірити:
- ✅ Зміни відповідають вимогам
- ✅ Немає зламаного функціоналу
- ✅ Код не змінювався (якщо завдання про документацію)
- ✅ Дані не змінювались (якщо завдання про UI)

---

## 📐 Style Guide

### Мінімалізм

**Правило:** Код має бути простим і зрозумілим, без зайвих абстракцій.

```python
# ✅ Добре: простий і зрозумілий код
def get_week_index(weeks, week):
    for i, w in enumerate(weeks):
        if w == week:
            return i
    return len(weeks) - 1

# ❌ Погано: надмірна абстракція
class WeekIndexFinder:
    def __init__(self, weeks):
        self.weeks = weeks
        self.index_map = {w: i for i, w in enumerate(weeks)}
    
    def find(self, week):
        return self.index_map.get(week, len(self.weeks) - 1)
```

### Читабельність

**Правило:** Код має бути читабельним без документації.

```python
# ✅ Добре: зрозуміло з контексту
nc_net = nc_long - nc_short

# ❌ Погано: незрозуміло без коментарів
result = a - b  # Що це?
```

### Без магії

**Правило:** Явні перетворення, без прихованої логіки.

```python
# ✅ Добре: явна конвертація
week_idx = int(st.session_state[week_idx_key])

# ❌ Погано: прихована конвертація
week_idx = st.session_state[week_idx_key]  # Може бути str!
```

### Без прихованих side-effects

**Правило:** Функції мають передбачувану поведінку.

```python
# ✅ Добре: явний side-effect
def update_week_index(new_idx):
    st.session_state[week_idx_key] = new_idx
    st.rerun()

# ❌ Погано: прихований side-effect
def get_week_index():
    # Невідомо, що це може міняти session_state!
    if week_idx_key not in st.session_state:
        st.session_state[week_idx_key] = 0
    return st.session_state[week_idx_key]
```

---

## 🏗️ Architecture Rules

### Compute Layer (src/compute/**)

**Відповідальність:** Всі обчислення, метрики, агрегації.

**Може:**
- Читати з `data/canonical/`
- Писати в `data/compute/`
- Розраховувати метрики (net, totals, 13W avg, extremes)

**Не може:**
- Читати з `data/compute/` (свої власні результати)
- Модифікувати UI
- Зберігати session state

### UI Layer (src/app/**)
??????????: ?????? `Run compute` ? Overview (admin) ????????? ????????? ? ???? ???????? compute; UI ?? ??????? ??????-??????????? ? ?? ?????? ???? ???????.

**Відповідальність:** Читання compute + presentation.

**Може:**
- Читати з `data/compute/`
- Фільтрувати дані для відображення
- Форматувати для UI (rounding, formatting)
- Зберігати session state (week_idx, asset, category)

**Не може:**
- Писати в `data/`
- Розраховувати метрики (net, extremes, 13W avg)
- Модифікувати canonical/compute дані

### Ingest Layer (src/ingest/**)

**Responsibility:** Download raw CFTC ZIPs, create immutable snapshots, append manifest history.

**How to run:**
- `python -m src.ingest.run_ingest --root . --log-level INFO`
- Optional: `--start-year` / `--end-year` to limit the range

**How to debug:**
- Check the latest rows in `data/raw/manifest.csv` (status OK/UNCHANGED/ERROR)
- If `ERROR`, read the `error` column and rerun (network or CFTC availability issues are common)
- If `UNCHANGED`, verify `checked_at_utc` was updated and `raw_path` still exists
- If a file is missing on disk, the next run should restore it

**Notes:**
- `checked_at_utc` is written for every new OK/UNCHANGED/ERROR row; old rows may be empty until backfilled
- Old raw files are removed only during historical migration (after successful copy)

**Do not:**
- Edit or overwrite existing snapshots in `data/raw/`
- Remove manifest history entries

### Normalize Layer (src/normalize/**)

**Responsibility:** Parse RAW ZIP -> canonical parquet + QA.

**Reads:** `data/raw/` (ZIP snapshots)

**Writes:** `data/canonical/cot_weekly_canonical_full.parquet`, `data/canonical/qa_report.txt`

**Contract source:** `configs/contracts_meta.yaml` -> auto-sync to `configs/markets.yaml` (enabled=true only)

**Canonical keys:** `market_key`, `report_date`, `contract_code`

**Canonical numeric fields:**
- `open_interest_all`
- `nc_long`, `nc_short`, `nc_net`
- `comm_long`, `comm_short`, `comm_net`
- `nr_long`, `nr_short`, `nr_net`

**Rules:**
- Dates are parsed to true datetime (sortable)
- Missing numeric values are filled with `0`
- Duplicates are merged by `(market_key, report_date, contract_code)` using sum over numeric fields
- `contract_code` may include letters or `+`

**QA rules (canonical):**
- Critical (stop pipeline): missing required columns, missing `report_date`, empty output
- Warning (continue): negative `open_interest_all`

**Sync call sites:**
- `src/ingest/run_ingest.py` (start of `main`)
- `src/normalize/run_normalize.py` (start of `main`)
- `src/compute/run_compute.py` (start of `main`)

---

## 🔍 Code Review Checklist

Перед комітом перевірити:

### Compute Layer
- ✅ Немає обчислень у UI layer
- ✅ Метрики валідуються в `validations.py`
- ✅ Результати записуються в `data/compute/`

### UI Layer
- ✅ Тільки читання з `data/compute/`
- ✅ Немає записів у `data/`
- ✅ Session state правильно синхронізується
- ✅ Немає прихованих side-effects

### General
- ✅ Код читабельний без документації
- ✅ Немає магії (явні перетворення)
- ✅ Мінімальні зміни (patch-only)
- ✅ Smoke tests проходять

---

## 🚨 Common Pitfalls

### ❌ Pitfall 1: Розрахунки в UI

**Помилка:**
```python
# src/app/pages/overview_mvp.py
nc_net = row.get('nc_long', 0) - row.get('nc_short', 0)  # ❌
```

**Правильно:**
```python
df['nc_net'] = df['nc_long'] - df['nc_short']

# src/app/pages/overview_mvp.py (тільки читання)
nc_net = row.get('nc_net', 0)  # ✅
```

### ❌ Pitfall 2: Модифікація даних в UI

**Помилка:**
```python
# src/app/pages/overview_mvp.py
df.to_parquet('data/compute/metrics_weekly.parquet')  # ❌
```

**Правильно:**
```python
# UI тільки читає
df = pd.read_parquet('data/compute/metrics_weekly.parquet')  # ✅
```

### ❌ Pitfall 3: Прихована конвертація типів

**Помилка:**
```python
# week_idx може бути str або int
if current_week_idx < 0:  # ❌ TypeError якщо str!
```

**Правильно:**
```python
# Явна нормалізація
current_week_idx = int(st.session_state[week_idx_key])
if current_week_idx < 0:  # ✅
```

---

## 📚 References

- **README.md** — Quick start, project structure, commands
- **RESTORE.md** — Backup/restore procedures
- **src/app/pages/overview_mvp.py** — Приклад правильного UI (read-only)

---

**Last updated:** 2026-01-20 (v1.2.9)


## Compute QA (?????????)
**????????:** Flow-flags ???????? ? `changes_weekly.parquet`; smoke-????? ?? ?? ?????????.


**QA ????:** `data/compute/qa_report.txt`

**???????:**
- ERROR ??????? ?????? (SystemExit).
- WARN ?? ???????, ??? ???????? ? QA ????.

**???????? ????????? (ERROR):**
- ???????? ????'?????? ??????? ? canonical ??? metrics.
- ????????? ?????? (`market_key`, `report_date`).
- ???????? ????????? ????? ?????????? ?? `markets.yaml`.
- ????????? `pos_all/pos_5y`, OI???????, ??????? ??????.

**???????????? (WARN):**
- ???????? ?????? ? ????? (???? ???? ?????? > 8 ????).
- ?????????? `open_interest_all` (???? ??????????? ? canonical).

**Smoke tests (compute):**
- `pytest tests/test_compute_smoke.py -v`

## Golden Rules (Do Not Break)

- `main` is production only. Streamlit Cloud deploys from `main`.
- `dev` is for all development and experiments.
- Never work directly in `main`.
- Never deploy from `dev`.
- Production reads `data/` only. No demo/fallback paths.
- Entry point is `app.py` only (`streamlit run app.py`).
