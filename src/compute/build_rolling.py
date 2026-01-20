"""Build rolling averages table."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_rolling(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Build rolling averages table with 13-week moving averages.
    
    Args:
        positions: Positions DataFrame with market_key, report_date, nc_long, nc_short, etc.
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - NC rolling: nc_long_ma_13w, nc_short_ma_13w, nc_total_ma_13w, nc_net_ma_13w
        - COMM rolling: comm_long_ma_13w, comm_short_ma_13w, comm_total_ma_13w, comm_net_ma_13w
        - NR rolling: nr_long_ma_13w, nr_short_ma_13w, nr_total_ma_13w, nr_net_ma_13w
    """
    logger.info("[rolling] building rolling averages table...")
    
    # Ensure sorted by market_key, report_date
    df = positions.sort_values(["market_key", "report_date"]).reset_index(drop=True).copy()
    
    # Build identity columns
    rolling = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
    })
    
    # Groups to process
    groups = ["nc", "comm", "nr"]
    metrics = ["long", "short", "total", "net"]
    
    for group in groups:
        for metric in metrics:
            col_name = f"{group}_{metric}"
            
            # Skip if column doesn't exist
            if col_name not in df.columns:
                continue
            
            # Calculate 13-week moving average per market_key
            # Rolling window = 13, min_periods = 1 (allow fewer than 13 if needed)
            rolling[f"{col_name}_ma_13w"] = (
                df.groupby("market_key")[col_name]
                .transform(lambda x: x.rolling(window=13, min_periods=1).mean())
            )
            
            # Convert to float64
            rolling[f"{col_name}_ma_13w"] = pd.to_numeric(rolling[f"{col_name}_ma_13w"], errors="coerce").astype("float64")
    
    logger.info(f"[rolling] built {len(rolling)} rows, {len(rolling.columns)} columns")
    logger.info(f"[rolling] columns: {list(rolling.columns)}")
    
    return rolling
