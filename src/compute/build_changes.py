"""Build changes table with week-over-week changes and flow flags."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_changes(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Build changes table with week-over-week changes.
    
    Args:
        positions: Positions DataFrame with market_key, report_date, nc_long, nc_short, etc.
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - NC changes: nc_long_chg_1w, nc_short_chg_1w, nc_total_chg_1w, nc_net_chg_1w
        - COMM changes: comm_long_chg_1w, comm_short_chg_1w, comm_total_chg_1w, comm_net_chg_1w
        - NR changes: nr_long_chg_1w, nr_short_chg_1w, nr_total_chg_1w, nr_net_chg_1w
    """
    logger.info("[changes] building changes table...")
    
    # Ensure sorted by market_key, report_date
    df = positions.sort_values(["market_key", "report_date"]).reset_index(drop=True).copy()
    
    # Build identity columns
    changes = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
    })
    
    # Groups to process
    groups = ["nc", "comm", "nr"]
    
    for group in groups:
        long_col = f"{group}_long"
        short_col = f"{group}_short"
        total_col = f"{group}_total"
        net_col = f"{group}_net"
        
        # Skip if columns don't exist (e.g., nr_* might be all NaN)
        if long_col not in df.columns or short_col not in df.columns:
            continue
        
        # Week-over-week changes (current - previous)
        # Group by market_key, then diff(1) within each group
        changes[f"{long_col}_chg_1w"] = df.groupby("market_key")[long_col].transform(lambda x: x.diff(1))
        changes[f"{short_col}_chg_1w"] = df.groupby("market_key")[short_col].transform(lambda x: x.diff(1))
        changes[f"{total_col}_chg_1w"] = df.groupby("market_key")[total_col].transform(lambda x: x.diff(1))
        changes[f"{net_col}_chg_1w"] = df.groupby("market_key")[net_col].transform(lambda x: x.diff(1))
        
        # Convert to float64 and handle NaN
        for col in [f"{long_col}_chg_1w", f"{short_col}_chg_1w", f"{total_col}_chg_1w", f"{net_col}_chg_1w"]:
            changes[col] = pd.to_numeric(changes[col], errors="coerce").astype("float64")
        
    logger.info(f"[changes] built {len(changes)} rows, {len(changes.columns)} columns")
    logger.info(f"[changes] columns: {list(changes.columns)}")
    
    return changes
