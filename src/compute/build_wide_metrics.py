"""Build wide metrics table as join of positions, changes, rolling, extremes."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_wide_metrics(
    positions: pd.DataFrame,
    changes: pd.DataFrame,
    flows: pd.DataFrame,
    rolling: pd.DataFrame,
    extremes: pd.DataFrame,
    moves: pd.DataFrame,
    canonical: pd.DataFrame,
    market_to_category: dict[str, str],
    market_to_contract: dict[str, str],
) -> pd.DataFrame:
    """
    Build wide metrics table as join of semantic tables.
    
    Args:
        positions: Positions DataFrame with market_key, report_date, nc_long, etc.
        changes: Changes DataFrame with market_key, report_date, *_chg_1w, etc.
        flows: Flows DataFrame with market_key, report_date, *_flow_1w, *_rotation_1w, etc.
        rolling: Rolling DataFrame with market_key, report_date, *_ma_13w, etc.
        extremes: Extremes DataFrame with market_key, report_date, *_min_all, etc.
        moves: Moves DataFrame with market_key, report_date, *_move_pct_all, etc.
        canonical: Canonical DataFrame (for open_interest_all, contract_code)
        market_to_category: Mapping from market_key to category
        market_to_contract: Mapping from market_key to contract_code
    
    Returns:
        Wide DataFrame with all columns from positions, changes, flows, rolling, extremes, moves
        plus category, contract_code, open_interest, spec_vs_hedge_net
    """
    logger.info("[wide_metrics] building wide metrics table as join of semantic tables...")
    
    # Normalize keys before join
    # Ensure all DataFrames have consistent key types
    for df_name, df in [
        ("positions", positions),
        ("changes", changes),
        ("flows", flows),
        ("rolling", rolling),
        ("extremes", extremes),
        ("moves", moves),
    ]:
        df["market_key"] = df["market_key"].astype(str)
        df["report_date"] = pd.to_datetime(df["report_date"]).dt.tz_localize(None)
        logger.info(f"[wide_metrics] normalized keys in {df_name}: {len(df)} rows")
    
    # Validate uniqueness before join
    join_keys = ["market_key", "report_date"]
    
    for df_name, df in [
        ("positions", positions),
        ("changes", changes),
        ("flows", flows),
        ("rolling", rolling),
        ("extremes", extremes),
        ("moves", moves),
    ]:
        duplicates = df.duplicated(subset=join_keys).sum()
        if duplicates > 0:
            raise ValueError(
                f"{df_name} has {duplicates} duplicate (market_key, report_date) pairs. "
                f"All DataFrames must have unique keys before join."
            )
        logger.info(f"[wide_metrics] {df_name}: {len(df)} rows, unique keys: {len(df.drop_duplicates(subset=join_keys))} rows")
    
    # Check for column collisions (except join keys)
    all_columns = set()
    collisions = []
    
    for df_name, df in [
        ("positions", positions),
        ("changes", changes),
        ("flows", flows),
        ("rolling", rolling),
        ("extremes", extremes),
        ("moves", moves),
    ]:
        df_cols = set(df.columns) - set(join_keys)
        for col in df_cols:
            if col in all_columns:
                collisions.append(f"{col} (exists in multiple tables)")
            all_columns.add(col)
    
    if collisions:
        raise ValueError(
            f"Column collisions detected (except join keys): {', '.join(collisions)}. "
            f"All columns except {join_keys} must be unique across semantic tables."
        )
    
    logger.info(f"[wide_metrics] no column collisions detected. Total unique columns: {len(all_columns)}")
    
    # Start with positions as base
    wide = positions.copy()
    logger.info(f"[wide_metrics] base (positions): {len(wide)} rows, {len(wide.columns)} columns")
    
    # Left join changes
    wide = wide.merge(changes, on=join_keys, how="left", validate="1:1")
    logger.info(f"[wide_metrics] after join changes: {len(wide)} rows, {len(wide.columns)} columns")
    
    # Left join flows
    wide = wide.merge(flows, on=join_keys, how="left", validate="1:1")
    # Count new schema columns (gross/net_abs/rotation/net_share/rotation_share)
    flow_cols_count = len([c for c in wide.columns if "_gross_chg_1w" in c or "_net_abs_chg_1w" in c or "_rotation_1w" in c or "_net_share_1w" in c or "_rotation_share_1w" in c])
    logger.info(f"[wide_metrics] after join flows: {len(wide)} rows, {len(wide.columns)} columns, {flow_cols_count} flow/rotation columns added")
    
    # Left join rolling
    wide = wide.merge(rolling, on=join_keys, how="left", validate="1:1")
    logger.info(f"[wide_metrics] after join rolling: {len(wide)} rows, {len(wide.columns)} columns")
    
    # Left join extremes
    wide = wide.merge(extremes, on=join_keys, how="left", validate="1:1")
    logger.info(f"[wide_metrics] after join extremes: {len(wide)} rows, {len(wide.columns)} columns")
    
    # Left join moves
    wide = wide.merge(moves, on=join_keys, how="left", validate="1:1")
    logger.info(f"[wide_metrics] after join moves: {len(wide)} rows, {len(wide.columns)} columns")
    
    # Validate 1:1 join result
    if len(wide) != len(positions):
        raise ValueError(
            f"Join result has {len(wide)} rows but positions has {len(positions)} rows. "
            f"Expected 1:1 join (all rows from positions must be preserved)."
        )
    
    # Check for duplicates after join
    duplicates_after = wide.duplicated(subset=join_keys).sum()
    if duplicates_after > 0:
        raise ValueError(
            f"Wide metrics has {duplicates_after} duplicate (market_key, report_date) pairs after join. "
            f"This should not happen with 1:1 joins."
        )
    
    # Add category and contract_code from mappings
    wide["category"] = wide["market_key"].map(market_to_category)
    wide["contract_code"] = wide["market_key"].map(market_to_contract)
    
    # Add open_interest from canonical
    # First, normalize canonical keys
    canonical_normalized = canonical.copy()
    canonical_normalized["market_key"] = canonical_normalized["market_key"].astype(str)
    canonical_normalized["report_date"] = pd.to_datetime(canonical_normalized["report_date"]).dt.tz_localize(None)
    
    # Merge open_interest_all from canonical (need contract_code match or just use latest per market_key+report_date)
    # Since canonical may have multiple rows per (market_key, report_date) if there are multiple contract_codes,
    # we'll aggregate or take first
    canonical_oi = canonical_normalized.groupby(join_keys)["open_interest_all"].first().reset_index()
    canonical_oi.columns = ["market_key", "report_date", "open_interest"]
    wide = wide.merge(canonical_oi, on=join_keys, how="left", validate="1:1")
    
    # Calculate Open Interest weekly change metrics (if open_interest exists)
    if "open_interest" in wide.columns:
        # Ensure sorted by market_key and report_date for shift to work correctly
        wide = wide.sort_values(["market_key", "report_date"]).reset_index(drop=True)
        
        # Calculate absolute change: current - previous week (using diff)
        wide["open_interest_chg_1w"] = wide.groupby("market_key")["open_interest"].diff(1)
        
        # Get previous week's open_interest for percentage calculation
        oi_prev = wide.groupby("market_key")["open_interest"].shift(1)
        oi_prev_numeric = pd.to_numeric(oi_prev, errors="coerce")
        
        # Calculate percentage change: chg_1w / abs(prev)
        # Edge cases: if prev is NaN or == 0 → pct = NaN
        wide["open_interest_chg_1w_pct"] = np.where(
            oi_prev.notna() & (oi_prev_numeric != 0),
            wide["open_interest_chg_1w"] / oi_prev_numeric,
            np.nan
        )
        
        # Calculate Open Interest positioning metrics (ALL window and 5Y rolling window)
        # ALL window: min/max/pos across entire history per market_key
        oi_current = pd.to_numeric(wide["open_interest"], errors="coerce")
        min_oi_all = wide.groupby("market_key")["open_interest"].transform("min")
        max_oi_all = wide.groupby("market_key")["open_interest"].transform("max")
        diff_oi_all = max_oi_all - min_oi_all
        # Calculate position: (current - min) / (max - min)
        # If min == max, set to 0.5 (as per requirements)
        pos_oi_all = np.where(
            diff_oi_all > 0,
            (oi_current - min_oi_all) / diff_oi_all,
            np.where(oi_current.notna(), 0.5, np.nan)  # If min == max and current is not NaN, set to 0.5
        )
        wide["open_interest_pos_all"] = pos_oi_all
        
        # 5Y rolling window: 260 weeks, min_periods=52
        min_oi_5y = wide.groupby("market_key")["open_interest"].transform(
            lambda x: x.rolling(window=260, min_periods=52).min()
        )
        max_oi_5y = wide.groupby("market_key")["open_interest"].transform(
            lambda x: x.rolling(window=260, min_periods=52).max()
        )
        diff_oi_5y = max_oi_5y - min_oi_5y
        # Calculate position: (current - min_5y) / (max_5y - min_5y)
        # If min_5y == max_5y (and both are not NaN), set to 0.5
        pos_oi_5y = np.where(
            (diff_oi_5y > 0) & min_oi_5y.notna() & max_oi_5y.notna(),
            (oi_current - min_oi_5y) / diff_oi_5y,
            np.where(
                (diff_oi_5y == 0) & min_oi_5y.notna() & max_oi_5y.notna() & oi_current.notna(),
                0.5,  # If min == max and current is not NaN, set to 0.5
                np.nan
            )
        )
        wide["open_interest_pos_5y"] = pos_oi_5y
        
        # Convert to float64
        wide["open_interest_pos_all"] = pd.to_numeric(wide["open_interest_pos_all"], errors="coerce").astype("float64")
        wide["open_interest_pos_5y"] = pd.to_numeric(wide["open_interest_pos_5y"], errors="coerce").astype("float64")

        # Open Interest percentile ranks (all-time and 5Y)
        def calc_percentile_rank(x: pd.Series) -> pd.Series:
            valid = x.dropna()
            count = len(valid)
            if count == 0:
                return pd.Series(np.nan, index=x.index)
            ranks = x.rank(method="min", na_option="keep")
            return ranks / count

        def calc_rolling_percentile(window_vals: np.ndarray) -> float:
            target = window_vals[-1]
            if np.isnan(target):
                return np.nan
            valid = window_vals[~np.isnan(window_vals)]
            if len(valid) == 0:
                return np.nan
            rank = np.sum(valid <= target)
            return rank / len(valid)

        oi_series = pd.to_numeric(wide["open_interest"], errors="coerce").astype("float64")
        wide["open_interest_pct_all"] = (
            oi_series.groupby(wide["market_key"]).transform(calc_percentile_rank).astype("float64")
        )
        wide["open_interest_pct_5y"] = (
            oi_series.groupby(wide["market_key"])
            .transform(lambda x: x.rolling(window=260, min_periods=52).apply(calc_rolling_percentile, raw=True))
            .astype("float64")
        )

        # OI change percentile ranks (based on abs(open_interest_chg_1w_pct))
        oi_chg_pct_abs = pd.to_numeric(wide["open_interest_chg_1w_pct"], errors="coerce").abs()
        wide["open_interest_chg_pct_rank_all"] = (
            oi_chg_pct_abs.groupby(wide["market_key"]).transform(calc_percentile_rank).astype("float64")
        )
        wide["open_interest_chg_pct_rank_5y"] = (
            oi_chg_pct_abs.groupby(wide["market_key"])
            .transform(lambda x: x.rolling(window=260, min_periods=52).apply(calc_rolling_percentile, raw=True))
            .astype("float64")
        )

        # OI change z-scores (based on open_interest_chg_1w_pct)
        oi_chg_pct = pd.to_numeric(wide["open_interest_chg_1w_pct"], errors="coerce").astype("float64")
        z_52_mean = oi_chg_pct.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=52, min_periods=26).mean()
        )
        z_52_std = oi_chg_pct.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=52, min_periods=26).std(ddof=0)
        )
        wide["open_interest_chg_z_52w"] = np.where(
            z_52_std > 0,
            (oi_chg_pct - z_52_mean) / z_52_std,
            np.nan,
        ).astype("float64")

        z_260_mean = oi_chg_pct.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=260, min_periods=52).mean()
        )
        z_260_std = oi_chg_pct.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=260, min_periods=52).std(ddof=0)
        )
        wide["open_interest_chg_z_260w"] = np.where(
            z_260_std > 0,
            (oi_chg_pct - z_260_mean) / z_260_std,
            np.nan,
        ).astype("float64")

        # OI regime and strength (based on change sign + change percentile)
        chg = oi_chg_pct
        regime = np.where(chg > 0, "Expansion", np.where(chg < 0, "Contraction", "Flat"))
        regime = np.where(chg.notna(), regime, "N/A")
        wide["open_interest_regime_all"] = regime
        wide["open_interest_regime_5y"] = regime

        def strength_label(pct_series: pd.Series) -> pd.Series:
            return pd.Series(
                np.select(
                    [pct_series < 0.33, (pct_series >= 0.33) & (pct_series <= 0.67), pct_series > 0.67],
                    ["Weak", "Moderate", "Strong"],
                    default="N/A",
                ),
                index=pct_series.index,
            )

        wide["open_interest_regime_strength_all"] = strength_label(wide["open_interest_chg_pct_rank_all"])
        wide["open_interest_regime_strength_5y"] = strength_label(wide["open_interest_chg_pct_rank_5y"])
    else:
        # If open_interest column doesn't exist, set all OI metrics to NaN
        wide["open_interest_chg_1w"] = np.nan
        wide["open_interest_chg_1w_pct"] = np.nan
        wide["open_interest_pos_all"] = np.nan
        wide["open_interest_pos_5y"] = np.nan
        wide["open_interest_pct_all"] = np.nan
        wide["open_interest_pct_5y"] = np.nan
        wide["open_interest_chg_pct_rank_all"] = np.nan
        wide["open_interest_chg_pct_rank_5y"] = np.nan
        wide["open_interest_chg_z_52w"] = np.nan
        wide["open_interest_chg_z_260w"] = np.nan
        wide["open_interest_regime_all"] = "N/A"
        wide["open_interest_regime_5y"] = "N/A"
        wide["open_interest_regime_strength_all"] = "N/A"
        wide["open_interest_regime_strength_5y"] = "N/A"
        logger.warning("[wide_metrics] open_interest missing, setting OI metrics to NaN")
    
    # Calculate spec_vs_hedge_net (nc_net - comm_net) if both exist
    if "nc_net" in wide.columns and "comm_net" in wide.columns:
        wide["spec_vs_hedge_net"] = wide["nc_net"] - wide["comm_net"]
    else:
        wide["spec_vs_hedge_net"] = np.nan
        logger.warning("[wide_metrics] nc_net or comm_net missing, setting spec_vs_hedge_net to NaN")

    # WoW change for spec_vs_hedge_net
    wide["spec_vs_hedge_net_chg_1w"] = wide.groupby("market_key")["spec_vs_hedge_net"].diff(1)
    
    # Calculate OI-based metrics: Funds, Commercials, and Non-Reported Net % OI
    logger.info("[wide_metrics] calculating OI-based metrics...")
    
    # Note: wide is already sorted above if open_interest was processed
    # If open_interest doesn't exist, ensure sorted for percentile calculations
    if "open_interest" not in wide.columns:
        wide = wide.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Funds Net % OI: nc_net_pct_oi = nc_net / open_interest
    if "nc_net" in wide.columns and "open_interest" in wide.columns:
        # Convert to numeric
        nc_net_numeric = pd.to_numeric(wide["nc_net"], errors="coerce")
        open_interest_numeric = pd.to_numeric(wide["open_interest"], errors="coerce")
        
        # Calculate: nc_net / open_interest
        # Edge case: if open_interest == 0 or NaN → result NaN
        wide["nc_net_pct_oi"] = np.where(
            (open_interest_numeric > 0) & open_interest_numeric.notna(),
            nc_net_numeric / open_interest_numeric,
            np.nan
        )
    else:
        wide["nc_net_pct_oi"] = np.nan
        logger.warning("[wide_metrics] nc_net or open_interest missing, setting nc_net_pct_oi to NaN")
    
    # Commercials Net % OI: comm_net_pct_oi = comm_net / open_interest
    if "comm_net" in wide.columns and "open_interest" in wide.columns:
        # Convert to numeric
        comm_net_numeric = pd.to_numeric(wide["comm_net"], errors="coerce")
        open_interest_numeric = pd.to_numeric(wide["open_interest"], errors="coerce")
        
        # Calculate: comm_net / open_interest
        # Edge case: if open_interest == 0 or NaN → result NaN
        wide["comm_net_pct_oi"] = np.where(
            (open_interest_numeric > 0) & open_interest_numeric.notna(),
            comm_net_numeric / open_interest_numeric,
            np.nan
        )
    else:
        wide["comm_net_pct_oi"] = np.nan
        logger.warning("[wide_metrics] comm_net or open_interest missing, setting comm_net_pct_oi to NaN")
    
    # Non-Reported Net % OI: nr_net_pct_oi = nr_net / open_interest
    if "nr_net" in wide.columns and "open_interest" in wide.columns:
        # Convert to numeric
        nr_net_numeric = pd.to_numeric(wide["nr_net"], errors="coerce")
        open_interest_numeric = pd.to_numeric(wide["open_interest"], errors="coerce")
        
        # Calculate: nr_net / open_interest
        # Edge case: if open_interest == 0 or NaN → result NaN
        wide["nr_net_pct_oi"] = np.where(
            (open_interest_numeric > 0) & open_interest_numeric.notna(),
            nr_net_numeric / open_interest_numeric,
            np.nan
        )
    else:
        wide["nr_net_pct_oi"] = np.nan
        logger.warning("[wide_metrics] nr_net or open_interest missing, setting nr_net_pct_oi to NaN")
    
    # Funds Flow % OI (1w): nc_flow_pct_oi_1w = nc_net_chg_1w / open_interest
    if "nc_net_chg_1w" in wide.columns and "open_interest" in wide.columns:
        # Convert to numeric
        nc_net_chg_numeric = pd.to_numeric(wide["nc_net_chg_1w"], errors="coerce")
        open_interest_numeric = pd.to_numeric(wide["open_interest"], errors="coerce")
        
        # Calculate: nc_net_chg_1w / open_interest
        # Edge case: if open_interest == 0 or NaN → result NaN
        wide["nc_flow_pct_oi_1w"] = np.where(
            (open_interest_numeric > 0) & open_interest_numeric.notna(),
            nc_net_chg_numeric / open_interest_numeric,
            np.nan
        )
    else:
        wide["nc_flow_pct_oi_1w"] = np.nan
        logger.warning("[wide_metrics] nc_net_chg_1w or open_interest missing, setting nc_flow_pct_oi_1w to NaN")
    
    # Calculate percentile/position metrics for OI-based metrics
    oi_metrics = ["nc_net_pct_oi", "comm_net_pct_oi", "nr_net_pct_oi", "nc_flow_pct_oi_1w"]
    
    for metric_col in oi_metrics:
        if metric_col not in wide.columns:
            continue
        
        # ALL-TIME percentile/position
        min_all = wide.groupby("market_key")[metric_col].transform("min")
        max_all = wide.groupby("market_key")[metric_col].transform("max")
        
        # Calculate position: (current - min) / (max - min)
        # If min == max, set to 0.5 (as per requirements)
        current = wide[metric_col]
        diff = max_all - min_all
        pos_all = np.where(
            diff > 0,
            (current - min_all) / diff,
            np.where(current.notna(), 0.5, np.nan)  # If min == max and current is not NaN, set to 0.5
        )
        wide[f"{metric_col}_pos_all"] = pos_all
        
        # 5Y trailing window percentile/position (260 weeks, min_periods=52)
        min_5y = wide.groupby("market_key")[metric_col].transform(
            lambda x: x.rolling(window=260, min_periods=52).min()
        )
        max_5y = wide.groupby("market_key")[metric_col].transform(
            lambda x: x.rolling(window=260, min_periods=52).max()
        )
        
        # Calculate position: (current - min_5y) / (max_5y - min_5y)
        # If min_5y == max_5y (and both are not NaN), set to 0.5
        diff_5y = max_5y - min_5y
        pos_5y = np.where(
            (diff_5y > 0) & min_5y.notna() & max_5y.notna(),
            (current - min_5y) / diff_5y,
            np.where(
                (diff_5y == 0) & min_5y.notna() & max_5y.notna() & current.notna(),
                0.5,  # If min == max and current is not NaN, set to 0.5
                np.nan
            )
        )
        wide[f"{metric_col}_pos_5y"] = pos_5y
        
        # Convert to float64
        wide[f"{metric_col}_pos_all"] = pd.to_numeric(wide[f"{metric_col}_pos_all"], errors="coerce").astype("float64")
        wide[f"{metric_col}_pos_5y"] = pd.to_numeric(wide[f"{metric_col}_pos_5y"], errors="coerce").astype("float64")
    
    logger.info("[wide_metrics] OI-based metrics calculated")

    # OI advanced metrics (z-scores, deltas, regime/driver/risk)
    logger.info("[wide_metrics] calculating advanced OI metrics...")
    if "open_interest" in wide.columns and "open_interest_chg_1w" in wide.columns:
        oi_series = pd.to_numeric(wide["open_interest"], errors="coerce").astype("float64")
        oi_chg_1w = pd.to_numeric(wide["open_interest_chg_1w"], errors="coerce").astype("float64")

        # z-score 52w and 260w (min 26 / 52)
        oi_mean_52 = oi_series.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=52, min_periods=26).mean()
        )
        oi_std_52 = oi_series.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=52, min_periods=26).std(ddof=0)
        )
        wide["oi_z_52w"] = np.where(
            oi_std_52 > 0,
            (oi_series - oi_mean_52) / oi_std_52,
            np.nan,
        ).astype("float64")

        oi_mean_260 = oi_series.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=260, min_periods=52).mean()
        )
        oi_std_260 = oi_series.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=260, min_periods=52).std(ddof=0)
        )
        wide["oi_z_260w"] = np.where(
            oi_std_260 > 0,
            (oi_series - oi_mean_260) / oi_std_260,
            np.nan,
        ).astype("float64")

        # 4w delta and acceleration (1w vs avg 4w)
        oi_4w_ago = oi_series.groupby(wide["market_key"]).shift(4)
        wide["oi_delta_4w"] = (oi_series - oi_4w_ago).astype("float64")
        wide["oi_acceleration"] = (oi_chg_1w - (wide["oi_delta_4w"] / 4.0)).astype("float64")

        # small_threshold = 0.05 * median(|oi_delta_1w| over 52w)
        abs_oi_delta = oi_chg_1w.abs()
        oi_median_abs_52 = abs_oi_delta.groupby(wide["market_key"]).transform(
            lambda x: x.rolling(window=52, min_periods=26).median()
        )
        small_threshold = 0.05 * oi_median_abs_52

        # Regime (N/A if required inputs are NaN)
        oi_z_52 = wide["oi_z_52w"]
        accel = wide["oi_acceleration"]
        delta_1w = oi_chg_1w

        regime_base = np.select(
            [
                (delta_1w > 0) & (accel > 0) & (oi_z_52 < 1.5),
                (delta_1w > 0) & (accel >= 0) & (oi_z_52 >= 1.5),
                (delta_1w < 0) & (oi_z_52 >= 1.5),
                (delta_1w.abs() <= small_threshold) & (oi_z_52.abs() < 1.0),
                (delta_1w > 0) & (oi_z_52 <= -1.0),
            ],
            [
                "Expansion_Early",
                "Expansion_Late",
                "Distribution",
                "Neutral",
                "Rebuild",
            ],
            default="Mixed",
        )
        missing_regime = delta_1w.isna() | accel.isna() | oi_z_52.isna() | small_threshold.isna()
        wide["oi_regime"] = np.where(missing_regime, "N/A", regime_base)

        # OI driver
        abs_funds = pd.to_numeric(wide.get("nc_net_chg_1w"), errors="coerce").abs()
        abs_comm = pd.to_numeric(wide.get("comm_net_chg_1w"), errors="coerce").abs()
        total_abs = abs_funds + abs_comm
        share_funds = np.where(total_abs > 0, abs_funds / total_abs, np.nan)
        share_comm = np.where(total_abs > 0, abs_comm / total_abs, np.nan)
        driver_base = np.select(
            [
                total_abs == 0,
                share_funds >= 0.6,
                share_comm >= 0.6,
            ],
            [
                "N/A",
                "Funds",
                "Commercials",
            ],
            default="Mixed",
        )
        missing_driver = total_abs.isna()
        wide["oi_driver"] = np.where(missing_driver, "N/A", driver_base)

        # OI risk level
        risk_score = np.zeros(len(wide), dtype="float64")
        risk_score += np.where(oi_z_52 >= 1.5, 1, 0)
        risk_score += np.where(oi_z_52 >= 2.0, 1, 0)
        pos_funds = wide.get("positioning_funds")
        if pos_funds is not None:
            pos_funds_str = pos_funds.astype(str)
            risk_score += np.where(pos_funds_str.str.startswith("Crowded"), 1, 0)
        conflict_level = wide.get("conflict_level")
        if conflict_level is not None:
            conflict_str = conflict_level.astype(str)
            risk_score += np.where(conflict_str == "High", 1, 0)

        risk_level = np.select(
            [risk_score <= 1, risk_score == 2, risk_score >= 3],
            ["Low", "Elevated", "High"],
            default="N/A",
        )
        missing_risk = oi_z_52.isna()
        wide["oi_risk_level"] = np.where(missing_risk, "N/A", risk_level)
    else:
        wide["oi_z_52w"] = np.nan
        wide["oi_z_260w"] = np.nan
        wide["oi_delta_4w"] = np.nan
        wide["oi_acceleration"] = np.nan
        wide["oi_regime"] = "N/A"
        wide["oi_driver"] = "N/A"
        wide["oi_risk_level"] = "N/A"

    # Changes heatline metrics (min/max/pos) for *_chg_1w
    logger.info("[wide_metrics] calculating chg_1w heatline metrics...")
    chg_groups = ["nc", "comm", "nr"]
    chg_metrics = ["long", "short", "total", "net"]
    for group in chg_groups:
        for metric in chg_metrics:
            chg_col = f"{group}_{metric}_chg_1w"
            if chg_col not in wide.columns:
                continue

            series = pd.to_numeric(wide[chg_col], errors="coerce").astype("float64")

            min_all = wide.groupby("market_key")[chg_col].transform("min")
            max_all = wide.groupby("market_key")[chg_col].transform("max")
            diff_all = max_all - min_all
            pos_all = np.where(
                diff_all > 0,
                (series - min_all) / diff_all,
                np.where(series.notna(), 0.5, np.nan)
            )

            wide[f"{chg_col}_min_all"] = pd.to_numeric(min_all, errors="coerce").astype("float64")
            wide[f"{chg_col}_max_all"] = pd.to_numeric(max_all, errors="coerce").astype("float64")
            wide[f"{chg_col}_pos_all"] = pd.to_numeric(pos_all, errors="coerce").astype("float64")

            min_5y = wide.groupby("market_key")[chg_col].transform(
                lambda x: x.rolling(window=260, min_periods=52).min()
            )
            max_5y = wide.groupby("market_key")[chg_col].transform(
                lambda x: x.rolling(window=260, min_periods=52).max()
            )
            diff_5y = max_5y - min_5y
            pos_5y = np.where(
                (diff_5y > 0) & min_5y.notna() & max_5y.notna(),
                (series - min_5y) / diff_5y,
                np.where(
                    (diff_5y == 0) & min_5y.notna() & max_5y.notna() & series.notna(),
                    0.5,
                    np.nan
                )
            )

            wide[f"{chg_col}_min_5y"] = pd.to_numeric(min_5y, errors="coerce").astype("float64")
            wide[f"{chg_col}_max_5y"] = pd.to_numeric(max_5y, errors="coerce").astype("float64")
            wide[f"{chg_col}_pos_5y"] = pd.to_numeric(pos_5y, errors="coerce").astype("float64")

    # Shared scale for nc_net + comm_net
    logger.info("[wide_metrics] calculating shared-scale net metrics (nc/comm)...")
    nc_net = pd.to_numeric(wide.get("nc_net"), errors="coerce").astype("float64")
    comm_net = pd.to_numeric(wide.get("comm_net"), errors="coerce").astype("float64")
    nc_net_chg = pd.to_numeric(wide.get("nc_net_chg_1w"), errors="coerce").astype("float64")
    comm_net_chg = pd.to_numeric(wide.get("comm_net_chg_1w"), errors="coerce").astype("float64")

    # All-time shared scale for net positions
    fc_net_min_all = wide.groupby("market_key")[["nc_net", "comm_net"]].transform("min").min(axis=1)
    fc_net_max_all = wide.groupby("market_key")[["nc_net", "comm_net"]].transform("max").max(axis=1)
    fc_net_diff_all = fc_net_max_all - fc_net_min_all
    wide["fc_net_min_all"] = pd.to_numeric(fc_net_min_all, errors="coerce").astype("float64")
    wide["fc_net_max_all"] = pd.to_numeric(fc_net_max_all, errors="coerce").astype("float64")
    wide["fc_net_pos_nc_all"] = np.where(
        fc_net_diff_all > 0,
        (nc_net - fc_net_min_all) / fc_net_diff_all,
        np.where(nc_net.notna(), 0.5, np.nan)
    ).astype("float64")
    wide["fc_net_pos_comm_all"] = np.where(
        fc_net_diff_all > 0,
        (comm_net - fc_net_min_all) / fc_net_diff_all,
        np.where(comm_net.notna(), 0.5, np.nan)
    ).astype("float64")

    # 5Y shared scale for net positions (260w)
    fc_net_min_5y = wide.groupby("market_key")[["nc_net", "comm_net"]].transform(
        lambda x: x.rolling(window=260, min_periods=52).min()
    ).min(axis=1)
    fc_net_max_5y = wide.groupby("market_key")[["nc_net", "comm_net"]].transform(
        lambda x: x.rolling(window=260, min_periods=52).max()
    ).max(axis=1)
    fc_net_diff_5y = fc_net_max_5y - fc_net_min_5y
    wide["fc_net_min_5y"] = pd.to_numeric(fc_net_min_5y, errors="coerce").astype("float64")
    wide["fc_net_max_5y"] = pd.to_numeric(fc_net_max_5y, errors="coerce").astype("float64")
    wide["fc_net_pos_nc_5y"] = np.where(
        (fc_net_diff_5y > 0) & fc_net_min_5y.notna() & fc_net_max_5y.notna(),
        (nc_net - fc_net_min_5y) / fc_net_diff_5y,
        np.where(
            (fc_net_diff_5y == 0) & nc_net.notna() & fc_net_min_5y.notna() & fc_net_max_5y.notna(),
            0.5,
            np.nan
        )
    ).astype("float64")
    wide["fc_net_pos_comm_5y"] = np.where(
        (fc_net_diff_5y > 0) & fc_net_min_5y.notna() & fc_net_max_5y.notna(),
        (comm_net - fc_net_min_5y) / fc_net_diff_5y,
        np.where(
            (fc_net_diff_5y == 0) & comm_net.notna() & fc_net_min_5y.notna() & fc_net_max_5y.notna(),
            0.5,
            np.nan
        )
    ).astype("float64")

    # All-time shared scale for net changes
    fc_net_chg_min_all = wide.groupby("market_key")[["nc_net_chg_1w", "comm_net_chg_1w"]].transform("min").min(axis=1)
    fc_net_chg_max_all = wide.groupby("market_key")[["nc_net_chg_1w", "comm_net_chg_1w"]].transform("max").max(axis=1)
    fc_net_chg_diff_all = fc_net_chg_max_all - fc_net_chg_min_all
    wide["fc_net_chg_min_all"] = pd.to_numeric(fc_net_chg_min_all, errors="coerce").astype("float64")
    wide["fc_net_chg_max_all"] = pd.to_numeric(fc_net_chg_max_all, errors="coerce").astype("float64")
    wide["fc_net_chg_pos_nc_all"] = np.where(
        fc_net_chg_diff_all > 0,
        (nc_net_chg - fc_net_chg_min_all) / fc_net_chg_diff_all,
        np.where(nc_net_chg.notna(), 0.5, np.nan)
    ).astype("float64")
    wide["fc_net_chg_pos_comm_all"] = np.where(
        fc_net_chg_diff_all > 0,
        (comm_net_chg - fc_net_chg_min_all) / fc_net_chg_diff_all,
        np.where(comm_net_chg.notna(), 0.5, np.nan)
    ).astype("float64")

    # 5Y shared scale for net changes (260w)
    fc_net_chg_min_5y = wide.groupby("market_key")[["nc_net_chg_1w", "comm_net_chg_1w"]].transform(
        lambda x: x.rolling(window=260, min_periods=52).min()
    ).min(axis=1)
    fc_net_chg_max_5y = wide.groupby("market_key")[["nc_net_chg_1w", "comm_net_chg_1w"]].transform(
        lambda x: x.rolling(window=260, min_periods=52).max()
    ).max(axis=1)
    fc_net_chg_diff_5y = fc_net_chg_max_5y - fc_net_chg_min_5y
    wide["fc_net_chg_min_5y"] = pd.to_numeric(fc_net_chg_min_5y, errors="coerce").astype("float64")
    wide["fc_net_chg_max_5y"] = pd.to_numeric(fc_net_chg_max_5y, errors="coerce").astype("float64")
    wide["fc_net_chg_pos_nc_5y"] = np.where(
        (fc_net_chg_diff_5y > 0) & fc_net_chg_min_5y.notna() & fc_net_chg_max_5y.notna(),
        (nc_net_chg - fc_net_chg_min_5y) / fc_net_chg_diff_5y,
        np.where(
            (fc_net_chg_diff_5y == 0) & nc_net_chg.notna() & fc_net_chg_min_5y.notna() & fc_net_chg_max_5y.notna(),
            0.5,
            np.nan
        )
    ).astype("float64")
    wide["fc_net_chg_pos_comm_5y"] = np.where(
        (fc_net_chg_diff_5y > 0) & fc_net_chg_min_5y.notna() & fc_net_chg_max_5y.notna(),
        (comm_net_chg - fc_net_chg_min_5y) / fc_net_chg_diff_5y,
        np.where(
            (fc_net_chg_diff_5y == 0) & comm_net_chg.notna() & fc_net_chg_min_5y.notna() & fc_net_chg_max_5y.notna(),
            0.5,
            np.nan
        )
    ).astype("float64")

    # Net z-score (52w) + Activity/Flow/Positioning + Consensus Signal
    logger.info("[wide_metrics] calculating net z-scores and traffic signal metrics...")
    wide = wide.sort_values(["market_key", "report_date"]).reset_index(drop=True)

    def _sign(series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        return np.sign(s).astype("float64")

    # Net z-score 52w (min_periods=26)
    nc_net = pd.to_numeric(wide.get("nc_net"), errors="coerce").astype("float64")
    comm_net = pd.to_numeric(wide.get("comm_net"), errors="coerce").astype("float64")

    nc_net_mean_52 = nc_net.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).mean()
    )
    nc_net_std_52 = nc_net.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).std(ddof=0)
    )
    comm_net_mean_52 = comm_net.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).mean()
    )
    comm_net_std_52 = comm_net.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).std(ddof=0)
    )

    wide["net_z_52w_funds"] = np.where(
        nc_net_std_52 > 0,
        (nc_net - nc_net_mean_52) / nc_net_std_52,
        np.nan,
    ).astype("float64")
    wide["net_z_52w_commercials"] = np.where(
        comm_net_std_52 > 0,
        (comm_net - comm_net_mean_52) / comm_net_std_52,
        np.nan,
    ).astype("float64")

    # Activity: Aggressive/Normal by rolling p75 of abs(net_delta_1w)
    nc_net_delta = pd.to_numeric(wide.get("nc_net_chg_1w"), errors="coerce").astype("float64")
    comm_net_delta = pd.to_numeric(wide.get("comm_net_chg_1w"), errors="coerce").astype("float64")
    nc_abs_delta = nc_net_delta.abs()
    comm_abs_delta = comm_net_delta.abs()

    nc_p75 = nc_abs_delta.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).quantile(0.75)
    )
    comm_p75 = comm_abs_delta.groupby(wide["market_key"]).transform(
        lambda x: x.rolling(window=52, min_periods=26).quantile(0.75)
    )

    wide["activity_funds"] = np.where(
        nc_p75.notna(),
        np.where(nc_abs_delta >= nc_p75, "Aggressive", "Normal"),
        "N/A",
    )
    wide["activity_commercials"] = np.where(
        comm_p75.notna(),
        np.where(comm_abs_delta >= comm_p75, "Aggressive", "Normal"),
        "N/A",
    )

    # Flow: Directional / Rotational
    def _flow_label(long_delta: pd.Series, short_delta: pd.Series, net_delta: pd.Series) -> pd.Series:
        long_s = pd.to_numeric(long_delta, errors="coerce")
        short_s = pd.to_numeric(short_delta, errors="coerce")
        net_s = pd.to_numeric(net_delta, errors="coerce")
        max_abs = np.maximum(long_s.abs(), short_s.abs())

        dir_condition = (
            (_sign(long_s) == -_sign(short_s)) &
            (net_s.abs() > 0.5 * max_abs)
        )
        zero_max = max_abs == 0
        one_zero = (long_s == 0) ^ (short_s == 0)
        net_zero = net_s == 0

        return pd.Series(
            np.where(
                zero_max,
                "N/A",
                np.where(
                    one_zero | net_zero,
                    "Rotational",
                    np.where(dir_condition, "Directional", "Rotational"),
                ),
            ),
            index=long_s.index,
        )

    wide["flow_funds"] = _flow_label(
        wide.get("nc_long_chg_1w"), wide.get("nc_short_chg_1w"), nc_net_delta
    )
    wide["flow_commercials"] = _flow_label(
        wide.get("comm_long_chg_1w"), wide.get("comm_short_chg_1w"), comm_net_delta
    )

    # Positioning (Funds) from net_z_52w_funds
    nc_z = wide["net_z_52w_funds"]
    wide["positioning_funds"] = pd.Series(
        np.select(
            [nc_z >= 1.5, (nc_z >= 1.0) & (nc_z < 1.5), (nc_z > -1.0) & (nc_z < 1.0),
             (nc_z <= -1.0) & (nc_z > -1.5), nc_z <= -1.5],
            ["Crowded Long", "Extended Long", "Balanced", "Extended Short", "Crowded Short"],
            default="N/A",
        ),
        index=wide.index,
    )

    # Positioning (Commercials) with Unwound override
    comm_z = wide["net_z_52w_commercials"]
    prev_comm_net = comm_net.groupby(wide["market_key"]).shift(1)
    prev_comm_z = comm_z.groupby(wide["market_key"]).shift(1)
    comm_sign_change = (_sign(comm_net_delta) == -_sign(prev_comm_net)) & (_sign(comm_net_delta) != 0) & (_sign(prev_comm_net) != 0)
    comm_unwound = (
        (wide["activity_commercials"] == "Aggressive") &
        (wide["flow_commercials"] == "Directional") &
        comm_sign_change &
        (prev_comm_z.abs() >= 1.0)
    )

    base_comm_pos = np.select(
        [comm_z >= 1.5, comm_z <= -1.5, comm_z.abs() < 1.0],
        ["Crowded Long", "Crowded Short", "Balanced"],
        default="Balanced",
    )
    wide["positioning_commercials"] = np.where(comm_unwound, "Unwound", base_comm_pos)

    # Conflict level (Funds vs Commercials)
    funds_aggressive = (wide["activity_funds"] == "Aggressive") & (wide["flow_funds"] == "Directional")
    comm_aggressive = (wide["activity_commercials"] == "Aggressive") & (wide["flow_commercials"] == "Directional")
    flows_opposite = (_sign(nc_net_delta) == -_sign(comm_net_delta)) & (_sign(nc_net_delta) != 0) & (_sign(comm_net_delta) != 0)

    wide["conflict_level"] = np.where(
        funds_aggressive & comm_aggressive & flows_opposite,
        "High",
        np.where(
            (funds_aggressive | comm_aggressive) & flows_opposite,
            "Medium",
            "Low",
        ),
    )

    # COT traffic signal (-2..+2)
    flow_score = np.where(comm_net_delta > 0, 1, 0) + np.where(nc_net_delta < 0, -1, 0)
    pos_score = np.where(nc_z >= 1.5, -1, 0) + np.where(nc_z <= -1.5, 1, 0)
    conflict_penalty = np.where(wide["conflict_level"] == "High", -1, 0)
    wide["cot_traffic_signal"] = np.clip(flow_score + pos_score + conflict_penalty, -2, 2).astype("int64")

    # Traffic Light (Funds + Commercials)
    logger.info("[wide_metrics] calculating traffic light labels...")
    def _activity_label(series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        return pd.Series(
            np.select(
                [s < 0.30, (s >= 0.30) & (s <= 0.70), s > 0.70],
                ["Quiet", "Active", "Aggressive"],
                default="N/A",
            ),
            index=series.index,
        )

    def _flow_quality_label(series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        return pd.Series(
            np.select(
                [s < 0.40, (s >= 0.40) & (s <= 0.60), s > 0.60],
                ["Directional", "Mixed", "Rotational"],
                default="N/A",
            ),
            index=series.index,
        )

    def _position_label(series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        return pd.Series(
            np.select(
                [s < 0.20, (s >= 0.20) & (s < 0.70), (s >= 0.70) & (s <= 0.90), s > 0.90],
                ["Unwound", "Neutral", "Crowded", "Extreme"],
                default="N/A",
            ),
            index=series.index,
        )

    def _deep_flag(series: pd.Series) -> pd.Series:
        s = pd.to_numeric(series, errors="coerce")
        return (s < 0.10) & s.notna()

    def _explain(group_label: str, activity: pd.Series, flow: pd.Series, pos: pd.Series, deep: pd.Series) -> pd.Series:
        base = group_label + " are " + activity + " with " + flow + "; positioning is " + pos + "."
        suffix = np.where(deep, " Positioning is in the lowest 10% (deep unwinding).", "")
        return pd.Series(np.where(activity != "N/A", base + suffix, "N/A"), index=activity.index)

    # Activity (all, 5y) from net_move_pct
    wide["nc_tl_activity_all"] = _activity_label(wide.get("nc_net_move_pct_all"))
    wide["comm_tl_activity_all"] = _activity_label(wide.get("comm_net_move_pct_all"))
    wide["nc_tl_activity_5y"] = _activity_label(wide.get("nc_net_move_pct_5y"))
    wide["comm_tl_activity_5y"] = _activity_label(wide.get("comm_net_move_pct_5y"))

    # Flow quality from rotation_share_1w
    wide["nc_tl_flow_quality"] = _flow_quality_label(wide.get("nc_rotation_share_1w"))
    wide["comm_tl_flow_quality"] = _flow_quality_label(wide.get("comm_rotation_share_1w"))

    # Positioning state from net_pos
    wide["nc_tl_position_all"] = _position_label(wide.get("nc_net_pos_all"))
    wide["comm_tl_position_all"] = _position_label(wide.get("comm_net_pos_all"))
    wide["nc_tl_position_5y"] = _position_label(wide.get("nc_net_pos_5y"))
    wide["comm_tl_position_5y"] = _position_label(wide.get("comm_net_pos_5y"))

    # Deep flags
    wide["nc_tl_position_deep_all"] = _deep_flag(wide.get("nc_net_pos_all"))
    wide["comm_tl_position_deep_all"] = _deep_flag(wide.get("comm_net_pos_all"))
    wide["nc_tl_position_deep_5y"] = _deep_flag(wide.get("nc_net_pos_5y"))
    wide["comm_tl_position_deep_5y"] = _deep_flag(wide.get("comm_net_pos_5y"))

    # Explanations
    wide["nc_tl_explain_all"] = _explain(
        "Funds",
        wide["nc_tl_activity_all"],
        wide["nc_tl_flow_quality"],
        wide["nc_tl_position_all"],
        wide["nc_tl_position_deep_all"],
    )
    wide["comm_tl_explain_all"] = _explain(
        "Commercials",
        wide["comm_tl_activity_all"],
        wide["comm_tl_flow_quality"],
        wide["comm_tl_position_all"],
        wide["comm_tl_position_deep_all"],
    )
    wide["nc_tl_explain_5y"] = _explain(
        "Funds",
        wide["nc_tl_activity_5y"],
        wide["nc_tl_flow_quality"],
        wide["nc_tl_position_5y"],
        wide["nc_tl_position_deep_5y"],
    )
    wide["comm_tl_explain_5y"] = _explain(
        "Commercials",
        wide["comm_tl_activity_5y"],
        wide["comm_tl_flow_quality"],
        wide["comm_tl_position_5y"],
        wide["comm_tl_position_deep_5y"],
    )

    # Consensus (Funds + Commercials)
    def _activity_score(label: pd.Series) -> pd.Series:
        return label.map({"Quiet": 0, "Active": 1, "Aggressive": 2}).fillna(np.nan)

    def _consensus(
        activity_nc: pd.Series,
        activity_comm: pd.Series,
        flow_nc: pd.Series,
        flow_comm: pd.Series,
        net_nc: pd.Series,
        net_comm: pd.Series,
        move_nc: pd.Series,
        move_comm: pd.Series,
        rot_nc: pd.Series,
        rot_comm: pd.Series,
        pos_nc: pd.Series,
        pos_comm: pd.Series,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        act_nc = activity_nc
        act_comm = activity_comm
        flow_nc_s = flow_nc
        flow_comm_s = flow_comm
        sign_nc = np.sign(pd.to_numeric(net_nc, errors="coerce"))
        sign_comm = np.sign(pd.to_numeric(net_comm, errors="coerce"))

        active_nc = act_nc.isin(["Active", "Aggressive"])
        active_comm = act_comm.isin(["Active", "Aggressive"])
        directional_nc = flow_nc_s == "Directional"
        directional_comm = flow_comm_s == "Directional"

        same_sign = (sign_nc > 0) & (sign_comm > 0) | (sign_nc < 0) & (sign_comm < 0)
        opposite_sign = (sign_nc > 0) & (sign_comm < 0) | (sign_nc < 0) & (sign_comm > 0)

        alignment = same_sign & active_nc & active_comm & directional_nc & directional_comm
        conflict = opposite_sign & active_nc & active_comm & directional_nc & directional_comm

        act_score_nc = _activity_score(act_nc)
        act_score_comm = _activity_score(act_comm)
        asymmetric = (np.abs(act_score_nc - act_score_comm) >= 1) | (
            (flow_nc_s == "Directional") & (flow_comm_s == "Rotational")
        ) | (
            (flow_nc_s == "Rotational") & (flow_comm_s == "Directional")
        )

        consensus_type = np.where(
            alignment,
            "Alignment",
            np.where(conflict, "Conflict", np.where(asymmetric, "Asymmetric", "Mixed")),
        )

        move_nc_s = pd.to_numeric(move_nc, errors="coerce")
        move_comm_s = pd.to_numeric(move_comm, errors="coerce")
        rot_nc_s = pd.to_numeric(rot_nc, errors="coerce")
        rot_comm_s = pd.to_numeric(rot_comm, errors="coerce")
        max_change = np.nanmax(np.vstack([move_nc_s, move_comm_s]), axis=0)
        min_rot = np.nanmin(np.vstack([rot_nc_s, rot_comm_s]), axis=0)
        high_conv = (max_change > 0.70) & (min_rot < 0.40)

        pos_nc_s = pos_nc
        pos_comm_s = pos_comm
        flow_mismatch = (flow_nc_s == "Directional") & (flow_comm_s == "Rotational") | (
            (flow_nc_s == "Rotational") & (flow_comm_s == "Directional")
        )
        pos_mismatch = pos_nc_s.isin(["Crowded", "Extreme"]) & pos_comm_s.isin(["Unwound"]) | (
            pos_comm_s.isin(["Crowded", "Extreme"]) & pos_nc_s.isin(["Unwound"])
        )
        medium_conv = (consensus_type == "Asymmetric") & (flow_mismatch | pos_mismatch)

        conviction = np.where(high_conv, "High", np.where(medium_conv, "Medium", "Low"))

        def _group_phrase(group: str, flow: pd.Series, activity: pd.Series, pos: pd.Series) -> pd.Series:
            flow_l = flow.str.lower()
            activity_l = activity.str.lower()
            pos_l = pos.str.lower()
            return group + " show " + activity_l + " " + flow_l + " positioning, with " + pos_l + " exposure."

        funds_phrase = _group_phrase("Funds", flow_nc_s, act_nc, pos_nc_s)
        comm_phrase = _group_phrase("Commercials", flow_comm_s, act_comm, pos_comm_s)
        explain = np.where(
            consensus_type == "Asymmetric",
            funds_phrase + " " + comm_phrase,
            np.where(
                consensus_type == "Alignment",
                "Funds and Commercials are aligned in directional positioning.",
                np.where(
                    consensus_type == "Conflict",
                    "Funds and Commercials are in directional conflict.",
                    "Mixed signals.",
                ),
            ),
        )

        # If inputs are missing, fall back to N/A
        missing = (act_nc == "N/A") | (act_comm == "N/A") | (flow_nc_s == "N/A") | (flow_comm_s == "N/A")
        consensus_type = np.where(missing, "N/A", consensus_type)
        conviction = np.where(missing, "N/A", conviction)
        explain = np.where(missing, "N/A", explain)

        return (
            pd.Series(consensus_type, index=activity_nc.index),
            pd.Series(conviction, index=activity_nc.index),
            pd.Series(explain, index=activity_nc.index),
        )

    # All-time consensus
    cons_all = _consensus(
        wide["nc_tl_activity_all"],
        wide["comm_tl_activity_all"],
        wide["nc_tl_flow_quality"],
        wide["comm_tl_flow_quality"],
        wide.get("nc_net"),
        wide.get("comm_net"),
        wide.get("nc_net_move_pct_all"),
        wide.get("comm_net_move_pct_all"),
        wide.get("nc_rotation_share_1w"),
        wide.get("comm_rotation_share_1w"),
        wide.get("nc_tl_position_all"),
        wide.get("comm_tl_position_all"),
    )
    wide["tl_consensus_type_all"] = cons_all[0]
    wide["tl_consensus_conviction_all"] = cons_all[1]
    wide["tl_consensus_explain_all"] = cons_all[2]

    # 5Y consensus
    cons_5y = _consensus(
        wide["nc_tl_activity_5y"],
        wide["comm_tl_activity_5y"],
        wide["nc_tl_flow_quality"],
        wide["comm_tl_flow_quality"],
        wide.get("nc_net"),
        wide.get("comm_net"),
        wide.get("nc_net_move_pct_5y"),
        wide.get("comm_net_move_pct_5y"),
        wide.get("nc_rotation_share_1w"),
        wide.get("comm_rotation_share_1w"),
        wide.get("nc_tl_position_5y"),
        wide.get("comm_tl_position_5y"),
    )
    wide["tl_consensus_type_5y"] = cons_5y[0]
    wide["tl_consensus_conviction_5y"] = cons_5y[1]
    wide["tl_consensus_explain_5y"] = cons_5y[2]
    
    # Ensure report_date is timezone-naive datetime
    wide["report_date"] = pd.to_datetime(wide["report_date"]).dt.tz_localize(None)
    wide["market_key"] = wide["market_key"].astype(str)
    
    # Final uniqueness check
    duplicates_final = wide.duplicated(subset=join_keys).sum()
    if duplicates_final > 0:
        raise ValueError(
            f"Final wide metrics has {duplicates_final} duplicate (market_key, report_date) pairs. "
            f"This should not happen."
        )
    
    logger.info(f"[wide_metrics] built wide metrics: {len(wide)} rows, {len(wide.columns)} columns")
    logger.info(f"[wide_metrics] columns: {sorted(list(wide.columns))}")
    
    return wide
