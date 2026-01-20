"""Build flows table with flow vs rotation decomposition of weekly changes."""

from __future__ import annotations

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("cot_mvp")


def build_flows_weekly(changes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build flows table with Gross vs Net vs Rotation decomposition of weekly changes.
    
    Decomposes weekly position changes into:
    - Gross: total absolute change (|ΔL| + |ΔS|)
    - Net: absolute net change (|ΔN|)
    - Rotation: gross - net (long↔short shift that doesn't change net)
    
    Args:
        changes_df: Changes DataFrame with market_key, report_date, and *_long_chg_1w / *_short_chg_1w / *_net_chg_1w columns
    
    Returns:
        DataFrame with columns:
        - Identity: market_key, report_date
        - For each group (nc, comm, nr):
          - {P}_gross_chg_1w = |ΔL| + |ΔS|
          - {P}_net_abs_chg_1w = |ΔN|
          - {P}_rotation_1w = max(gross - net_abs, 0)
          - {P}_rotation_share_1w = rotation / gross (if gross > 0 else 0)
          - {P}_net_share_1w = net_abs / gross (if gross > 0 else 0)
          - {P}_total_chg_1w_calc = ΔT = ΔL + ΔS (for QA, to avoid collision with changes.total_chg_1w)
          - {P}_net_chg_1w_calc = ΔN = ΔL - ΔS (for QA/verification)
    """
    logger.info("[flows] building flows table...")
    
    # Ensure sorted by market_key, report_date
    df = changes_df.sort_values(["market_key", "report_date"]).reset_index(drop=True).copy()
    
    # Build identity columns
    flows = pd.DataFrame({
        "market_key": df["market_key"],
        "report_date": df["report_date"],
    })
    
    # Groups to process
    groups = ["nc", "comm", "nr"]
    eps = 1e-9  # Small epsilon to avoid division by zero
    
    for group in groups:
        prefix = f"{group}_"
        long_chg_col = f"{prefix}long_chg_1w"
        short_chg_col = f"{prefix}short_chg_1w"
        net_chg_col = f"{prefix}net_chg_1w"
        
        # Check if required columns exist
        has_long = long_chg_col in df.columns
        has_short = short_chg_col in df.columns
        has_net = net_chg_col in df.columns
        
        if not (has_long and has_short):
            # Create NaN columns if missing
            flows[f"{prefix}gross_chg_1w"] = np.nan
            flows[f"{prefix}net_abs_chg_1w"] = np.nan
            flows[f"{prefix}rotation_1w"] = np.nan
            flows[f"{prefix}rotation_share_1w"] = np.nan
            flows[f"{prefix}net_share_1w"] = np.nan
            flows[f"{prefix}total_chg_1w_calc"] = np.nan
            flows[f"{prefix}net_chg_1w_calc"] = np.nan
            continue
        
        # Get changes (keep NaN to avoid fabricating first-week values)
        delta_long = pd.to_numeric(df[long_chg_col], errors="coerce")
        delta_short = pd.to_numeric(df[short_chg_col], errors="coerce")
        
        # Get actual net change from changes_df (canon)
        if has_net:
            delta_net_actual = pd.to_numeric(df[net_chg_col], errors="coerce")
            # If net change is missing but long/short are present, compute fallback
            delta_net_actual = delta_net_actual.fillna(delta_long - delta_short)
        else:
            # Fallback to calculated if net_chg_1w not available
            delta_net_actual = delta_long - delta_short
        
        # Calculate total change: ΔT = ΔL + ΔS (for QA)
        delta_total = delta_long + delta_short
        flows[f"{prefix}total_chg_1w_calc"] = delta_total.astype("float64")
        
        # Calculate net change: ΔN = ΔL - ΔS (for QA/verification)
        delta_net_calc = delta_long - delta_short
        flows[f"{prefix}net_chg_1w_calc"] = delta_net_calc.astype("float64")
        
        # Gross change: |ΔL| + |ΔS|
        abs_long = np.abs(delta_long)
        abs_short = np.abs(delta_short)
        gross_chg = abs_long + abs_short
        flows[f"{prefix}gross_chg_1w"] = gross_chg.astype("float64")
        
        # Net absolute change: |ΔN|
        net_abs_chg = np.abs(delta_net_actual)
        flows[f"{prefix}net_abs_chg_1w"] = net_abs_chg.astype("float64")
        
        # Rotation: max(gross - net_abs, 0)
        rotation_magnitude = np.maximum(gross_chg - net_abs_chg, 0.0)
        flows[f"{prefix}rotation_1w"] = rotation_magnitude.astype("float64")
        
        # Rotation share: rotation / gross (if gross > 0 else 0)
        rotation_share = pd.Series(np.nan, index=df.index, dtype="float64")
        rotation_share = rotation_share.mask(gross_chg == 0, 0.0)
        rotation_share = rotation_share.mask(gross_chg > eps, rotation_magnitude / gross_chg)
        flows[f"{prefix}rotation_share_1w"] = rotation_share
        
        # Net share: net_abs / gross (if gross > 0 else 0)
        net_share = pd.Series(np.nan, index=df.index, dtype="float64")
        net_share = net_share.mask(gross_chg == 0, 0.0)
        net_share = net_share.mask(gross_chg > eps, net_abs_chg / gross_chg)
        flows[f"{prefix}net_share_1w"] = net_share
    
    logger.info(f"[flows] built {len(flows)} rows, {len(flows.columns)} columns")
    logger.info(f"[flows] columns: {list(flows.columns)}")
    
    return flows
