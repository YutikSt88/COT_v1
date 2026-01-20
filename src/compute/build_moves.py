"""Build moves table with percentile rankings of week-over-week absolute changes."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_moves_weekly(changes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build moves table with percentile rankings of absolute week-over-week changes.
    
    For each (market_key, metric), calculates percentile of abs(chg_1w) within entire history.
    Formula: rank(abs(chg_1w_t)) / count(non-null abs(chg_1w))
    
    Args:
        changes_df: Changes DataFrame with market_key, report_date, *_chg_1w columns
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - Move percentiles (all-time): {group}_{metric}_move_pct_all
        - Move percentiles (5Y=260w): {group}_{metric}_move_pct_5y
    """
    logger.info("[moves] building moves table with percentile rankings...")
    
    # Ensure sorted by market_key, report_date
    df = changes_df.sort_values(["market_key", "report_date"]).reset_index(drop=True).copy()
    
    # Build identity columns
    moves = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
    })
    
    # Groups and metrics to process
    groups = ["nc", "comm", "nr"]
    metrics = ["long", "short", "total", "net"]
    
    for group in groups:
        for metric in metrics:
            chg_col = f"{group}_{metric}_chg_1w"
            
            # Skip if column doesn't exist
            if chg_col not in df.columns:
                continue
            
            # For each market_key, calculate percentile rank of absolute change (all-time)
            # Formula: rank(abs(chg_1w_t)) / count(non-null abs(chg_1w))
            # rank(method='min') gives 1-based rank, divide by total count to get [0, 1] percentile
            def calc_percentile(x):
                abs_vals = x.abs()
                non_null_count = abs_vals.notna().sum()
                if non_null_count == 0:
                    return pd.Series(np.nan, index=x.index)
                # rank(method='min') gives 1-based ranks (1, 2, 3, ...)
                # To get percentile in [0, 1], we use: (rank - 1) / (count - 1)
                # But if count == 1, then rank=1, percentile should be 1.0 (or 0.0?)
                # Standard percentile formula: rank / count gives [0, 1]
                ranks = abs_vals.rank(method="min", na_option="keep")
                # Divide by non_null_count to get percentile in [0, 1]
                # When rank=1 and count=1: 1/1 = 1.0 (100th percentile, highest)
                # When rank=1 and count=10: 1/10 = 0.1 (10th percentile)
                # When rank=10 and count=10: 10/10 = 1.0 (100th percentile)
                return ranks / non_null_count
            
            move_pct = df.groupby("market_key")[chg_col].transform(calc_percentile)
            
            # Set to NaN where original chg_1w is NaN
            move_pct = move_pct.where(df[chg_col].notna(), np.nan)
            
            # Store result
            result_col = f"{group}_{metric}_move_pct_all"
            moves[result_col] = move_pct.astype("float64")

            # 5Y percentile (260-week rolling window, min_periods=52)
            def calc_rolling_percentile(window_vals: np.ndarray) -> float:
                target = window_vals[-1]
                if np.isnan(target):
                    return np.nan
                valid = window_vals[~np.isnan(window_vals)]
                if len(valid) == 0:
                    return np.nan
                rank = np.sum(valid <= target)
                return rank / len(valid)

            abs_series = df[chg_col].abs()
            move_pct_5y = (
                abs_series.groupby(df["market_key"])
                .transform(lambda x: x.rolling(window=260, min_periods=52).apply(calc_rolling_percentile, raw=True))
            )
            move_pct_5y = move_pct_5y.where(df[chg_col].notna(), np.nan)
            moves[f"{group}_{metric}_move_pct_5y"] = move_pct_5y.astype("float64")
    
    logger.info(f"[moves] built {len(moves)} rows, {len(moves.columns)} columns")
    
    # Count move_pct columns
    move_pct_cols = [col for col in moves.columns if "_move_pct_" in col]
    logger.info(f"[moves] move percentile columns: {len(move_pct_cols)}")
    logger.info(f"[moves] columns: {list(moves.columns)}")
    
    return moves
