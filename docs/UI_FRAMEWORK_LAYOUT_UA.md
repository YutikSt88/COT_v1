# UI Framework Layout (П.2 Каркас Інтерфейсу)

## 1) Глобальний Shell

### Структура
- `TopBar` (фіксована верхня панель)
- `SideNav` (ліва вузька навігація, collapsible)
- `MainWorkspace` (основний контент)

### Розкладка
- Desktop:
  - `TopBar`: висота 56px
  - `SideNav`: 220px (expanded) / 72px (collapsed)
  - `MainWorkspace`: займає решту
- Мінімальна ширина контенту: 1280px (для аналітичних таблиць/графіків)

## 2) TopBar (мінімум, без шуму)

### Ліва частина
- `App title` (коротка назва, без брендингових декоративних блоків)
- `Global market search`

### Права частина
- `MarketSelector` (поточний ринок)
- `DateRangePicker` (4W / 12W / YTD / 1Y / ALL)
- `Status` (останнє оновлення даних)
- `User menu`

## 3) SideNav

### Пункти
- `Dashboard`
- `Market Detail`
- `Signals`

### Правила
- Іконка + текст (коли expanded)
- Тільки іконка (коли collapsed)
- Активний пункт має чіткий індикатор (border-left + приглушений фон)

## 4) MainWorkspace по екранах

### Dashboard
- Ряд 1: `Signal summary strip` (кількість bullish/bearish/extreme)
- Ряд 2: `Mini charts grid` (4-8 ринків)
- Ряд 3: `DataTable` (швидкий скан ринків)

### Market Detail
- Верх: `ChartContainer` (Price + COT net positioning)
- Середина: `ChartContainer` (Z-score / extremes)
- Низ: `DataTable` (тижневі значення + ключові зміни)

### Signals
- Верх: `FiltersBar` (signal state, category, market, date range)
- Низ: `Active signals table` (sortable, density: compact)

## 5) Layout & Spacing Rules
- Базова сітка: 8px.
- Відступи сторінки: 16px (min), 24px (standard).
- Висота панелей графіків:
  - великий графік: 360-420px
  - другорядний: 240-300px
- Таблиці: compact row height (32-36px).

## 6) Типографіка
- Заголовки: Inter 600
- Основний текст: Inter 400/500
- Числа/метрики: Roboto Mono 500
- Вирівнювання чисел у таблицях: праворуч

## 7) Колірна дисципліна
- Фон: near-black
- Панелі: темно-сірі
- Межі: low-contrast
- Сигнали:
  - green: bullish/net long
  - red: bearish/net short
  - yellow/orange: warning/extreme
  - blue/cyan: reference

## 8) Адаптивність (MVP)
- Ціль MVP: desktop-first.
- На width < 1100:
  - `SideNav` auto-collapse
  - частина метрик ховається в dropdown/tooltip
  - таблиці переходять у горизонтальний scroll

## 9) Компонентні контракти (мінімальні)
- `ChartContainer`: тільки рендер графіка + title + toolbar slot.
- `DataTable`: тільки таблиця (sorting/filtering/pagination), без fetch.
- `MetricCard`: лише 1 метрика + delta + семантичний колір.
- `SignalBadge`: текст сигналу + severity.

## 10) Definition of Done для П.2
- Є узгоджений shell (TopBar + SideNav + Workspace).
- Є layout-шаблони для 3 екранів.
- Є єдині правила відступів, кольорів, типографіки.
- Можна починати реалізацію компонентів без додаткових уточнень.

