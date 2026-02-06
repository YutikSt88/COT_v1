"""Signals page: active signal scan table with filters."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.app.ui_state import APP_VERSION, set_selected_asset, set_selected_category
from src.common.paths import ProjectPaths

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@st.cache_data
def _load_radar(path_str: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path_str)


def _signal_state(row: pd.Series) -> str:
    sig = pd.to_numeric(row.get("cot_traffic_signal"), errors="coerce")
    funds_z = pd.to_numeric(row.get("net_z_52w_funds"), errors="coerce")
    oi_risk = str(row.get("oi_risk_level") or "")
    if (pd.notna(funds_z) and abs(float(funds_z)) >= 2.0) or oi_risk == "High":
        return "extreme"
    if pd.notna(sig) and sig >= 1:
        return "bullish"
    if pd.notna(sig) and sig <= -1:
        return "bearish"
    return "neutral"


def render() -> None:
    paths = ProjectPaths(REPO_ROOT)
    radar_path = paths.data / "compute" / "market_radar_latest.parquet"
    if not radar_path.exists():
        st.error("market_radar_latest.parquet not found.")
        return

    df = _load_radar(str(radar_path), radar_path.stat().st_mtime)
    if df.empty:
        st.warning("market_radar_latest.parquet is empty.")
        return

    df = df.copy()
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        latest_date = df["report_date"].max()
        df = df[df["report_date"] == latest_date].copy()
    else:
        latest_date = None

    df["signal_state"] = df.apply(_signal_state, axis=1)
    df["signal_abs"] = pd.to_numeric(df.get("cot_traffic_signal"), errors="coerce").abs()

    with st.sidebar:
        st.markdown("### Navigation")
        current_page = st.session_state.get("page", "signals")

        if st.button(
            "Market",
            type="primary" if current_page == "market" else "secondary",
            use_container_width=True,
        ):
            if current_page != "market":
                st.session_state["page"] = "market"
                st.rerun()

        if st.button(
            "Overview",
            type="primary" if current_page == "overview" else "secondary",
            use_container_width=True,
        ):
            if current_page != "overview":
                st.session_state["page"] = "overview"
                st.rerun()

        if st.button(
            "Signals",
            type="primary" if current_page == "signals" else "secondary",
            use_container_width=True,
        ):
            if current_page != "signals":
                st.session_state["page"] = "signals"
                st.rerun()

        st.markdown("---")
        st.markdown("### Filters")
        categories = sorted(df["category"].dropna().astype(str).unique().tolist()) if "category" in df.columns else []
        selected_categories = st.multiselect("Category", options=categories, default=categories)
        selected_signal = st.selectbox("Signal", options=["all", "extreme", "bullish", "bearish", "neutral"], index=0)
        selected_conflict = st.selectbox("Conflict", options=["all", "High", "Medium", "Low"], index=0)

    df_out = df.copy()
    if selected_categories:
        df_out = df_out[df_out["category"].isin(selected_categories)]
    if selected_signal != "all":
        df_out = df_out[df_out["signal_state"] == selected_signal]
    if selected_conflict != "all":
        df_out = df_out[df_out["conflict_level"] == selected_conflict]

    df_out = df_out.sort_values(["signal_abs", "hot_score"], ascending=False, na_position="last")

    date_label = pd.to_datetime(latest_date).strftime("%Y-%m-%d") if pd.notna(latest_date) else "N/A"
    st.markdown("## Signals")
    st.caption(f"Report date: {date_label}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("All", len(df))
    c2.metric("Filtered", len(df_out))
    c3.metric("Extreme", int((df_out["signal_state"] == "extreme").sum()) if not df_out.empty else 0)
    c4.metric("Hot", int((df_out.get("is_hot") == True).sum()) if not df_out.empty else 0)

    if df_out.empty:
        st.warning("No signals for current filters.")
        return

    st.markdown("### Active Signals Table")
    view_cols = [
        "market_name",
        "category",
        "signal_state",
        "cot_traffic_signal",
        "hot_score",
        "conflict_level",
        "oi_risk_level",
        "net_z_52w_funds",
        "open_interest_chg_1w_pct",
    ]
    present_cols = [c for c in view_cols if c in df_out.columns]
    st.dataframe(df_out[present_cols], use_container_width=True, hide_index=True)

    st.markdown("### Open Market Detail")
    markets = df_out[["market_id", "market_name", "category"]].dropna(subset=["market_id"]).copy()
    market_options = markets["market_name"].astype(str).tolist()
    market_map = dict(zip(markets["market_name"].astype(str), markets["market_id"].astype(str)))
    category_map = dict(zip(markets["market_name"].astype(str), markets["category"].astype(str)))

    selected_market_name = st.selectbox("Market", options=market_options, index=0)
    if st.button("Open in Overview", use_container_width=False):
        mk = market_map.get(selected_market_name)
        cat = category_map.get(selected_market_name)
        if cat:
            set_selected_category(cat)
        if mk:
            set_selected_asset(mk)
        st.session_state["page"] = "overview"
        st.rerun()

    st.markdown("---")
    st.caption(f"Version: {APP_VERSION}")
