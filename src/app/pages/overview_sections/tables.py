"""Tables section: historical table view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages.overview_sections.common import fmt_num, fmt_delta


def render_tables(df=None, row=None, **kwargs) -> None:
    """Render historical table view."""
    if df is None or df.empty:
        st.warning("No data for table.")
        return

    if "report_date" not in df.columns:
        st.error("Missing 'report_date' column in data.")
        return

    df = df.copy()
    df["report_date"] = pd.to_datetime(df["report_date"])
    df = df.sort_values("report_date", ascending=True).reset_index(drop=True)

    col_control1, col_control2 = st.columns([2, 1])

    with col_control1:
        num_weeks = st.slider(
            "Weeks to show",
            min_value=13,
            max_value=260,
            value=52,
            step=1,
            help="How many recent weeks to display.",
        )

    with col_control2:
        show_details = st.checkbox(
            "Show details",
            value=False,
            help="Show Long/Short instead of only Net/Total.",
        )

    df_slice = df.tail(num_weeks).copy()

    if df_slice.empty:
        st.warning("No data for the selected range.")
        return

    display_df = pd.DataFrame()
    display_df["Date"] = df_slice["report_date"].dt.strftime("%Y-%m-%d")

    if "nc_net" in df_slice.columns:
        display_df["NC Net"] = df_slice["nc_net"].apply(fmt_num)
        if "nc_net_chg_1w" in df_slice.columns:
            display_df["NC Net Delta 1w"] = df_slice["nc_net_chg_1w"].apply(fmt_delta)

    if "nc_total" in df_slice.columns:
        display_df["NC Total"] = df_slice["nc_total"].apply(fmt_num)
        if "nc_total_chg_1w" in df_slice.columns:
            display_df["NC Total Delta 1w"] = df_slice["nc_total_chg_1w"].apply(fmt_delta)

    if "comm_net" in df_slice.columns:
        display_df["Comm Net"] = df_slice["comm_net"].apply(fmt_num)
        if "comm_net_chg_1w" in df_slice.columns:
            display_df["Comm Net Delta 1w"] = df_slice["comm_net_chg_1w"].apply(fmt_delta)

    if "comm_total" in df_slice.columns:
        display_df["Comm Total"] = df_slice["comm_total"].apply(fmt_num)
        if "comm_total_chg_1w" in df_slice.columns:
            display_df["Comm Total Delta 1w"] = df_slice["comm_total_chg_1w"].apply(fmt_delta)

    if "nr_net" in df_slice.columns and df_slice["nr_net"].notna().any():
        display_df["NR Net"] = df_slice["nr_net"].apply(fmt_num)
        if "nr_net_chg_1w" in df_slice.columns and df_slice["nr_net_chg_1w"].notna().any():
            display_df["NR Net Delta 1w"] = df_slice["nr_net_chg_1w"].apply(fmt_delta)

    if "nr_total" in df_slice.columns and df_slice["nr_total"].notna().any():
        display_df["NR Total"] = df_slice["nr_total"].apply(fmt_num)
        if "nr_total_chg_1w" in df_slice.columns and df_slice["nr_total_chg_1w"].notna().any():
            display_df["NR Total Delta 1w"] = df_slice["nr_total_chg_1w"].apply(fmt_delta)

    if "open_interest" in df_slice.columns and df_slice["open_interest"].notna().any():
        display_df["Open Interest"] = df_slice["open_interest"].apply(fmt_num)
        if "open_interest_chg_1w" in df_slice.columns and df_slice["open_interest_chg_1w"].notna().any():
            display_df["OI Delta 1w"] = df_slice["open_interest_chg_1w"].apply(fmt_delta)

    if show_details:
        if "nc_long" in df_slice.columns:
            display_df["NC Long"] = df_slice["nc_long"].apply(fmt_num)
        if "nc_short" in df_slice.columns:
            display_df["NC Short"] = df_slice["nc_short"].apply(fmt_num)

        if "comm_long" in df_slice.columns:
            display_df["Comm Long"] = df_slice["comm_long"].apply(fmt_num)
        if "comm_short" in df_slice.columns:
            display_df["Comm Short"] = df_slice["comm_short"].apply(fmt_num)

        if "nr_long" in df_slice.columns and df_slice["nr_long"].notna().any():
            display_df["NR Long"] = df_slice["nr_long"].apply(fmt_num)
        if "nr_short" in df_slice.columns and df_slice["nr_short"].notna().any():
            display_df["NR Short"] = df_slice["nr_short"].apply(fmt_num)

    display_df = display_df.iloc[::-1].reset_index(drop=True)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )
