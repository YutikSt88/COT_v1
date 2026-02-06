"""Unit tests for extremes calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.compute.build_extremes import build_extremes


def test_build_extremes_pos_all_is_half_when_min_equals_max() -> None:
    """If all-time min == max and value is present, pos_all should be 0.5."""
    positions = pd.DataFrame(
        {
            "market_key": ["EUR", "EUR", "EUR"],
            "report_date": pd.to_datetime(["2025-01-07", "2025-01-14", "2025-01-21"]),
            "nc_long": [100.0, 100.0, 100.0],
        }
    )

    out = build_extremes(positions)
    assert np.allclose(out["nc_long_pos_all"], 0.5, atol=1e-9)


def test_build_extremes_pos_5y_uses_min_periods_52() -> None:
    """5Y pos must be NaN before 52 observations; with flat data then 0.5."""
    weeks = pd.date_range("2020-01-07", periods=60, freq="W-TUE")
    positions = pd.DataFrame(
        {
            "market_key": ["EUR"] * len(weeks),
            "report_date": weeks,
            "nc_long": [200.0] * len(weeks),
        }
    )

    out = build_extremes(positions)
    pos_5y = out["nc_long_pos_5y"]

    assert pos_5y.iloc[:51].isna().all()
    assert np.allclose(pos_5y.iloc[51:], 0.5, atol=1e-9)
