# Handoff для наступного розробника (UA)

Дата: 2026-02-07  
Актуальний коміт `main`: `ee16ac2`

## 1) Що вже зроблено

- Streamlit UI переведено на єдиний terminal-style:
  - `src/app/pages/market.py` -> Dashboard
  - `src/app/pages/overview_mvp.py` -> Market Detail
  - `src/app/pages/signals.py` -> Signals
  - `src/app/pages/_terminal_ui.py` -> спільна тема/лоадери/nav
- Виправлено data-path bug і додано fallback:
  - якщо немає `market_radar_latest.parquet`, UI бере дані з `metrics_weekly.parquet`.
- Оновлено документацію:
  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEV_HANDOFF.md`
  - `docs/COMPUTE_METRICS.md`
- Додано стабільні скрипти:
  - `scripts/dev-up.ps1` (запуск)
  - `scripts/sync-main.ps1` (синхронізація з main)

## 2) Як запускати локально

Відкрити PowerShell у корені репозиторію:

```powershell
.\scripts\sync-main.ps1
.\scripts\dev-up.ps1 -Mode streamlit
```

Оновлення даних:

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\run_pipeline.py --root . --log-level INFO --yes
```

## 3) Як деплоїти (Streamlit Cloud)

- Branch: `main`
- Main file path: `app.py`
- Після `git push origin main` -> `Manage app` -> `Reboot app`  
  (за потреби `Clear cache + Reboot`)

## 4) Відомі нюанси

- Після редизайну тимчасово відсутня кнопка “Update data” в адмінці.
  - Дані оновлюються через `scripts/run_pipeline.py`.
- Якщо в середовищі немає compute-файлів:
  - спочатку запустити pipeline.
- Не комітити локальні артефакти:
  - `data/app/auth.db`
  - `client/node_modules`
  - випадкові `package-lock.json` у корені

## 5) Що робити далі (пріоритет)

1. Повернути admin-кнопку оновлення даних у Streamlit UI (з permission check `run_pipeline`).
2. Доробити Streamlit-візуал до production-level (типографіка, щільність, таблиці, контраст).
3. Додати smoke-перевірку на наявність ключових compute-файлів при старті.
4. Підготувати production deployment runbook для окремого сервера (Hetzner).
