"""Build positions table from canonical data."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_positions(canonical: pd.DataFrame) -> pd.DataFrame:
    """
    Build positions table with long/short/total/net for nc/comm/nr.
    
    Args:
        canonical: Canonical_full DataFrame with market_key, report_date, comm_long, comm_short, nc_long, nc_short
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - NC: nc_long, nc_short, nc_total, nc_net
        - COMM: comm_long, comm_short, comm_total, comm_net
        - NR: nr_long, nr_short, nr_total, nr_net
    """
    logger.info("[positions] building positions table...")
    
    # Filter and sort by market_key, report_date
    df = canonical.sort_values(["market_key", "report_date"]).reset_index(drop=True)
    
    # Build identity columns
    positions = pd.DataFrame({
        "market_key": df["market_key"].astype(str),
        "report_date": pd.to_datetime(df["report_date"]).dt.tz_localize(None),  # timezone-naive
    })
    
    # NC (Non-Commercial) positions
    positions["nc_long"] = pd.to_numeric(df["nc_long"], errors="coerce").astype("float64").fillna(0.0)
    positions["nc_short"] = pd.to_numeric(df["nc_short"], errors="coerce").astype("float64").fillna(0.0)
    positions["nc_total"] = positions["nc_long"] + positions["nc_short"]
    positions["nc_net"] = positions["nc_long"] - positions["nc_short"]
    
    # COMM (Commercial) positions
    positions["comm_long"] = pd.to_numeric(df["comm_long"], errors="coerce").astype("float64").fillna(0.0)
    positions["comm_short"] = pd.to_numeric(df["comm_short"], errors="coerce").astype("float64").fillna(0.0)
    positions["comm_total"] = positions["comm_long"] + positions["comm_short"]
    positions["comm_net"] = positions["comm_long"] - positions["comm_short"]
    
    # NR (Non-Reportable) positions
    if "nr_long" in df.columns and "nr_short" in df.columns:
        positions["nr_long"] = pd.to_numeric(df["nr_long"], errors="coerce").astype("float64").fillna(0.0)
        positions["nr_short"] = pd.to_numeric(df["nr_short"], errors="coerce").astype("float64").fillna(0.0)
        positions["nr_total"] = positions["nr_long"] + positions["nr_short"]
        positions["nr_net"] = positions["nr_long"] - positions["nr_short"]
    else:
        # If columns don't exist, fill with 0 to keep downstream charts stable
        positions["nr_long"] = 0.0
        positions["nr_short"] = 0.0
        positions["nr_total"] = 0.0
        positions["nr_net"] = 0.0
    
    logger.info(f"[positions] built {len(positions)} rows, {len(positions.columns)} columns")
    logger.info(f"[positions] columns: {list(positions.columns)}")
    
    return positions
