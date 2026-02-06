# COT_v1: Compute Metrics Reference (актуально)

Цей документ — джерело правди для колонок та формул Compute шару.

## Загальні правила Compute
- Вхід: `data/canonical/cot_weekly_canonical_full.parquet`
- Фільтрація тільки за `configs/markets.yaml` (market_key + contract_code)
- Пропуски числових значень в positions → 0
- 5Y = 260 тижнів (min_periods=52)
- Якщо min == max → pos = 0.5 (якщо current не NaN)

## 1) positions_weekly.parquet
**Файл:** `data/compute/positions_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

Колонки (для P ∈ {nc, comm, nr}):
- `{P}_long`
- `{P}_short`
- `{P}_total = {P}_long + {P}_short`
- `{P}_net = {P}_long - {P}_short`

## 2) changes_weekly.parquet
**Файл:** `data/compute/changes_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

Колонки:
- `{P}_long_chg_1w`
- `{P}_short_chg_1w`
- `{P}_total_chg_1w`
- `{P}_net_chg_1w`

Формула: `current - previous` в межах `market_key`.

## 3) flows_weekly.parquet
**Файл:** `data/compute/flows_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

Колонки (для P ∈ {nc, comm, nr}):
- `{P}_gross_chg_1w = |ΔLong| + |ΔShort|`
- `{P}_net_abs_chg_1w = |ΔNet|`
- `{P}_rotation_1w = max(gross - net_abs, 0)`
- `{P}_rotation_share_1w = rotation / gross (gross > 0)`
- `{P}_net_share_1w = net_abs / gross (gross > 0)`
- `{P}_total_chg_1w_calc` (QA)
- `{P}_net_chg_1w_calc` (QA)

## 4) rolling_weekly.parquet
**Файл:** `data/compute/rolling_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

Колонки (для P ∈ {nc, comm, nr}):
- `{P}_long_ma_13w`
- `{P}_short_ma_13w`
- `{P}_total_ma_13w`
- `{P}_net_ma_13w`

## 5) extremes_weekly.parquet
**Файл:** `data/compute/extremes_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

All-time:
- `{P}_{metric}_min_all`, `{P}_{metric}_max_all`, `{P}_{metric}_pos_all`

5Y (260w, min_periods=52):
- `{P}_{metric}_min_5y`, `{P}_{metric}_max_5y`, `{P}_{metric}_pos_5y`

## 6) moves_weekly.parquet
**Файл:** `data/compute/moves_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

Колонки:
- `{P}_{metric}_move_pct_all`
- `{P}_{metric}_move_pct_5y`

## 7) metrics_weekly.parquet (Wide)
**Файл:** `data/compute/metrics_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Джерело:** left join `positions + changes + flows + rolling + extremes + moves`.

Додаткові колонки:
- `category`, `contract_code`
- `open_interest` (з canonical)
- `open_interest_chg_1w`, `open_interest_chg_1w_pct`
- `open_interest_pos_all`, `open_interest_pos_5y`
- `open_interest_pct_all`, `open_interest_pct_5y`
- `open_interest_chg_pct_rank_all`, `open_interest_chg_pct_rank_5y`
- `open_interest_chg_z_52w`, `open_interest_chg_z_260w`
- `open_interest_regime_all`, `open_interest_regime_5y`
- `open_interest_regime_strength_all`, `open_interest_regime_strength_5y`
- `spec_vs_hedge_net`, `spec_vs_hedge_net_chg_1w`

OI-regime (advanced):
- `oi_z_52w`, `oi_z_260w`
- `oi_delta_4w`, `oi_acceleration`
- `oi_regime`, `oi_driver`, `oi_risk_level`

OI-% метрики:
- `nc_net_pct_oi`, `comm_net_pct_oi`, `nr_net_pct_oi`
- `nc_flow_pct_oi_1w`
Примітка: **comm_flow_pct_oi_1w / nr_flow_pct_oi_1w наразі не обчислюються в compute**.

Traffic/Consensus:
- `net_z_52w_funds`, `net_z_52w_commercials`
- `activity_funds`, `activity_commercials`
- `flow_funds`, `flow_commercials`
- `positioning_funds`, `positioning_commercials`
- `conflict_level`, `cot_traffic_signal`
- `nc_tl_*`, `comm_tl_*`, `tl_consensus_*`

## Dataset: market_radar_latest.parquet
**Файл:** `data/compute/market_radar_latest.parquet`  
**Source:** `metrics_weekly.parquet` (latest report_date per market_key)

Використовується в UI Market Radar.

## Dataset: market_positioning_latest.parquet
**Файл:** `data/compute/market_positioning_latest.parquet`  
**Source:** `metrics_weekly.parquet` (latest report_date per market_key)

Використовується в UI Table view на Market page.

---

**Last updated:** 2026-01-20 (v1.2.9)
