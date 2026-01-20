"""Smoke test for normalize module."""

from __future__ import annotations
from pathlib import Path
import pytest
import pandas as pd


def test_normalize_imports():
    """Test that normalize modules can be imported."""
    from src.normalize.run_normalize import main
    from src.normalize.cot_parser import parse_deacot_zip
    from src.normalize.qa_checks import qa_uniqueness, qa_missing_dates, qa_open_interest
    
    assert main is not None
    assert parse_deacot_zip is not None
    assert qa_uniqueness is not None
    assert qa_missing_dates is not None


def test_canonical_exists_if_present():
    """Test that canonical_full.parquet exists and is not empty (if present)."""
    canonical_path = Path("data/canonical/cot_weekly_canonical_full.parquet")
    
    if canonical_path.exists():
        df = pd.read_parquet(canonical_path)
        assert len(df) > 0, "Canonical parquet should have rows"
        assert "market_key" in df.columns
        assert "report_date" in df.columns
        assert "contract_code" in df.columns
