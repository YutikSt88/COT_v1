# Dashboard Spec (П.4 Детальна Специфікація Екрана Dashboard)

## 1) Призначення екрана
- Дати трейдеру швидкий огляд поточного стану ринків.
- Виявити найсильніші сигнали (bullish/bearish/extreme) за мінімум кліків.
- Дозволити перейти з “скану” в `Market Detail`.

## 2) Цільовий сценарій
1. Користувач відкриває `Dashboard`.
2. Бачить агреговану картину (`signal summary`).
3. Фільтрує ринки (категорія/сигнал/діапазон).
4. Сортує таблицю за пріоритетом сигналу.
5. Відкриває конкретний ринок.

## 3) Структура Dashboard (зверху вниз)

### 3.1 `FiltersBar` (sticky)
Склад:
- `MarketSelector` (опційно: all + конкретний ринок)
- `Category filter` (FX, Metals, Indices, etc.)
- `Signal filter` (all, bullish, bearish, extreme)
- `DateRangePicker` (4W, 12W, YTD, 1Y, ALL)
- `Reset filters`

Правила:
- Стан фільтрів зберігається в URL.
- Sticky поведінка при скролі.

---

### 3.2 `Signal Summary Strip`
Метрики:
- `Bullish count`
- `Bearish count`
- `Extreme count`
- `Neutral count`
- `Last update time`

Правила:
- Кожна метрика = компактний `MetricCard`.
- Клік по метриці автоматично ставить `Signal filter`.

---

### 3.3 `Mini Charts Grid`
Призначення:
- Швидка візуальна перевірка 4-8 топових ринків за поточним фільтром.

Кожна картка:
- Назва ринку
- `SignalBadge`
- міні-графік (ціна + net positioning або z-score)
- коротка метрика (наприклад `z=1.8`)

Правила:
- Без зайвих підписів осей.
- Основний сенс: напрямок + екстремум.
- Клік відкриває `Market Detail` з цим ринком.

---

### 3.4 `Market Scan Table`
Основний блок екрана:
- Таблиця ринків (TanStack Table), compact-density.

Рекомендовані колонки MVP:
- `Market`
- `Category`
- `Signal`
- `Net Position`
- `Z-Score`
- `Delta 1W`
- `Extreme Flag`
- `Updated`

Поведіка:
- sorting (за замовчуванням: `signal_priority desc`, потім `|z-score| desc`)
- column visibility toggle (простий)
- row click -> `Market Detail`

## 4) Логіка пріоритету сигналів

## Signal Priority (для сортування)
1. `extreme`
2. `bullish` / `bearish` (сильні)
3. `neutral`

## Нормалізація індикаторів
- Використовувати єдине поле `signal_state` для badge/фільтра/сорту.
- `signal_strength` (numeric) для вторинного сорту.

## 5) URL State Contract (Dashboard)
- `?screen=dashboard`
- `?market=all|EUR`
- `?category=all|fx|metals|indices`
- `?signal=all|bullish|bearish|extreme|neutral`
- `?range=4W|12W|YTD|1Y|ALL`
- `?sort=signal_priority_desc`

## 6) Стани екрана

### `loading`
- skeleton для summary, mini-grid, таблиці.

### `empty`
- текст: “За поточними фільтрами даних немає”
- кнопка: “Скинути фільтри”

### `error`
- коротке повідомлення + retry.
- технічні деталі в collapsible block.

## 7) Правила щільності та читабельності
- Таблиця — головний блок, не менше 60% висоти контенту.
- Один акцентний колір на підблок.
- Відсутність декоративних іконок без смислу.
- Числа вирівняні праворуч, mono font.

## 8) KPI якості для Dashboard MVP
- Час “відкрив -> знайшов топ-сигнал” < 10 секунд.
- 1 клік з dashboard до деталі ринку.
- Нуль неоднозначних кольорів (семантика стабільна).
- Стійка робота при 30+ ринках у таблиці.

## 9) Definition of Done для П.4
- Dashboard має фіксовану структуру: filters -> summary -> mini charts -> table.
- Фільтри синхронізовані з URL.
- Рядок таблиці відкриває `Market Detail`.
- Сигнали мають єдину семантику кольорів/пріоритетів.

