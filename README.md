# COT_v1

COT-аналітична платформа на базі CFTC Legacy COT даних.

Поточний продакшн-інтерфейс: **Streamlit** (єдиний основний UI).

## Швидкий старт (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Запуск UI (одна команда)

```powershell
.\scripts\dev-up.ps1 -Mode streamlit
```

### Синхронізація з main (одна команда)

```powershell
.\scripts\sync-main.ps1
```

## Оновлення даних

Оновлення виконується пайплайном `ingest -> normalize -> compute`:

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\run_pipeline.py --root . --log-level INFO --yes
```

Після завершення пайплайна перезапусти або rerun Streamlit.

## Архітектура

Пайплайн:

1. `src/ingest` -> `data/raw`
2. `src/normalize` -> `data/canonical`
3. `src/compute` -> `data/compute`
4. `src/app` (Streamlit UI) читає лише `data/compute`

Ключові артефакти `data/compute`:

- `metrics_weekly.parquet`
- `market_radar_latest.parquet`
- `market_positioning_latest.parquet`

## Запуск компонентів вручну

### Streamlit

```powershell
streamlit run app.py
```

### API (для React/dev режиму)

```powershell
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### React (додатково, не основний продакшн UI)

```powershell
cd .\client
npm install
npm run dev
```

## Деплой Streamlit Community Cloud

- Repository: `main`
- Main file path: `app.py`
- Python dependencies: `requirements.txt`

Після `git push origin main` Streamlit Cloud перезбирає додаток.

## Рекомендований щоденний flow

1. `.\scripts\sync-main.ps1`
2. `.\scripts\dev-up.ps1 -Mode streamlit`
3. (за потреби оновлення даних) `python .\scripts\run_pipeline.py --root . --log-level INFO --yes`

## Основні документи

- `docs/ARCHITECTURE.md` — технічна архітектура
- `docs/DEV_HANDOFF.md` — інструкція для наступників
- `docs/COMPUTE_METRICS.md` — метрики та compute-контракти

## Примітка

Якщо бачиш `market_radar_latest.parquet not found`, спочатку запусти pipeline командою вище.



