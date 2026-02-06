"""Signals page (Streamlit terminal UI)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages._terminal_ui import (
    apply_terminal_theme,
    get_compute_paths,
    load_radar_with_fallback,
    render_nav,
    signal_state_from_row,
)


def render() -> None:
    apply_terminal_theme()
    render_nav("signals")

    radar_path, metrics_path = get_compute_paths()
    df, source = load_radar_with_fallback(radar_path, metrics_path)
    if df.empty:
        st.warning("No signals data available. Run compute pipeline to generate data files.")
        return
    if source == "metrics_fallback":
        st.info("Using fallback data from metrics_weekly.parquet (market_radar_latest.parquet is missing).")

    df = df.copy()
    df["signal_state"] = df.apply(signal_state_from_row, axis=1)

    report_date = "N/A"
    if "report_date" in df.columns and not df["report_date"].isna().all():
        report_date = pd.to_datetime(df["report_date"].max()).strftime("%Y-%m-%d")

    st.markdown("## Signals")
    st.caption(f"Report date: {report_date}")

    categories = sorted(df["category"].dropna().astype(str).unique().tolist()) if "category" in df.columns else []

    f1, f2, f3 = st.columns(3)
    with f1:
        signal_filter = st.selectbox("Signal", ["all", "extreme", "bullish", "bearish", "neutral"], index=0)
    with f2:
        category_filter = st.selectbox("Category", ["all", *categories], index=0)
    with f3:
        conflict_filter = st.selectbox("Conflict", ["all", "High", "Medium", "Low"], index=0)

    out = df
    if signal_filter != "all":
        out = out[out["signal_state"] == signal_filter]
    if category_filter != "all":
        out = out[out["category"].astype(str).str.lower() == category_filter.lower()]
    if conflict_filter != "all" and "conflict_level" in out.columns:
        out = out[out["conflict_level"] == conflict_filter]

    out = out.copy()
    out["score"] = pd.to_numeric(out.get("hot_score"), errors="coerce")
    out["z_score"] = pd.to_numeric(out.get("net_z_52w_funds"), errors="coerce")
    out["delta_1w_pct"] = pd.to_numeric(out.get("open_interest_chg_1w_pct"), errors="coerce") * 100.0

    cols = [
        "market_id",
        "category",
        "signal_state",
        "score",
        "conflict_level",
        "z_score",
        "delta_1w_pct",
    ]
    cols = [c for c in cols if c in out.columns]

    if not out.empty:
        out = out.sort_values(["score", "z_score"], ascending=False, na_position="last")

    out = out[cols].rename(
        columns={
            "market_id": "Market",
            "category": "Category",
            "signal_state": "Signal",
            "score": "Score",
            "conflict_level": "Conflict",
            "z_score": "Z-score",
            "delta_1w_pct": "Delta 1W %",
        }
    )

    st.markdown("### Active Signals")
    st.dataframe(out, use_container_width=True, hide_index=True)
