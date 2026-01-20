"""Build extremes table with all-time and 5Y trailing window extremes."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_extremes(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Build extremes table with all-time and 5Y (260-week) trailing window min/max/pos.

    Args:
        positions: Positions DataFrame with market_key, report_date, nc_long, nc_short, etc.

    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - *_min_all, *_max_all, *_pos_all (all-time)
        - *_min_5y, *_max_5y, *_pos_5y (260-week trailing window, min_periods=52)
    """
    logger.info("[extremes] building extremes table...")

    # Ensure sorted by market_key, report_date
    df = positions.sort_values(["market_key", "report_date"]).reset_index(drop=True).copy()

    # Build identity columns
    extremes = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
    })

    groups = ["nc", "comm", "nr"]
    metrics = ["long", "short", "total", "net"]

    logger.info("[extremes] calculating all-time and 260-week extremes...")
    for group in groups:
        for metric in metrics:
            col_name = f"{group}_{metric}"
            if col_name not in df.columns:
                continue

            series = pd.to_numeric(df[col_name], errors="coerce").astype("float64")

            # All-time min/max/pos
            min_all = df.groupby("market_key")[col_name].transform("min")
            max_all = df.groupby("market_key")[col_name].transform("max")
            diff_all = max_all - min_all
            pos_all = np.where(
                diff_all > 0,
                (series - min_all) / diff_all,
                np.where(series.notna(), 0.5, np.nan)
            )

            extremes[f"{col_name}_min_all"] = pd.to_numeric(min_all, errors="coerce").astype("float64")
            extremes[f"{col_name}_max_all"] = pd.to_numeric(max_all, errors="coerce").astype("float64")
            extremes[f"{col_name}_pos_all"] = pd.to_numeric(pos_all, errors="coerce").astype("float64")

            # 5Y trailing (260 weeks)
            min_5y = df.groupby("market_key")[col_name].transform(
                lambda x: x.rolling(window=260, min_periods=52).min()
            )
            max_5y = df.groupby("market_key")[col_name].transform(
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

            extremes[f"{col_name}_min_5y"] = pd.to_numeric(min_5y, errors="coerce").astype("float64")
            extremes[f"{col_name}_max_5y"] = pd.to_numeric(max_5y, errors="coerce").astype("float64")
            extremes[f"{col_name}_pos_5y"] = pd.to_numeric(pos_5y, errors="coerce").astype("float64")

    logger.info(f"[extremes] built {len(extremes)} rows, {len(extremes.columns)} columns")
    logger.info(f"[extremes] columns: {list(extremes.columns)}")

    return extremes
