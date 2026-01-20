"""Debug script to verify metrics_weekly.parquet after compute pipeline.

Checks:
1. File mtime (last modification time)
2. Column existence
3. Sample values for one market/week
4. NaN analysis
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.common.paths import ProjectPaths


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main function to verify metrics_weekly.parquet."""
    paths = ProjectPaths(REPO_ROOT)
    metrics_path = paths.data / "compute" / "metrics_weekly.parquet"
    
    print("=" * 80)
    print("DEBUG: metrics_weekly.parquet Verification")
    print("=" * 80)
    print()
    
    # Check if file exists
    if not metrics_path.exists():
        print(f"[ERROR] File does not exist: {metrics_path}")
        return 1
    
    # Get file mtime
    mtime = datetime.fromtimestamp(metrics_path.stat().st_mtime)
    print(f"File: {metrics_path}")
    print(f"Last modified: {format_datetime(mtime)}")
    print()
    
    # Read parquet
    print("Reading parquet file...")
    try:
        df = pd.read_parquet(metrics_path)
        print(f"[OK] Successfully read {len(df)} rows, {len(df.columns)} columns")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to read parquet: {e}")
        return 1
    
    # Required columns for OI tab
    required_cols = [
        "open_interest_chg_1w",
        "open_interest_chg_1w_pct",
        "open_interest_pos_all",
        "open_interest_pos_5y",
        "nc_net_pct_oi",
        "nc_net_pct_oi_pos_all",
        "nc_net_pct_oi_pos_5y",
        "nc_flow_pct_oi_1w",
        "nc_flow_pct_oi_1w_pos_all",
        "nc_flow_pct_oi_1w_pos_5y",
    ]
    
    # Check column existence
    print("Checking required columns...")
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"[ERROR] Missing columns: {', '.join(missing_cols)}")
    else:
        print(f"[OK] All {len(required_cols)} required columns exist")
    print()
    
    # Show column status
    print("Column status:")
    for col in required_cols:
        if col in df.columns:
            non_null_count = df[col].notna().sum()
            null_count = df[col].isna().sum()
            total = len(df)
            status = "[OK]" if non_null_count > 0 else "[WARN]"
            print(f"  {status:8s} {col}: {non_null_count}/{total} non-null ({null_count} null)")
        else:
            print(f"  [ERROR]  {col}: MISSING")
    print()
    
    # Get sample market/week (latest week for a market with data)
    print("Finding sample market/week...")
    
    # Try to find a market with non-null open_interest
    if "open_interest" in df.columns:
        df_with_oi = df[df["open_interest"].notna()].copy()
        if len(df_with_oi) > 0:
            # Get latest week
            df_with_oi = df_with_oi.sort_values(["market_key", "report_date"])
            sample_row = df_with_oi.iloc[-1]
            sample_market = sample_row["market_key"]
            sample_date = sample_row["report_date"]
            print(f"  Sample: market_key='{sample_market}', report_date={sample_date}")
            print()
            
            # Show sample values
            print(f"Sample values for {sample_market} / {sample_date}:")
            print("-" * 80)
            
            # Base columns
            base_cols = ["market_key", "report_date", "open_interest", "nc_net", "nc_net_chg_1w"]
            for col in base_cols:
                if col in df.columns:
                    val = sample_row[col]
                    if pd.isna(val):
                        print(f"  {col:30s}: NaN")
                    else:
                        print(f"  {col:30s}: {val}")
                else:
                    print(f"  {col:30s}: MISSING")
            print()
            
            # OI metrics
            print("  Open Interest metrics:")
            oi_cols = [
                "open_interest_chg_1w",
                "open_interest_chg_1w_pct",
                "open_interest_pos_all",
                "open_interest_pos_5y",
            ]
            for col in oi_cols:
                if col in df.columns:
                    val = sample_row[col]
                    if pd.isna(val):
                        print(f"    {col:28s}: NaN")
                    else:
                        print(f"    {col:28s}: {val}")
                else:
                    print(f"    {col:28s}: MISSING")
            print()
            
            # Funds Net % OI metrics
            print("  Funds Net % OI metrics:")
            net_pct_cols = [
                "nc_net_pct_oi",
                "nc_net_pct_oi_pos_all",
                "nc_net_pct_oi_pos_5y",
            ]
            for col in net_pct_cols:
                if col in df.columns:
                    val = sample_row[col]
                    if pd.isna(val):
                        print(f"    {col:28s}: NaN")
                    else:
                        print(f"    {col:28s}: {val}")
                else:
                    print(f"    {col:28s}: MISSING")
            print()
            
            # Funds Flow % OI metrics
            print("  Funds Flow % OI (1w) metrics:")
            flow_pct_cols = [
                "nc_flow_pct_oi_1w",
                "nc_flow_pct_oi_1w_pos_all",
                "nc_flow_pct_oi_1w_pos_5y",
            ]
            for col in flow_pct_cols:
                if col in df.columns:
                    val = sample_row[col]
                    if pd.isna(val):
                        print(f"    {col:28s}: NaN")
                    else:
                        print(f"    {col:28s}: {val}")
                else:
                    print(f"    {col:28s}: MISSING")
            print()
            
            # NaN analysis
            print("NaN Analysis:")
            print("-" * 80)
            
            # Check open_interest
            if "open_interest" in df.columns:
                oi_null_pct = (df["open_interest"].isna().sum() / len(df)) * 100
                print(f"  open_interest: {df['open_interest'].isna().sum()}/{len(df)} NaN ({oi_null_pct:.1f}%)")
                
                if oi_null_pct > 50:
                    print("    [WARN] Most open_interest values are NaN")
                    print("          -> Check if canonical has open_interest_all data")
            
            # Check open_interest_chg_1w (should have NaN only for first row per market)
            if "open_interest_chg_1w" in df.columns:
                chg_null_count = df["open_interest_chg_1w"].isna().sum()
                chg_null_pct = (chg_null_count / len(df)) * 100
                print(f"  open_interest_chg_1w: {chg_null_count}/{len(df)} NaN ({chg_null_pct:.1f}%)")
                
                if chg_null_pct > 20:
                    print("    [WARN] Many open_interest_chg_1w values are NaN")
                    print("          -> Expected: NaN only for first row per market_key")
                else:
                    print("    [OK] Expected: NaN only for first row per market_key")
            
            # Check nc_net_pct_oi
            if "nc_net_pct_oi" in df.columns:
                net_pct_null_count = df["nc_net_pct_oi"].isna().sum()
                net_pct_null_pct = (net_pct_null_count / len(df)) * 100
                print(f"  nc_net_pct_oi: {net_pct_null_count}/{len(df)} NaN ({net_pct_null_pct:.1f}%)")
                
                if net_pct_null_pct > 50:
                    print("    [WARN] Many nc_net_pct_oi values are NaN")
                    print("          -> Check if open_interest is missing or zero")
            
            # Check nc_flow_pct_oi_1w
            if "nc_flow_pct_oi_1w" in df.columns:
                flow_pct_null_count = df["nc_flow_pct_oi_1w"].isna().sum()
                flow_pct_null_pct = (flow_pct_null_count / len(df)) * 100
                print(f"  nc_flow_pct_oi_1w: {flow_pct_null_count}/{len(df)} NaN ({flow_pct_null_pct:.1f}%)")
                
                if flow_pct_null_pct > 50:
                    print("    [WARN] Many nc_flow_pct_oi_1w values are NaN")
                    print("          -> Check if open_interest is missing or zero, or nc_net_chg_1w is missing")
        else:
            print("  [WARN] No rows with non-null open_interest found")
            print("        -> Cannot show sample values")
    else:
        print("  [ERROR] open_interest column not found")
    
    print()
    print("=" * 80)
    print("[OK] Verification complete")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
