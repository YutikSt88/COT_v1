"""Build latest market positioning table dataset."""

from __future__ import annotations

import pandas as pd
import numpy as np


def build_market_positioning_latest(
    metrics: pd.DataFrame,
    market_name_map: dict[str, str],
) -> pd.DataFrame:
    """
    Build latest market positioning dataset (one row per market_key).

    Uses existing metrics columns only (no new analytics).
    """
    if metrics.empty:
        return pd.DataFrame()

    df = metrics.copy()
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.tz_localize(None)

    latest_dates = df.groupby("market_key")["report_date"].transform("max")
    latest = df[df["report_date"] == latest_dates].copy()

    latest["market_id"] = latest["market_key"].astype(str)
    latest["market_name"] = latest["market_key"].map(market_name_map).fillna(latest["market_key"])

    def _sign_with_eps(val: float) -> int:
        if np.isnan(val):
            return 0
        if abs(val) < 1e-6:
            return 0
        return 1 if val > 0 else -1

    def _fmt_z(val: float | None) -> str:
        if val is None or np.isnan(val):
            return "N/A"
        return f"Z={val:+.1f}"

    open_interest = pd.to_numeric(latest.get("open_interest"), errors="coerce")
    open_interest_chg_1w = pd.to_numeric(latest.get("open_interest_chg_1w"), errors="coerce")
    open_interest_prev = open_interest - open_interest_chg_1w
    prev_ok = open_interest_prev.notna() & (open_interest_prev != 0)

    # Funds (nc)
    funds_net = pd.to_numeric(latest.get("nc_net"), errors="coerce")
    funds_net_chg = pd.to_numeric(latest.get("nc_net_chg_1w"), errors="coerce")
    latest["funds_net"] = funds_net
    latest["funds_net_chg_1w"] = funds_net_chg
    latest["funds_pct_oi_chg_1w"] = np.where(prev_ok, funds_net_chg / open_interest_prev, np.nan)
    latest["funds_z_52w"] = pd.to_numeric(latest.get("net_z_52w_funds"), errors="coerce")

    # Commercials
    comm_net = pd.to_numeric(latest.get("comm_net"), errors="coerce")
    comm_net_chg = pd.to_numeric(latest.get("comm_net_chg_1w"), errors="coerce")
    latest["comm_net"] = comm_net
    latest["comm_net_chg_1w"] = comm_net_chg
    latest["comm_pct_oi_chg_1w"] = np.where(prev_ok, comm_net_chg / open_interest_prev, np.nan)
    latest["comm_z_52w"] = pd.to_numeric(latest.get("net_z_52w_commercials"), errors="coerce")

    # Small (nr)
    small_net = pd.to_numeric(latest.get("nr_net"), errors="coerce")
    small_net_chg = pd.to_numeric(latest.get("nr_net_chg_1w"), errors="coerce")
    latest["small_net"] = small_net
    latest["small_net_chg_1w"] = small_net_chg
    latest["small_pct_oi_chg_1w"] = np.where(prev_ok, small_net_chg / open_interest_prev, np.nan)

    # why_tags (optional, max 3)
    def _build_tags(row: pd.Series) -> str:
        tags: list[str] = []

        if row.get("conflict_level") == "High":
            tags.append("High conflict")

        z_funds = pd.to_numeric(row.get("net_z_52w_funds"), errors="coerce")
        z_comm = pd.to_numeric(row.get("net_z_52w_commercials"), errors="coerce")
        if pd.notna(z_funds) and pd.notna(z_comm):
            if _sign_with_eps(float(z_funds)) != 0 and _sign_with_eps(float(z_comm)) == -_sign_with_eps(float(z_funds)):
                tags.append("Commercials opposite")

        if pd.notna(z_funds) and abs(z_funds) >= 1.5:
            tags.append(f"Funds crowded ({_fmt_z(float(z_funds))})")

        oi_regime = row.get("oi_regime")
        if oi_regime == "Expansion_Early":
            tags.append("OI: Expansion (Early)")
        elif oi_regime == "Expansion_Late":
            tags.append("OI: Expansion (Late)")

        oi_risk = row.get("oi_risk_level")
        if oi_risk == "High":
            tags.append("OI Risk: High")
        elif oi_risk == "Elevated":
            tags.append("OI Risk: Elevated")

        return " | ".join(tags[:3])

    latest["why_tags"] = latest.apply(_build_tags, axis=1)

    out_cols = [
        "market_id",
        "market_name",
        "category",
        "report_date",
        "cot_traffic_signal",
        "conflict_level",
        "oi_regime",
        "oi_risk_level",
        "open_interest",
        "open_interest_chg_1w",
        "open_interest_chg_1w_pct",
        "funds_net",
        "funds_net_chg_1w",
        "funds_pct_oi_chg_1w",
        "funds_z_52w",
        "comm_net",
        "comm_net_chg_1w",
        "comm_pct_oi_chg_1w",
        "comm_z_52w",
        "small_net",
        "small_net_chg_1w",
        "small_pct_oi_chg_1w",
        "why_tags",
    ]

    for col in out_cols:
        if col not in latest.columns:
            latest[col] = np.nan

    return latest[out_cols].reset_index(drop=True)
