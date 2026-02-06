"""Dashboard page (Streamlit terminal UI)."""

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


def _signal_color(sig: str) -> str:
    if sig == "bullish":
        return "#22c55e"
    if sig == "bearish":
        return "#ef4444"
    if sig == "extreme":
        return "#f59e0b"
    return "#38bdf8"


def render() -> None:
    apply_terminal_theme()
    render_nav("market")

    radar_path, metrics_path = get_compute_paths()
    df, source = load_radar_with_fallback(radar_path, metrics_path)
    if df.empty:
        st.warning("No dashboard data available. Run compute pipeline to generate data files.")
        return
    if source == "metrics_fallback":
        st.info("Using fallback data from metrics_weekly.parquet (market_radar_latest.parquet is missing).")

    df = df.copy()
    df["signal_state"] = df.apply(signal_state_from_row, axis=1)

    categories = sorted(df["category"].dropna().astype(str).unique().tolist()) if "category" in df.columns else []

    st.markdown("## Dashboard")
    report_date = "N/A"
    if "report_date" in df.columns and not df["report_date"].isna().all():
        report_date = pd.to_datetime(df["report_date"].max()).strftime("%Y-%m-%d")
    st.caption(f"Report date: {report_date}")

    c1, c2 = st.columns(2)
    with c1:
        signal_filter = st.selectbox("Signal", ["all", "extreme", "bullish", "bearish", "neutral"], index=0)
    with c2:
        category_filter = st.selectbox("Category", ["all", *categories], index=0)

    df_view = df
    if signal_filter != "all":
        df_view = df_view[df_view["signal_state"] == signal_filter]
    if category_filter != "all":
        df_view = df_view[df_view["category"].astype(str).str.lower() == category_filter.lower()]

    s1, s2, s3, s4 = st.columns(4)
    for col, label, key in [
        (s1, "Bullish", "bullish"),
        (s2, "Bearish", "bearish"),
        (s3, "Extreme", "extreme"),
        (s4, "Neutral", "neutral"),
    ]:
        val = int((df_view["signal_state"] == key).sum())
        with col:
            st.markdown(
                f"""
                <div class='cot-panel'>
                  <div class='cot-kpi-label'>{label}</div>
                  <div class='cot-kpi-value' style='color:{_signal_color(key)}'>{val}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    out = df_view.copy()
    out["signal"] = out["signal_state"].astype(str)
    out["score"] = pd.to_numeric(out.get("hot_score"), errors="coerce")
    out["z_score"] = pd.to_numeric(out.get("net_z_52w_funds"), errors="coerce")
    out["delta_1w_pct"] = pd.to_numeric(out.get("open_interest_chg_1w_pct"), errors="coerce") * 100.0

    cols = [
        "market_id",
        "category",
        "signal",
        "score",
        "conflict_level",
        "z_score",
        "delta_1w_pct",
    ]
    cols = [c for c in cols if c in out.columns]

    if out.empty:
        st.info("No rows for current filters.")
        return

    out = out.sort_values(["score", "z_score"], ascending=False, na_position="last")
    out = out[cols].rename(
        columns={
            "market_id": "Market",
            "category": "Category",
            "signal": "Signal",
            "score": "Score",
            "conflict_level": "Conflict",
            "z_score": "Z-score",
            "delta_1w_pct": "Delta 1W %",
        }
    )

    st.markdown("### Market Scan")
    st.dataframe(out, use_container_width=True, hide_index=True)
