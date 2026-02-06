"""Market Detail page (Streamlit terminal UI)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages._terminal_ui import (
    apply_terminal_theme,
    get_compute_paths,
    load_metrics,
    load_radar_latest,
    render_nav,
    signal_state_from_row,
)


RANGE_OPTIONS = ["4W", "12W", "YTD", "1Y", "ALL"]


def _fmt_num(val: float | int | None) -> str:
    if val is None or pd.isna(val):
        return "N/A"
    return f"{float(val):,.0f}"


def _filter_by_range(df: pd.DataFrame, range_code: str) -> pd.DataFrame:
    if df.empty or "report_date" not in df.columns:
        return df
    out = df[df["report_date"].notna()].copy()
    if out.empty:
        return out
    latest = out["report_date"].max()
    if range_code == "ALL":
        return out
    if range_code == "4W":
        return out[out["report_date"] >= latest - pd.Timedelta(days=28)]
    if range_code == "12W":
        return out[out["report_date"] >= latest - pd.Timedelta(days=84)]
    if range_code == "1Y":
        return out[out["report_date"] >= latest - pd.Timedelta(days=365)]
    if range_code == "YTD":
        return out[out["report_date"] >= pd.Timestamp(year=latest.year, month=1, day=1)]
    return out


def render() -> None:
    apply_terminal_theme()
    render_nav("overview")

    radar_path, metrics_path = get_compute_paths()
    if not metrics_path.exists():
        st.error("metrics_weekly.parquet not found")
        return

    metrics = load_metrics(str(metrics_path), metrics_path.stat().st_mtime)
    if metrics.empty:
        st.warning("No market detail data available.")
        return

    radar = pd.DataFrame()
    if radar_path.exists():
        radar = load_radar_latest(str(radar_path), radar_path.stat().st_mtime)
        if not radar.empty:
            radar = radar.copy()
            radar["signal_state"] = radar.apply(signal_state_from_row, axis=1)

    market_col = "market_key" if "market_key" in metrics.columns else "market_id"
    markets = sorted(metrics[market_col].dropna().astype(str).unique().tolist())
    if not markets:
        st.warning("No market keys available in metrics_weekly.parquet")
        return

    current = st.session_state.get("selected_asset")
    if current not in markets:
        current = markets[0]
    range_default = st.session_state.get("md_range", "12W")
    if range_default not in RANGE_OPTIONS:
        range_default = "12W"

    st.markdown("## Market Detail")

    c1, c2 = st.columns([2, 1])
    with c1:
        selected_market = st.selectbox("Market", markets, index=markets.index(current))
    with c2:
        selected_range = st.selectbox("Range", RANGE_OPTIONS, index=RANGE_OPTIONS.index(range_default))

    st.session_state["selected_asset"] = selected_market
    st.session_state["md_range"] = selected_range

    asset_df = metrics[metrics[market_col].astype(str) == str(selected_market)].copy().sort_values("report_date")
    if asset_df.empty:
        st.info("No rows for selected market")
        return

    series_df = _filter_by_range(asset_df, selected_range)
    if series_df.empty:
        series_df = asset_df.tail(1).copy()

    latest = asset_df.iloc[-1]
    sig = "neutral"
    if not radar.empty and "market_id" in radar.columns:
        rr = radar[radar["market_id"].astype(str) == str(selected_market)]
        if not rr.empty and "signal_state" in rr.columns:
            sig = str(rr.iloc[0]["signal_state"])

    color = "#38bdf8"
    if sig == "bullish":
        color = "#22c55e"
    elif sig == "bearish":
        color = "#ef4444"
    elif sig == "extreme":
        color = "#f59e0b"

    r1, r2, r3, r4, r5 = st.columns(5)
    cards = [
        (r1, "Signal", sig.upper(), color),
        (r2, "Funds Net", _fmt_num(latest.get("nc_net")), "#e5edf8"),
        (r3, "Commercials Net", _fmt_num(latest.get("comm_net")), "#e5edf8"),
        (r4, "Z-score (Funds)", f"{float(latest.get('net_z_52w_funds')):.2f}" if pd.notna(latest.get("net_z_52w_funds")) else "N/A", "#f59e0b"),
        (r5, "Updated", pd.to_datetime(latest.get("report_date")).strftime("%Y-%m-%d") if pd.notna(latest.get("report_date")) else "N/A", "#e5edf8"),
    ]
    for col, label, value, c in cards:
        with col:
            st.markdown(
                f"""
                <div class='cot-panel'>
                  <div class='cot-kpi-label'>{label}</div>
                  <div style='font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color:{c}; font-size:24px; font-weight:700;'>{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    chart_df = series_df[[c for c in ["report_date", "nc_net", "comm_net", "open_interest"] if c in series_df.columns]].copy()
    if "report_date" in chart_df.columns:
        chart_df = chart_df.set_index("report_date")

    st.markdown("### Price + COT")
    st.line_chart(chart_df, use_container_width=True, height=320)

    z_df = series_df[[c for c in ["report_date", "net_z_52w_funds", "net_z_52w_commercials"] if c in series_df.columns]].copy()
    if "report_date" in z_df.columns:
        z_df = z_df.set_index("report_date")

    st.markdown("### Z-score / Extremes")
    st.line_chart(z_df, use_container_width=True, height=240)

    table_cols = [
        "report_date",
        "nc_net",
        "comm_net",
        "net_z_52w_funds",
        "net_z_52w_commercials",
        "open_interest",
        "open_interest_chg_1w_pct",
    ]
    table_cols = [c for c in table_cols if c in asset_df.columns]
    out = asset_df[table_cols].sort_values("report_date", ascending=False).head(30).copy()
    if "open_interest_chg_1w_pct" in out.columns:
        out["open_interest_chg_1w_pct"] = pd.to_numeric(out["open_interest_chg_1w_pct"], errors="coerce") * 100.0
    if "report_date" in out.columns:
        out["report_date"] = pd.to_datetime(out["report_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    out = out.rename(
        columns={
            "report_date": "Date",
            "nc_net": "Funds Net",
            "comm_net": "Com Net",
            "net_z_52w_funds": "Funds Z",
            "net_z_52w_commercials": "Com Z",
            "open_interest": "Open Interest",
            "open_interest_chg_1w_pct": "OI Delta 1W %",
        }
    )

    st.markdown("### Recent Weekly Data")
    st.dataframe(out, use_container_width=True, hide_index=True)
