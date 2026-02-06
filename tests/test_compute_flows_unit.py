"""Unit tests for flows decomposition formulas."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.compute.build_flows import build_flows_weekly


def test_build_flows_weekly_decomposition_identity() -> None:
    """gross = net_abs + rotation and shares sum to 1 when gross > 0."""
    df = pd.DataFrame(
        {
            "market_key": ["EUR", "EUR", "EUR"],
            "report_date": pd.to_datetime(["2025-01-07", "2025-01-14", "2025-01-21"]),
            "nc_long_chg_1w": [np.nan, 10.0, -5.0],
            "nc_short_chg_1w": [np.nan, 4.0, -2.0],
            "nc_net_chg_1w": [np.nan, 6.0, -3.0],
            "comm_long_chg_1w": [np.nan, -7.0, 2.0],
            "comm_short_chg_1w": [np.nan, -1.0, 6.0],
            "comm_net_chg_1w": [np.nan, -6.0, -4.0],
            "nr_long_chg_1w": [np.nan, 1.0, 0.0],
            "nr_short_chg_1w": [np.nan, 3.0, -1.0],
            "nr_net_chg_1w": [np.nan, -2.0, 1.0],
        }
    )

    out = build_flows_weekly(df)

    for group in ["nc", "comm", "nr"]:
        gross = out[f"{group}_gross_chg_1w"]
        net_abs = out[f"{group}_net_abs_chg_1w"]
        rotation = out[f"{group}_rotation_1w"]

        mask = gross.notna() & net_abs.notna() & rotation.notna()
        assert np.allclose((net_abs + rotation)[mask], gross[mask], atol=1e-9)

        share_mask = (
            out[f"{group}_rotation_share_1w"].notna()
            & out[f"{group}_net_share_1w"].notna()
            & (gross > 0)
        )
        assert np.allclose(
            (
                out.loc[share_mask, f"{group}_rotation_share_1w"]
                + out.loc[share_mask, f"{group}_net_share_1w"]
            ),
            1.0,
            atol=1e-9,
        )
