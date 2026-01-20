# COT_v1: Compute Metrics Reference (актуально)

Цей документ — єдине джерело правди для колонок і формул шару Compute.

## Загальні правила Compute
- Вхід: `data/canonical/cot_weekly_canonical_full.parquet`
- Фільтрація тільки за `configs/markets.yaml` (`market_key` + `contract_code`)
- Пропуски числових значень в positions приводяться до 0
- 5Y = 260 тижнів (min_periods=52)
- Якщо min == max, тоді pos = 0.5 (за умови, що поточне значення не NaN)

---

## ???????? ??? ??????? (??????????)
- Flow-flags ???????? ? `changes_weekly.parquet` ? ?? ??????????? ? `metrics_weekly.parquet`.
- 5Y = 260 ?????? ??????????? ??? extremes ?? ???? OI-???????/??????????? ? wide view.
- pos = 0.5 ??? min==max ?????????????? ??? all-time ? 5Y (extremes + OI ???????).
- `open_interest_all` ????'???????: ???? ??????? ????? ? Compute ??????????? (????????? ? `run_compute.py`).
- `% OI` ? wide view: `chg_1w / prev` ??? ??????; ???? prev==0 ??? NaN ? ????????? NaN.
- QA ???? Compute: `data/compute/qa_report.txt`.



## 1) positions_weekly.parquet
**Файл:** `data/compute/positions_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Колонки (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_long`
- `{P}_short`
- `{P}_total = {P}_long + {P}_short`
- `{P}_net = {P}_long - {P}_short`

---

## 2) changes_weekly.parquet
**Файл:** `data/compute/changes_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Колонки (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_long_chg_1w`
- `{P}_short_chg_1w`
- `{P}_total_chg_1w`
- `{P}_net_chg_1w`

**Формула:** зміна = `current - previous` в межах `market_key`.

---

## 3) flows_weekly.parquet
**Файл:** `data/compute/flows_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Колонки (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_gross_chg_1w = |ΔLong| + |ΔShort|`
- `{P}_net_abs_chg_1w = |ΔNet|`
- `{P}_rotation_1w = max(gross - net_abs, 0)`
- `{P}_rotation_share_1w = rotation / gross (якщо gross > 0, інакше 0)`
- `{P}_net_share_1w = net_abs / gross (якщо gross > 0, інакше 0)`

**QA-колонки (для перевірки):**
- `{P}_total_chg_1w_calc = ΔLong + ΔShort`
- `{P}_net_chg_1w_calc = ΔLong - ΔShort`

---

## 4) rolling_weekly.parquet
**Файл:** `data/compute/rolling_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Колонки (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_long_ma_13w`
- `{P}_short_ma_13w`
- `{P}_total_ma_13w`
- `{P}_net_ma_13w`

**Формула:** 13-тижневе ковзне середнє (`rolling(window=13, min_periods=1)`).

---

## 5) extremes_weekly.parquet
**Файл:** `data/compute/extremes_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**All-time (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_long_min_all`, `{P}_long_max_all`, `{P}_long_pos_all`
- `{P}_short_min_all`, `{P}_short_max_all`, `{P}_short_pos_all`
- `{P}_total_min_all`, `{P}_total_max_all`, `{P}_total_pos_all`
- `{P}_net_min_all`, `{P}_net_max_all`, `{P}_net_pos_all`

**5Y (260 тижнів, min_periods=52):**
- `{P}_long_min_5y`, `{P}_long_max_5y`, `{P}_long_pos_5y`
- `{P}_short_min_5y`, `{P}_short_max_5y`, `{P}_short_pos_5y`
- `{P}_total_min_5y`, `{P}_total_max_5y`, `{P}_total_pos_5y`
- `{P}_net_min_5y`, `{P}_net_max_5y`, `{P}_net_pos_5y`

**Position formula:**  
`pos = (current - min) / (max - min)`  
Якщо `max == min` і current не NaN → `pos = 0.5`.

---

## 6) moves_weekly.parquet
**Файл:** `data/compute/moves_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Колонки (для кожної групи P ∈ {nc, comm, nr}):**
- `{P}_long_move_pct_all`
- `{P}_short_move_pct_all`
- `{P}_total_move_pct_all`
- `{P}_net_move_pct_all`

**Формула:** перцентиль `abs(chg_1w)` в межах історії `market_key`.

---

## 7) metrics_weekly.parquet (Wide)
**Файл:** `data/compute/metrics_weekly.parquet`  
**Ключі:** `market_key`, `report_date`

**Джерело:** left join: positions + changes + flows + rolling + extremes + moves

**Додаткові колонки:**
- `category` (з `markets.yaml`)
- `contract_code` (з `markets.yaml`)
- `open_interest` (from canonical `open_interest_all`)
- `open_interest_chg_1w`
- `open_interest_chg_1w_pct = open_interest_chg_1w / previous_open_interest`
- `open_interest_pct_all`, `open_interest_pct_5y` (percentile rank of open_interest)
- `open_interest_chg_pct_rank_all`, `open_interest_chg_pct_rank_5y` (percentile rank of abs(open_interest_chg_1w_pct))
- `open_interest_chg_z_52w`, `open_interest_chg_z_260w` (z-score of open_interest_chg_1w_pct)
- `open_interest_regime_all`, `open_interest_regime_5y` (Expansion/Contraction/Flat)
- `open_interest_regime_strength_all`, `open_interest_regime_strength_5y` (Weak/Moderate/Strong)
- `open_interest_pos_all`, `open_interest_pos_5y` (deprecated)

## Net z-score + Activity/Flow/Positioning + Consensus

**Z-score (52w, min_periods=26, ddof=0):**
- `net_z_52w_funds` = z-score of `nc_net`
- `net_z_52w_commercials` = z-score of `comm_net`

**Activity (rolling 52w p75 of abs(net_delta_1w), min_periods=26):**
- `activity_funds`: Aggressive if `abs(nc_net_chg_1w) >= p75_52w`, else Normal; if not enough history -> N/A
- `activity_commercials`: Aggressive if `abs(comm_net_chg_1w) >= p75_52w`, else Normal; if not enough history -> N/A

**Flow (Directional/Rotational):**
- Directional if `sign(long_delta_1w) == -sign(short_delta_1w)` AND `abs(net_delta_1w) > 0.5 * max(abs(long_delta_1w), abs(short_delta_1w))`
- If max(abs(long),abs(short)) == 0 -> N/A
- If one of long/short delta == 0 (other != 0) -> Rotational
- If net_delta == 0 -> Rotational

Columns:
- `flow_funds`, `flow_commercials`

**Positioning (Funds):** from `net_z_52w_funds`
- >= +1.5: Crowded Long
- +1.0..+1.5: Extended Long
- -1.0..+1.0: Balanced
- -1.5..-1.0: Extended Short
- <= -1.5: Crowded Short

Column: `positioning_funds`

**Positioning (Commercials):** Unwound override + z-score base
- Unwound if:
  - `activity_commercials == "Aggressive"`
  - `flow_commercials == "Directional"`
  - sign(net_delta_1w_commercials) == -sign(prev_net_commercials) (ignore if any sign == 0)
  - `abs(prev_net_z_52w_commercials) >= 1.0`
- Else:
  - abs(z) < 1.0 -> Balanced
  - z >= +1.5 -> Crowded Long
  - z <= -1.5 -> Crowded Short
  - 1.0..1.5 -> Balanced

Column: `positioning_commercials`

**Market Consensus + Signal:**
- `conflict_level`:
  - High: funds_aggressive AND commercials_aggressive AND flows_opposite
  - Medium: (funds_aggressive OR commercials_aggressive) AND flows_opposite
  - Low: else
  - funds_aggressive = activity_funds == Aggressive AND flow_funds == Directional
  - commercials_aggressive = activity_commercials == Aggressive AND flow_commercials == Directional
  - flows_opposite = sign(nc_net_chg_1w) == -sign(comm_net_chg_1w), ignore if any sign == 0
- `cot_traffic_signal` (-2..+2):
  - flow_score = +1 if comm_net_chg_1w > 0; -1 if nc_net_chg_1w < 0
  - pos_score = -1 if net_z_52w_funds >= 1.5; +1 if net_z_52w_funds <= -1.5
  - conflict_penalty = -1 if conflict_level == High else 0
  - `cot_traffic_signal = clamp(flow_score + pos_score + conflict_penalty, -2, +2)`

## Open Interest Regime (Advanced)

**Columns:**
- `oi_z_52w`, `oi_z_260w` (optional)
- `oi_delta_4w`
- `oi_acceleration`
- `oi_regime`
- `oi_driver`
- `oi_risk_level`

**Formulas:**
- `oi_z_52w = (oi - mean_52w) / std_52w`, min_periods=26, std==0 -> NaN
- `oi_z_260w = (oi - mean_260w) / std_260w`, min_periods=52, std==0 -> NaN
- `oi_delta_4w = oi - oi_4w_ago`
- `oi_acceleration = oi_delta_1w - (oi_delta_4w / 4.0)`
- `small_threshold = 0.05 * median(|oi_delta_1w| over 52w)`

**Regime:**
- `Expansion_Early`: `oi_delta_1w > 0` AND `oi_acceleration > 0` AND `oi_z_52w < 1.5`
- `Expansion_Late`: `oi_delta_1w > 0` AND `oi_acceleration >= 0` AND `oi_z_52w >= 1.5`
- `Distribution`: `oi_delta_1w < 0` AND `oi_z_52w >= 1.5`
- `Neutral`: `abs(oi_delta_1w) <= small_threshold` AND `abs(oi_z_52w) < 1.0`
- `Rebuild`: `oi_delta_1w > 0` AND `oi_z_52w <= -1.0`
- else `Mixed`
- If any required inputs are NaN -> `oi_regime = "N/A"`

**OI Driver:**
- `abs_funds = abs(nc_net_chg_1w)`, `abs_comm = abs(comm_net_chg_1w)`, `total_abs = abs_funds + abs_comm`
- If `total_abs == 0` -> `N/A`
- If `share_funds >= 0.6` -> `Funds`
- If `share_comm >= 0.6` -> `Commercials`
- else `Mixed`
- If inputs are NaN -> `oi_driver = "N/A"`

**OI Risk Level (risk_score):**
- +1 if `oi_z_52w >= 1.5`
- +1 if `oi_z_52w >= 2.0`
- +1 if `positioning_funds` starts with "Crowded" (if present)
- +1 if `conflict_level == "High"` (if present)
- score 0–1 -> `Low`, 2 -> `Elevated`, >=3 -> `High`
- If required inputs are NaN -> `oi_risk_level = "N/A"`

## Dataset: market_positioning_latest.parquet

**Source:** `metrics_weekly.parquet` (latest report_date per market_key)  
**Output:** `data/compute/market_positioning_latest.parquet`  
**Keys:** `market_id`, `report_date`

**Columns:**
- Market: `market_id`, `market_name`, `category`, `report_date`
- Signals: `cot_traffic_signal`, `conflict_level`, `oi_regime`, `oi_risk_level`
- OI: `open_interest`, `open_interest_chg_1w`, `open_interest_chg_1w_pct`
- Funds: `funds_net`, `funds_net_chg_1w`, `funds_pct_oi_chg_1w`, `funds_z_52w`
- Commercials: `comm_net`, `comm_net_chg_1w`, `comm_pct_oi_chg_1w`, `comm_z_52w`
- Small: `small_net`, `small_net_chg_1w`, `small_pct_oi_chg_1w`
- Optional: `why_tags` (CSV, max 3, same priority as Market Radar)

**Formulas:**
- `open_interest_prev = open_interest - open_interest_chg_1w`
- `*_pct_oi_chg_1w = *_net_chg_1w / open_interest_prev` (NaN if prev is 0 or NaN)
**OI formulas:**
- `open_interest_pct_all` = rank(open_interest) / count per market_key (all-time)
- `open_interest_pct_5y` = rolling percentile of open_interest (260w, min_periods=52)
- `open_interest_chg_pct_rank_all` = rank(abs(open_interest_chg_1w_pct)) / count (all-time)
- `open_interest_chg_pct_rank_5y` = rolling percentile of abs(open_interest_chg_1w_pct) (260w, min_periods=52)
- `open_interest_chg_z_52w` = (chg_pct - mean_52w) / std_52w (window=52, min_periods=26, ddof=0)
- `open_interest_chg_z_260w` = (chg_pct - mean_260w) / std_260w (window=260, min_periods=52, ddof=0)
- `open_interest_regime_*`: Expansion if chg_pct > 0, Contraction if chg_pct < 0, Flat if chg_pct == 0
- `open_interest_regime_strength_*`: Weak < 0.33, Moderate 0.33-0.67, Strong > 0.67 (from change percentile)
- `spec_vs_hedge_net = nc_net - comm_net`
- `spec_vs_hedge_net_chg_1w`

**OI-% метрики:**
- `nc_net_pct_oi = nc_net / open_interest`
- `comm_net_pct_oi = comm_net / open_interest`
- `nr_net_pct_oi = nr_net / open_interest`
- `nc_flow_pct_oi_1w = nc_net_chg_1w / open_interest`
- Для кожної з цих метрик: `_pos_all`, `_pos_5y`

---

## Основний файл для UI
UI читає тільки:  
- `data/compute/metrics_weekly.parquet`

---

## Додаткові метрики для UI (shared scale + heatlines)

### Heatline для *_chg_1w
Для кожної групи P ∈ {nc, comm, nr} і метрики M ∈ {long, short, total, net}:
- `{P}_{M}_chg_1w_min_all`
- `{P}_{M}_chg_1w_max_all`
- `{P}_{M}_chg_1w_pos_all`
- `{P}_{M}_chg_1w_min_5y`
- `{P}_{M}_chg_1w_max_5y`
- `{P}_{M}_chg_1w_pos_5y`

### Спільна шкала для nc/comm
**Net positions (nc_net + comm_net):**
- `fc_net_min_all`, `fc_net_max_all`
- `fc_net_pos_nc_all`, `fc_net_pos_comm_all`
- `fc_net_min_5y`, `fc_net_max_5y`
- `fc_net_pos_nc_5y`, `fc_net_pos_comm_5y`

**Net Δ1w (nc_net_chg_1w + comm_net_chg_1w):**
- `fc_net_chg_min_all`, `fc_net_chg_max_all`
- `fc_net_chg_pos_nc_all`, `fc_net_chg_pos_comm_all`
- `fc_net_chg_min_5y`, `fc_net_chg_max_5y`
- `fc_net_chg_pos_nc_5y`, `fc_net_chg_pos_comm_5y`
