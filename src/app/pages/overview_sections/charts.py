"""Charts section: time-series charts with group/metric/range toggles."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages.overview_sections.common import (
    fmt_num,
    fmt_delta_colored,
    inject_charts_css,
)


def render_charts(df: pd.DataFrame | None = None, row: dict | None = None, **kwargs) -> None:
    """Render Charts section with time-series chart."""
    if df is None or df.empty:
        st.warning("No data for charts.")
        return

    if row is None:
        st.warning("No data for the selected week.")
        return

    inject_charts_css()

    df_chart = df.sort_values("report_date").reset_index(drop=True).copy()
    df_chart["report_date"] = pd.to_datetime(df_chart["report_date"])

    col_group, col_metric, col_range = st.columns(3)

    with col_group:
        group = st.radio(
            "Group",
            options=["Funds", "Commercials", "Non-Reported"],
            key="charts_group",
            horizontal=True,
        )

    with col_metric:
        metric = st.radio(
            "Metric",
            options=["Net", "Total", "Long", "Short"],
            key="charts_metric",
            horizontal=True,
        )

    with col_range:
        range_option = st.radio(
            "Range",
            options=["1Y", "5Y", "All"],
            key="charts_range",
            horizontal=True,
        )

    group_map = {
        "Funds": "nc",
        "Commercials": "comm",
        "Non-Reported": "nr",
    }
    prefix = group_map.get(group, "nc")

    metric_map = {
        "Net": "net",
        "Total": "total",
        "Long": "long",
        "Short": "short",
    }
    metric_suffix = metric_map.get(metric, "net")

    main_col = f"{prefix}_{metric_suffix}"
    ma_col = f"{prefix}_{metric_suffix}_ma_13w"
    pos_5y_col = f"{prefix}_{metric_suffix}_pos_5y"
    chg_1w_col = f"{prefix}_{metric_suffix}_chg_1w"
    move_pct_col = f"{prefix}_{metric_suffix}_move_pct_all"

    if main_col not in df_chart.columns:
        st.error(f"Missing column '{main_col}' in data.")
        return

    current_date = pd.to_datetime(row.get("report_date"))
    if pd.notna(current_date):
        df_chart = df_chart[df_chart["report_date"] <= current_date].copy()

    if range_option == "1Y" and pd.notna(current_date):
        start_date = current_date - pd.DateOffset(years=1)
        df_chart = df_chart[df_chart["report_date"] >= start_date].copy()
    elif range_option == "5Y" and pd.notna(current_date):
        start_date = current_date - pd.DateOffset(years=5)
        df_chart = df_chart[df_chart["report_date"] >= start_date].copy()

    chart_data = df_chart[["report_date", main_col]].copy()
    chart_data.columns = ["report_date", metric]

    if ma_col in df_chart.columns:
        chart_data[f"{metric} (13W avg)"] = df_chart[ma_col].values

    chart_data_indexed = chart_data.set_index("report_date")
    st.line_chart(chart_data_indexed, use_container_width=True)

    markers = []
    pos_5y_val = row.get(pos_5y_col)
    if pd.notna(pos_5y_val):
        if pos_5y_val >= 0.9:
            markers.append("Position in top 10% (5Y)")
        elif pos_5y_val <= 0.1:
            markers.append("Position in bottom 10% (5Y)")

    move_pct_val = row.get(move_pct_col)
    if pd.notna(move_pct_val) and move_pct_val >= 0.95:
        markers.append("Extreme weekly change")

    if markers:
        st.markdown(f"**Signals (current week):** {' | '.join(markers)}")

    st.markdown("---")
    st.markdown("**Summary (current week):**")

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

    with summary_col1:
        current_val = row.get(main_col)
        st.metric(
            label="Current value",
            value=fmt_num(current_val) if pd.notna(current_val) else "N/A",
        )

    with summary_col2:
        wow_delta = row.get(chg_1w_col)
        if pd.notna(wow_delta):
            st.markdown(f"**Delta 1w:** {fmt_delta_colored(wow_delta)}", unsafe_allow_html=True)
        else:
            st.markdown("**Delta 1w:** N/A")

    with summary_col3:
        move_pct = row.get(move_pct_col)
        if pd.notna(move_pct):
            pct_rounded = round(move_pct * 100)
            st.metric(
                label="Change percentile",
                value=f"{pct_rounded}%",
            )
        else:
            st.metric(
                label="Change percentile",
                value="N/A",
            )

    with summary_col4:
        pos_5y = row.get(pos_5y_col)
        if pd.notna(pos_5y):
            pos_pct = round(pos_5y * 100)
            st.metric(
                label="Position (5Y)",
                value=f"{pos_pct}%",
            )
        else:
            st.metric(
                label="Position (5Y)",
                value="N/A",
            )
