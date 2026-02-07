# COT_v1 Developer Handoff

Це практична інструкція для нового розробника, який має підтримувати проект без довгого входження в контекст.

## 1. Що важливо знати одразу

- Основний production UI: **Streamlit**
- Root entrypoint: `app.py`
- Дані для UI: тільки `data/compute/*`
- Оновлення даних робиться pipeline-командою (див. нижче)

## 2. Мінімальний старт за 5 хвилин

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\dev-up.ps1 -Mode streamlit
```

Після цього UI доступний на `http://localhost:8501`.

## 3. Оновлення коду з main

```powershell
.\scripts\sync-main.ps1
```

Скрипт:

- переходить на `main`
- робить `fetch`
- робить fast-forward pull (або hard-reset у force-режимі)

## 4. Оновлення даних (адмін-операція)

```powershell
python .\scripts\run_pipeline.py --root . --log-level INFO --yes
```

Це генерує актуальні parquet-файли в `data/compute`.

## 5. Де шукати основний код

- App routing/auth shell: `src/app/app.py`
- Auth + RBAC: `src/app/auth.py`
- Dashboard page: `src/app/pages/market.py`
- Market Detail page: `src/app/pages/overview_mvp.py`
- Signals page: `src/app/pages/signals.py`
- Shared UI helpers: `src/app/pages/_terminal_ui.py`
- Pipeline runner: `scripts/run_pipeline.py`

## 6. Правила змін

- Не переносити compute-логіку в UI
- Не змінювати data contracts без оновлення docs
- Перед commit перевіряти, що випадково не потрапили локальні артефакти (`auth.db`, `node_modules`, тимчасові lock-файли)

## 7. Часті проблеми

### `market_radar_latest.parquet not found`

Причина: не запускали compute pipeline.

Рішення:

```powershell
python .\scripts\run_pipeline.py --root . --log-level INFO --yes
```

### `npm ENOENT package.json`

Причина: команда запущена не в `client`.

Рішення:

```powershell
cd .\client
npm install
npm run dev
```

### `uvicorn ... Address already in use`

Причина: порт 8000 вже зайнятий іншим процесом.

Рішення: зупинити попередній процес або використати інший порт.

## 8. Деплой

Streamlit Cloud:

- Branch: `main`
- Main file: `app.py`
- Після `git push origin main` виконай `Reboot app` (за потреби `Clear cache + Reboot`).

