# Market Detail Spec (П.5 Детальна Специфікація Екрана Market Detail)

## 1) Призначення екрана
- Дати глибоку аналітику по одному ринку.
- Підтвердити/спростувати сигнал із Dashboard.
- Показати контекст: поточний стан, динаміка, екстремуми, історія.

## 2) Цільовий сценарій
1. Користувач приходить з `Dashboard` по конкретному ринку.
2. Бачить ключовий сигнал і стан позиціонування.
3. Перевіряє графіки (ціна + net, z-score/extremes).
4. Дивиться тижневі зміни в таблиці.
5. Формує торгове рішення або повертається до скану.

## 3) Структура Market Detail (зверху вниз)

### 3.1 `Context Header`
Склад:
- Назва ринку + категорія
- Поточний `SignalBadge`
- Останнє оновлення
- Кнопка повернення до `Dashboard`

Правила:
- Header компактний, без великих декоративних блоків.
- Найважливіше: ринок + сигнал + час оновлення.

---

### 3.2 `Key Metrics Row`
Рекомендовані метрики:
- `Net Position`
- `Z-Score`
- `Delta 1W`
- `Extreme Distance` (позиція відносно max/min діапазону)
- `Signal Strength`

Правила:
- Всі значення у `MetricCard`.
- Числа моноширинні, праве вирівнювання.
- Delta кольором тільки за семантикою.

---

### 3.3 `Primary Chart` (головний)
Склад:
- Price series
- COT net positioning (на другій осі або синхронізованим нижнім шаром)
- Маркери зміни signal_state

Інтеракції:
- hover crosshair
- zoom/pan
- toggle series

Правила:
- Графік читабельний при 1Y/ALL.
- Reference lines стримані (low contrast).
- Не перевантажувати підписами.

---

### 3.4 `Secondary Chart` (контекстний)
Склад:
- Z-score або percentile-position
- Extreme bands (warning zone / extreme zone)

Правила:
- Чітко видимі пороги (наприклад `|z| >= 1.5`, `|z| >= 2.0`).
- Yellow/orange тільки для warning/extreme.

---

### 3.5 `Market Data Table`
Колонки MVP:
- `Date`
- `Price`
- `Net Position`
- `Z-Score`
- `Delta 1W`
- `Signal`
- `Extreme Flag`

Поведіка:
- sorting by `Date desc` за замовчуванням
- швидкий filter по даті
- export CSV (v1, не в MVP обов'язково)

## 4) Toolbar і режими перегляду

### Режими графіків
- `Absolute`
- `Normalized`
- `Percentile` (для порівняння в історичному діапазоні)

### Time range
- `4W`, `12W`, `YTD`, `1Y`, `ALL`

### URL State Contract
- `?screen=market`
- `?market=EUR`
- `?range=1Y`
- `?mode=absolute|normalized|percentile`

## 5) Семантика сигналів (єдина для всіх блоків)
- `bullish` -> green
- `bearish` -> red
- `neutral` -> blue/gray
- `warning/extreme` -> yellow/orange

Правила:
- Однакові кольори в badge, chart markers і table cells.
- Без додаткових “красивих” кольорів.

## 6) Стани екрана

### loading
- skeleton для header/metrics/charts/table.

### empty
- “Немає даних для вибраного ринку/періоду”
- кнопка скидання range.

### error
- коротка причина + retry.
- деталі помилки у collapsible.

## 7) Аналітичні підказки (MVP)
- Tooltip на порогах z-score:
  - що означає warning/extreme
- Tooltip на метриці `Signal Strength`:
  - як пораховано (коротко)

Без довгих текстових пояснень на екрані.

## 8) KPI якості для Market Detail
- Час “відкрив -> зрозумів контекст сигналу” < 15 секунд.
- Всі ключові метрики в першому екрані без скролу (desktop).
- Графіки лишаються читабельними на `ALL` діапазоні.

## 9) Definition of Done для П.5
- Є header + metrics + 2 графіки + таблиця.
- Працюють range/mode перемикачі.
- URL відтворює стан екрану.
- Семантика кольорів консистентна з Dashboard.

