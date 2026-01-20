"""Build latest market radar view for UI."""

from __future__ import annotations

import pandas as pd
import numpy as np


def build_market_radar_latest(
    metrics: pd.DataFrame,
    market_name_map: dict[str, str],
) -> pd.DataFrame:
    """
    Build latest market radar dataset (one row per market_key).

    Required input columns (from metrics):
    - market_key, report_date, category
    - cot_traffic_signal, conflict_level
    - oi_regime, oi_z_52w, oi_risk_level
    - net_z_52w_funds
    """
    if metrics.empty:
        return pd.DataFrame()

    df = metrics.copy()
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.tz_localize(None)

    # Latest row per market_key
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

    # is_hot
    cot_signal = pd.to_numeric(latest.get("cot_traffic_signal"), errors="coerce")
    oi_z = pd.to_numeric(latest.get("oi_z_52w"), errors="coerce")
    net_z = pd.to_numeric(latest.get("net_z_52w_funds"), errors="coerce")
    conflict = latest.get("conflict_level").astype(str)
    oi_risk = latest.get("oi_risk_level").astype(str)

    hot_conditions = (
        (cot_signal.abs() >= 1)
        | (conflict == "High")
        | (oi_risk.isin(["Elevated", "High"]))
        | (oi_z.abs() >= 1.5)
        | (net_z.abs() >= 1.5)
    )
    latest["is_hot"] = hot_conditions.fillna(False).astype(bool)

    # hot_score
    hot_score = 2 * cot_signal.abs().fillna(0)
    hot_score += 2 * (conflict == "High").astype(float)
    hot_score += 1 * (oi_risk == "High").astype(float)
    hot_score += 0.5 * (oi_risk == "Elevated").astype(float)
    hot_score += 1 * (oi_z.abs() >= 1.5).astype(float)
    hot_score += 1 * (net_z.abs() >= 1.5).astype(float)
    latest["hot_score"] = hot_score.astype("float64")

    # Crowding/opposition flags
    net_z_comm = pd.to_numeric(latest.get("net_z_52w_commercials"), errors="coerce")
    latest["funds_crowded"] = (net_z.abs() >= 1.5).fillna(False).astype(bool)
    funds_sign = net_z.apply(_sign_with_eps)
    comm_sign = net_z_comm.apply(_sign_with_eps)
    latest["commercial_opposition"] = (
        (funds_sign != 0) & (comm_sign == -funds_sign)
    ).fillna(False).astype(bool)
    latest["confirmed_imbalance"] = (
        latest["funds_crowded"] & latest["commercial_opposition"]
    ).fillna(False).astype(bool)

    # why_tags
    def _fmt_z(val: float | None) -> str:
        if val is None or np.isnan(val):
            return ""
        return f"Z={val:+.1f}"

    def _build_tags(row: pd.Series) -> str:
        tags: list[str] = []

        # Conflict
        if row.get("conflict_level") == "High":
            tags.append("High Conflict")

        # Funds crowding
        z_funds = pd.to_numeric(row.get("net_z_52w_funds"), errors="coerce")
        if pd.notna(z_funds):
            if abs(z_funds) >= 2.0:
                tags.append(f"Funds Extreme ({_fmt_z(float(z_funds))})")
            elif abs(z_funds) >= 1.5:
                tags.append(f"Funds Crowded ({_fmt_z(float(z_funds))})")

        # OI regime
        oi_regime = row.get("oi_regime")
        regime_map = {
            "Expansion_Late": "OI: Expansion (Late)",
            "Expansion_Early": "OI: Expansion (Early)",
            "Distribution": "OI: Distribution",
            "Rebuild": "OI: Rebuild",
        }
        if oi_regime in regime_map:
            tags.append(regime_map[oi_regime])

        # OI risk
        oi_risk_level = row.get("oi_risk_level")
        if oi_risk_level == "High":
            tags.append("OI Risk: High")
        elif oi_risk_level == "Elevated":
            tags.append("OI Risk: Elevated")

        # OI extreme (z)
        z_oi = pd.to_numeric(row.get("oi_z_52w"), errors="coerce")
        if pd.notna(z_oi):
            if abs(z_oi) >= 2.0:
                tags.append(f"OI Extreme ({_fmt_z(float(z_oi))})")
            elif abs(z_oi) >= 1.5:
                tags.append(f"OI Stretched ({_fmt_z(float(z_oi))})")

        # Take first 2-4 by priority
        tags = tags[:4]
        return " | ".join(tags)

    latest["why_tags"] = latest.apply(_build_tags, axis=1)

    # Output selection
    out_cols = [
        "market_id",
        "market_name",
        "category",
        "report_date",
        "cot_traffic_signal",
        "conflict_level",
        "oi_regime",
        "oi_z_52w",
        "oi_risk_level",
        "net_z_52w_funds",
        "funds_net",
        "funds_net_delta_1w",
        "funds_pct_oi_change",
        "funds_net_z_52w",
        "comm_net",
        "comm_net_delta_1w",
        "comm_pct_oi_change",
        "comm_net_z_52w",
        "small_net",
        "small_net_delta_1w",
        "small_pct_oi_change",
        "small_net_z_52w",
        "open_interest",
        "open_interest_chg_1w",
        "open_interest_chg_1w_pct",
        "funds_crowded",
        "commercial_opposition",
        "confirmed_imbalance",
        "is_hot",
        "hot_score",
        "why_tags",
    ]
    for col in out_cols:
        if col not in latest.columns:
            latest[col] = np.nan

    latest["funds_net"] = latest.get("nc_net")
    latest["funds_net_delta_1w"] = latest.get("nc_net_chg_1w")
    latest["funds_pct_oi_change"] = latest.get("nc_flow_pct_oi_1w")
    latest["funds_net_z_52w"] = latest.get("net_z_52w_funds")

    latest["comm_net"] = latest.get("comm_net")
    latest["comm_net_delta_1w"] = latest.get("comm_net_chg_1w")
    latest["comm_pct_oi_change"] = latest.get("comm_flow_pct_oi_1w")
    latest["comm_net_z_52w"] = latest.get("net_z_52w_commercials")

    latest["small_net"] = latest.get("nr_net")
    latest["small_net_delta_1w"] = latest.get("nr_net_chg_1w")
    latest["small_pct_oi_change"] = latest.get("nr_flow_pct_oi_1w")
    latest["small_net_z_52w"] = np.nan

    return latest[out_cols].reset_index(drop=True)

