# COT_v1 Compute Metrics Reference

Документ фіксує ключові артефакти compute-шару і мінімальні контракти для UI.

## 1. Input / Output

### Input

- `data/canonical/cot_weekly_canonical_full.parquet`

### Output (`data/compute`)

- `positions_weekly.parquet`
- `changes_weekly.parquet`
- `flows_weekly.parquet`
- `rolling_weekly.parquet`
- `extremes_weekly.parquet`
- `moves_weekly.parquet`
- `metrics_weekly.parquet`
- `market_radar_latest.parquet`
- `market_positioning_latest.parquet`
- `qa_report.txt`

## 2. Core keys

Базові ключі для join-логіки:

- `market_key`
- `report_date`

## 3. Semantic tables

### positions_weekly

Для груп `nc`, `comm`, `nr`:

- `{group}_long`
- `{group}_short`
- `{group}_total`
- `{group}_net`

### changes_weekly

Тижневі зміни для long/short/total/net:

- `{group}_*_chg_1w`

### flows_weekly

Потоки і ротація:

- `{group}_gross_chg_1w`
- `{group}_net_abs_chg_1w`
- `{group}_rotation_1w`
- `{group}_rotation_share_1w`
- `{group}_net_share_1w`

### rolling_weekly

13-тижневі середні:

- `{group}_long_ma_13w`
- `{group}_short_ma_13w`
- `{group}_total_ma_13w`
- `{group}_net_ma_13w`

### extremes_weekly

All-time і 5Y (260w) діапазони:

- `{group}_{metric}_min_all`
- `{group}_{metric}_max_all`
- `{group}_{metric}_pos_all`
- `{group}_{metric}_min_5y`
- `{group}_{metric}_max_5y`
- `{group}_{metric}_pos_5y`

### moves_weekly

- `{group}_{metric}_move_pct_all`
- `{group}_{metric}_move_pct_5y`

## 4. Wide table: metrics_weekly

`metrics_weekly.parquet` — головне джерело для детальних сторінок UI.

Важливі блоки колонок:

- позиції/зміни (`nc_*`, `comm_*`, `nr_*`)
- OI (`open_interest*`)
- z-score (`net_z_52w_funds`, `net_z_52w_commercials`)
- traffic/consensus (`cot_traffic_signal`, `conflict_level`)
- OI regime (`oi_regime`, `oi_risk_level`, `oi_z_52w`)

## 5. Radar/Positioning datasets

### market_radar_latest

Побудовано з `metrics_weekly` (останній `report_date` на market).

Використовується сторінками:

- Dashboard
- Signals

### market_positioning_latest

Також latest-зріз із `metrics_weekly`.

Використовується для table-style позиціонування.

## 6. Оновлення compute

```powershell
python .\scripts\run_pipeline.py --root . --log-level INFO --yes
```

## 7. Важливе правило

Якщо додаєш нову метрику в compute:

1. додаєш у `src/compute`
2. додаєш/оновлюєш валідацію
3. оновлюєш цей документ
4. лише потім використовуєш в UI

