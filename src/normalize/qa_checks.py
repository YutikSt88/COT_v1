"""QA checks for normalized canonical data."""

from __future__ import annotations
import pandas as pd


def qa_uniqueness(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Check uniqueness of (market_key, report_date) pairs.
    
    Returns:
        List of error messages (empty if OK)
    """
    errors: list[str] = []
    warnings: list[str] = []
    dupes = df[df.duplicated(subset=["market_key", "report_date"], keep=False)]
    if not dupes.empty:
        errors.append(f"Uniqueness FAILED: {len(dupes)} duplicate (market_key, report_date) pairs")
    return errors, warnings


def qa_missing_dates(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Check null ratio for numeric columns.
    
    Args:
        df: DataFrame to check
        max_null_ratio: Maximum allowed null ratio (default 0.001 = 0.1%)
        
    Returns:
        List of error messages (empty if OK)
    """
    errors: list[str] = []
    warnings: list[str] = []
    if "report_date" in df.columns:
        missing = df["report_date"].isna().sum()
        if missing > 0:
            errors.append(f"Report date FAILED: {missing} rows with missing report_date")
    return errors, warnings


def qa_open_interest(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Check that open_interest_all is non-negative.
    
    Returns:
        List of error messages (empty if OK)
    """
    errors: list[str] = []
    warnings: list[str] = []
    if "open_interest_all" in df.columns:
        negative = df[df["open_interest_all"] < 0]
        if not negative.empty:
            warnings.append(f"Open Interest WARN: {len(negative)} rows with negative open_interest_all")
    return errors, warnings


def qa_comm_nc_mapping(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Check that comm_* and nc_* columns are not identical (mapping bug detection).
    
    Returns:
        List of error messages (empty if OK)
    """
    errors: list[str] = []
    warnings: list[str] = []
    required_cols = ["comm_long", "comm_short", "nc_long", "nc_short"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return errors, warnings  # Skip check if columns don't exist
    
    # Check if comm_* and nc_* are identical
    same_long = (df["nc_long"] == df["comm_long"]).fillna(False)
    same_short = (df["nc_short"] == df["comm_short"]).fillna(False)
    same_all = same_long & same_short
    same_pct = same_all.mean()
    
    if same_pct > 0.999:
        errors.append(
            f"Mapping FAILED: comm_* equals nc_* for {same_pct*100:.1f}% of rows. "
            f"Expected comm_* (Commercials) and nc_* (Non-Commercials) to represent different player groups. "
            f"This indicates a mapping bug in normalize step."
        )
    return errors, warnings
