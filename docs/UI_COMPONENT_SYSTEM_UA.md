# UI Component System (П.3 Дизайн-Система Компонентів)

## 1) Принципи
- Кожен компонент має одну чітку відповідальність.
- Fetch-логіка не змішується з presentation (виняток: page-level containers).
- Компоненти мають стабільні стани: `loading`, `empty`, `error`, `ready`.
- Колір завжди семантичний, не декоративний.

## 2) Базові токени (MVP)

### Простір
- `space-1 = 4px`
- `space-2 = 8px`
- `space-3 = 12px`
- `space-4 = 16px`
- `space-6 = 24px`

### Радіуси / бордери
- Панелі: 6px (стримано, без “карткової іграшковості”)
- Бордер: 1px low-contrast

### Типографіка
- Заголовки: Inter 600
- Текст: Inter 400/500
- Числа: Roboto Mono 500

## 3) Компоненти MVP

### 3.1 `ChartContainer`
Призначення:
- Контейнер для будь-якого графіка (ECharts), title + toolbar + стан.

Props (мінімум):
- `title: string`
- `subtitle?: string`
- `height?: number`
- `loading?: boolean`
- `error?: string | null`
- `isEmpty?: boolean`
- `toolbarSlot?: ReactNode`
- `children: ReactNode`

Правила:
- Без власного fetch.
- Всі графіки мають однаковий header-стиль.
- `error` показує коротке технічне повідомлення + retry action (через callback slot).

---

### 3.2 `MarketSelector`
Призначення:
- Вибір активного ринку (пошук + список).

Props:
- `value: string`
- `options: { value: string; label: string; category?: string }[]`
- `onChange: (market: string) => void`
- `disabled?: boolean`

Правила:
- Підтримка keyboard navigation.
- Пошук чутливий до символу/alias.
- Зміна значення синхронізується з URL.

---

### 3.3 `SignalBadge`
Призначення:
- Компактний індикатор стану сигналу.

Props:
- `state: "bullish" | "bearish" | "neutral" | "warning" | "extreme"`
- `label?: string`
- `size?: "sm" | "md"`

Правила:
- `bullish -> green`, `bearish -> red`, `warning/extreme -> yellow/orange`, `neutral -> blue/gray`.
- Контраст WCAG читабельний на темному фоні.

---

### 3.4 `MetricCard`
Призначення:
- Показ ключової метрики (значення + delta + semantic status).

Props:
- `label: string`
- `value: string`
- `delta?: string`
- `trend?: "up" | "down" | "flat"`
- `tone?: "neutral" | "positive" | "negative" | "warning"`
- `loading?: boolean`

Правила:
- Мінімальний дизайн, без зайвих іконок.
- Значення монопросторовим шрифтом.
- Delta кольориться лише семантично.

---

### 3.5 `DataTable`
Призначення:
- Аналітична таблиця на TanStack Table.

Props:
- `columns: ColumnDef<T>[]`
- `data: T[]`
- `loading?: boolean`
- `error?: string | null`
- `emptyText?: string`
- `onRowClick?: (row: T) => void`

Правила:
- Sticky header.
- Числа праворуч, mono font.
- Сортування/фільтрація без втрати продуктивності.
- Мінімум візуального шуму: compact rows 32-36px.

---

### 3.6 `DateRangePicker`
Призначення:
- Перемикання вікна аналізу.

Props:
- `value: "4W" | "12W" | "YTD" | "1Y" | "ALL" | CustomRange`
- `onChange: (...) => void`
- `allowCustom?: boolean`

Правила:
- Швидкі пресети first-class.
- Значення в URL.
- Custom range без модальних вікон на MVP (простий popover).

## 4) Станові патерни

### `loading`
- Skeleton, без “стрибаючого” layout.
- Для таблиць: 6-10 рядків skeleton.

### `empty`
- Коротке пояснення + дія (наприклад “скинути фільтри”).

### `error`
- Одне речення + технічний код/текст у collapsible details.
- Retry control у межах того ж блоку.

## 5) Page Containers (композиція)

### `DashboardContainer`
- Завантажує summary + market list.
- Рендерить `MetricCard`, `ChartContainer`, `DataTable`.

### `MarketDetailContainer`
- Завантажує таймсерії конкретного ринку.
- Рендерить 2 графіки + таблицю історії.

### `SignalsContainer`
- Завантажує активні сигнали + фільтри.
- Рендерить таблицю і статуси.

## 6) URL State Contract (MVP)
- `?market=EUR`
- `?range=12W`
- `?signal=bullish|bearish|extreme|all`
- `?page=1&sort=signalStrength_desc`

Правила:
- URL є джерелом істини для фільтрів.
- При refresh стан зберігається.

## 7) Критерії якості компонентів
- Компонент рендериться ізольовано (Story/preview або test harness).
- Не має прихованих сайд-ефектів.
- Має однакову поведінку на всіх 3 MVP-екранах.

## 8) Definition of Done для П.3
- Визначені API для всіх MVP-компонентів.
- Задокументовані стани `loading/empty/error`.
- Єдині semantic color rules зафіксовані.
- Готово до п.4 (екран `Dashboard` детально по секціях).

