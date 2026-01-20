"""Smoke test for compute module."""

from __future__ import annotations
from pathlib import Path
import pytest
import pandas as pd
import numpy as np


def test_compute_imports():
    """Test that compute modules can be imported."""
    from src.compute.run_compute import main
    from src.compute.build_positions import build_positions
    from src.compute.build_changes import build_changes
    from src.compute.build_flows import build_flows_weekly
    from src.compute.build_rolling import build_rolling
    from src.compute.build_extremes import build_extremes
    from src.compute.build_moves import build_moves_weekly
    from src.compute.validations import validate_canonical_exists
    
    assert main is not None
    assert build_positions is not None
    assert build_changes is not None
    assert build_flows_weekly is not None
    assert build_rolling is not None
    assert build_extremes is not None
    assert build_moves_weekly is not None
    assert validate_canonical_exists is not None


def test_metrics_exists_if_present():
    """Test that metrics_weekly.parquet exists and is not empty (if present)."""
    metrics_path = Path("data/compute/metrics_weekly.parquet")
    
    if metrics_path.exists():
        df = pd.read_parquet(metrics_path)
        assert len(df) > 0, "Metrics parquet should have rows"
        assert "market_key" in df.columns
        assert "report_date" in df.columns
        
        # Regression check: comm_* and nc_* must not be identical (mapping bug detection)
        if "nc_long" in df.columns and "comm_long" in df.columns:
            same_long = (df["nc_long"] == df["comm_long"]).fillna(False)
            same_short = (df["nc_short"] == df["comm_short"]).fillna(False)
            same_net = (df["nc_net"] == df["comm_net"]).fillna(False)
            same_all = same_long & same_short & same_net
            same_pct = same_all.mean()
            
            assert same_pct < 0.999, (
                f"comm_* equals nc_* for {same_pct*100:.1f}% of rows. "
                f"This indicates a mapping bug - comm_* and nc_* should represent different player groups."
            )


def test_positions_exists_if_present():
    """Test that positions_weekly.parquet exists and has required columns (if present)."""
    positions_path = Path("data/compute/positions_weekly.parquet")
    
    if positions_path.exists():
        df = pd.read_parquet(positions_path)
        assert len(df) > 0, "Positions parquet should have rows"
        assert "market_key" in df.columns, "Positions must have market_key column"
        assert "report_date" in df.columns, "Positions must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check required position columns exist
        required_cols = ["nc_long", "nc_short", "nc_total", "nc_net", 
                        "comm_long", "comm_short", "comm_total", "comm_net"]
        for col in required_cols:
            assert col in df.columns, f"Positions must have {col} column"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Positions should have unique (market_key, report_date) pairs, found {duplicates} duplicates"


def test_changes_exists_if_present():
    """Test that changes_weekly.parquet exists and has required columns (if present)."""
    changes_path = Path("data/compute/changes_weekly.parquet")
    
    if changes_path.exists():
        df = pd.read_parquet(changes_path)
        assert len(df) > 0, "Changes parquet should have rows"
        assert "market_key" in df.columns, "Changes must have market_key column"
        assert "report_date" in df.columns, "Changes must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Changes should have unique (market_key, report_date) pairs, found {duplicates} duplicates"


def test_rolling_exists_if_present():
    """Test that rolling_weekly.parquet exists and has required columns (if present)."""
    rolling_path = Path("data/compute/rolling_weekly.parquet")
    
    if rolling_path.exists():
        df = pd.read_parquet(rolling_path)
        assert len(df) > 0, "Rolling parquet should have rows"
        assert "market_key" in df.columns, "Rolling must have market_key column"
        assert "report_date" in df.columns, "Rolling must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Rolling should have unique (market_key, report_date) pairs, found {duplicates} duplicates"


def test_extremes_exists_if_present():
    """Test that extremes_weekly.parquet exists and has required columns (if present)."""
    extremes_path = Path("data/compute/extremes_weekly.parquet")
    
    if extremes_path.exists():
        df = pd.read_parquet(extremes_path)
        assert len(df) > 0, "Extremes parquet should have rows"
        assert "market_key" in df.columns, "Extremes must have market_key column"
        assert "report_date" in df.columns, "Extremes must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Extremes should have unique (market_key, report_date) pairs, found {duplicates} duplicates"


def test_metrics_wide_view_join():
    """Test that metrics_weekly.parquet is built as join of semantic tables."""
    metrics_path = Path("data/compute/metrics_weekly.parquet")
    positions_path = Path("data/compute/positions_weekly.parquet")
    
    if metrics_path.exists() and positions_path.exists():
        metrics = pd.read_parquet(metrics_path)
        positions = pd.read_parquet(positions_path)
        
        # Check that metrics has required keys
        assert "market_key" in metrics.columns, "Metrics must have market_key column"
        assert "report_date" in metrics.columns, "Metrics must have report_date column"
        
        # Check 1:1 join (metrics row count == positions row count)
        assert len(metrics) == len(positions), (
            f"Metrics row count ({len(metrics)}) must equal positions row count ({len(positions)}). "
            f"Expected 1:1 join."
        )
        
        # Check uniqueness of (market_key, report_date)
        duplicates = metrics.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, (
            f"Metrics should have unique (market_key, report_date) pairs, found {duplicates} duplicates"
        )
        
        # Check that metrics has required columns from semantic tables
        # Positions columns
        required_positions = ["nc_long", "nc_short", "nc_total", "nc_net", 
                             "comm_long", "comm_short", "comm_total", "comm_net"]
        for col in required_positions:
            assert col in metrics.columns, f"Metrics must have {col} column from positions"
        
        # Changes columns (at least one chg_1w)
        chg_cols = [col for col in metrics.columns if "_chg_1w" in col]
        assert len(chg_cols) > 0, "Metrics must have at least one _chg_1w column from changes"
        
        # Rolling columns (at least one ma_13w)
        ma_cols = [col for col in metrics.columns if "_ma_13w" in col]
        assert len(ma_cols) > 0, "Metrics must have at least one _ma_13w column from rolling"
        
        # Extremes columns (at least one min_all, max_all, pos_all, min_5y, max_5y, pos_5y)
        extremes_patterns = ["_min_all", "_max_all", "_pos_all", "_min_5y", "_max_5y", "_pos_5y"]
        extremes_cols = [col for col in metrics.columns if any(pattern in col for pattern in extremes_patterns)]
        assert len(extremes_cols) > 0, "Metrics must have at least one extremes column (min_all/max_all/pos_all/min_5y/max_5y/pos_5y)"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(metrics["report_date"]), "report_date must be datetime"


def test_moves_weekly_exists_if_present():
    """Test that moves_weekly.parquet exists and has required columns (if present)."""
    moves_path = Path("data/compute/moves_weekly.parquet")
    
    if moves_path.exists():
        df = pd.read_parquet(moves_path)
        assert len(df) > 0, "Moves parquet should have rows"
        assert "market_key" in df.columns, "Moves must have market_key column"
        assert "report_date" in df.columns, "Moves must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Moves should have unique (market_key, report_date) pairs, found {duplicates} duplicates"
        
        # Check at least one _move_pct_all column exists
        move_pct_cols = [col for col in df.columns if "_move_pct_all" in col]
        assert len(move_pct_cols) > 0, "Moves must have at least one _move_pct_all column"
        
        # Check values are in [0, 1] range (NaN allowed)
        for col in move_pct_cols:
            non_nan_values = df[col].dropna()
            if len(non_nan_values) > 0:
                min_val = non_nan_values.min()
                max_val = non_nan_values.max()
                assert min_val >= 0.0, f"{col}: minimum value {min_val} is < 0 (expected [0, 1])"
                assert max_val <= 1.0, f"{col}: maximum value {max_val} is > 1 (expected [0, 1])"


def test_flows_weekly_exists_if_present():
    """Test that flows_weekly.parquet exists and has required columns (if present)."""
    flows_path = Path("data/compute/flows_weekly.parquet")
    
    if flows_path.exists():
        df = pd.read_parquet(flows_path)
        assert len(df) > 0, "Flows parquet should have rows"
        assert "market_key" in df.columns, "Flows must have market_key column"
        assert "report_date" in df.columns, "Flows must have report_date column"
        
        # Check report_date is datetime (timezone-naive)
        assert pd.api.types.is_datetime64_any_dtype(df["report_date"]), "report_date must be datetime"
        
        # Check uniqueness of (market_key, report_date)
        duplicates = df.duplicated(subset=["market_key", "report_date"]).sum()
        assert duplicates == 0, f"Flows should have unique (market_key, report_date) pairs, found {duplicates} duplicates"
        
        # Check required columns for all groups (nc, comm, nr)
        groups = ["nc", "comm", "nr"]
        required_cols_per_group = [
            "gross_chg_1w",
            "net_abs_chg_1w",
            "rotation_1w",
            "rotation_share_1w",
            "net_share_1w",
            "total_chg_1w_calc",  # For QA
            "net_chg_1w_calc",  # For QA
        ]
        
        for group in groups:
            prefix = f"{group}_"
            for col_suffix in required_cols_per_group:
                col = f"{prefix}{col_suffix}"
                assert col in df.columns, f"Flows must have {col} column"
        
        # Check invariants on non-null rows
        for group in groups:
            prefix = f"{group}_"
            eps = 1e-6
            
            gross_col = f"{prefix}gross_chg_1w"
            net_abs_col = f"{prefix}net_abs_chg_1w"
            rotation_col = f"{prefix}rotation_1w"
            rotation_share_col = f"{prefix}rotation_share_1w"
            net_share_col = f"{prefix}net_share_1w"
            
            # gross_chg_1w >= 0
            non_nan_gross = df[gross_col].dropna()
            if len(non_nan_gross) > 0:
                min_gross = non_nan_gross.min()
                assert min_gross >= 0.0, f"{gross_col}: minimum value {min_gross} is < 0 (expected >= 0)"
            
            # net_abs_chg_1w >= 0
            non_nan_net_abs = df[net_abs_col].dropna()
            if len(non_nan_net_abs) > 0:
                min_net_abs = non_nan_net_abs.min()
                assert min_net_abs >= 0.0, f"{net_abs_col}: minimum value {min_net_abs} is < 0 (expected >= 0)"
            
            # rotation_1w >= 0
            non_nan_rotation = df[rotation_col].dropna()
            if len(non_nan_rotation) > 0:
                min_rotation = non_nan_rotation.min()
                assert min_rotation >= 0.0, f"{rotation_col}: minimum value {min_rotation} is < 0 (expected >= 0)"
            
            # rotation_share_1w in [0, 1]
            non_nan_rotation_share = df[rotation_share_col].dropna()
            if len(non_nan_rotation_share) > 0:
                min_share = non_nan_rotation_share.min()
                max_share = non_nan_rotation_share.max()
                assert min_share >= 0.0, f"{rotation_share_col}: minimum value {min_share} is < 0 (expected [0, 1])"
                assert max_share <= 1.0, f"{rotation_share_col}: maximum value {max_share} is > 1 (expected [0, 1])"
            
            # net_share_1w in [0, 1]
            non_nan_net_share = df[net_share_col].dropna()
            if len(non_nan_net_share) > 0:
                min_net_share = non_nan_net_share.min()
                max_net_share = non_nan_net_share.max()
                assert min_net_share >= 0.0, f"{net_share_col}: minimum value {min_net_share} is < 0 (expected [0, 1])"
                assert max_net_share <= 1.0, f"{net_share_col}: maximum value {max_net_share} is > 1 (expected [0, 1])"
            
            # gross >= net_abs
            mask_both = df[gross_col].notna() & df[net_abs_col].notna()
            if mask_both.sum() > 0:
                gross_vals = df.loc[mask_both, gross_col]
                net_abs_vals = df.loc[mask_both, net_abs_col]
                diff = (gross_vals - net_abs_vals).min()
                assert diff >= -eps, (
                    f"{group}: gross_chg_1w < net_abs_chg_1w. "
                    f"Min difference: {diff} (expected gross >= net_abs)"
                )
            
            # rotation == gross - net_abs (with tolerance)
            mask_all = df[gross_col].notna() & df[net_abs_col].notna() & df[rotation_col].notna()
            if mask_all.sum() > 0:
                gross_vals = df.loc[mask_all, gross_col]
                net_abs_vals = df.loc[mask_all, net_abs_col]
                rotation_vals = df.loc[mask_all, rotation_col]
                expected_rotation = np.maximum(gross_vals - net_abs_vals, 0.0)
                diff = (rotation_vals - expected_rotation).abs()
                max_diff = diff.max()
                assert max_diff < eps, (
                    f"{group}: rotation_1w != max(gross - net_abs, 0). "
                    f"Max difference: {max_diff} (expected < {eps})"
                )
            
            # rotation_share + net_share ≈ 1 (when gross > 0)
            mask_shares = (
                df[gross_col].notna() & 
                (df[gross_col] > eps) &
                df[rotation_share_col].notna() & 
                df[net_share_col].notna()
            )
            if mask_shares.sum() > 0:
                rotation_share_vals = df.loc[mask_shares, rotation_share_col]
                net_share_vals = df.loc[mask_shares, net_share_col]
                sum_shares = rotation_share_vals + net_share_vals
                diff = (sum_shares - 1.0).abs()
                max_diff = diff.max()
                assert max_diff < eps, (
                    f"{group}: rotation_share + net_share != 1 (when gross > 0). "
                    f"Max difference: {max_diff} (expected < {eps})"
                )
            
            # total_chg_1w_calc ≈ long_chg_1w + short_chg_1w (tolerance check)
            # Note: This requires changes_weekly.parquet, so we check if we can load it
            changes_path = Path("data/compute/changes_weekly.parquet")
            if changes_path.exists():
                changes_df = pd.read_parquet(changes_path)
                long_chg_col = f"{prefix}long_chg_1w"
                short_chg_col = f"{prefix}short_chg_1w"
                total_chg_calc_col = f"{prefix}total_chg_1w_calc"  # Use _calc from flows
                
                if all(col in changes_df.columns for col in [long_chg_col, short_chg_col]):
                    # Merge flows and changes to compare
                    merged = df.merge(
                        changes_df[[long_chg_col, short_chg_col, "market_key", "report_date"]],
                        on=["market_key", "report_date"],
                        how="inner"
                    )
                    
                    if total_chg_calc_col in merged.columns:
                        mask = (
                            merged[total_chg_calc_col].notna() &
                            merged[long_chg_col].notna() &
                            merged[short_chg_col].notna()
                        )
                        if mask.sum() > 0:
                            sum_long_short = merged.loc[mask, long_chg_col] + merged.loc[mask, short_chg_col]
                            total_chg_calc = merged.loc[mask, total_chg_calc_col]
                            diff = (sum_long_short - total_chg_calc).abs()
                            max_diff = diff.max()
                            assert max_diff < 1e-6, (
                                f"{group}: total_chg_1w_calc != long_chg_1w + short_chg_1w. "
                                f"Max difference: {max_diff} (expected < 1e-6)"
                            )


def test_metrics_weekly_has_flows_columns():
    """Test that metrics_weekly.parquet contains flows columns after join."""
    metrics_path = Path("data/compute/metrics_weekly.parquet")
    
    if metrics_path.exists():
        df = pd.read_parquet(metrics_path)
        
        # Check that flows columns are present (from flows_weekly join)
        groups = ["nc", "comm", "nr"]
        required_flows_cols = [
            "gross_chg_1w",
            "net_abs_chg_1w",
            "rotation_1w",
            "rotation_share_1w",
            "net_share_1w",
        ]
        
        for group in groups:
            prefix = f"{group}_"
            for col_suffix in required_flows_cols:
                col = f"{prefix}{col_suffix}"
                assert col in df.columns, (
                    f"metrics_weekly must have {col} column from flows_weekly join. "
                    f"Available columns ending with '_flow_1w' or '_rotation_1w': "
                    f"{[c for c in df.columns if '_flow_1w' in c or '_rotation_1w' in c][:10]}"
                )
