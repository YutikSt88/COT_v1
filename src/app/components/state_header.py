"""State header component: displays asset state with heatline indicators."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.components.heatline import heatline


def render_state_header(df_latest: pd.DataFrame) -> None:
    """
    Render "Asset State" header block.

    Args:
        df_latest: Single-row DataFrame with latest metrics data for selected market
    """
    if df_latest.empty:
        st.warning("No data for asset state.")
        return

    row = df_latest.iloc[0]

    st.markdown("<h3 style='text-align: center;'>Asset State</h3>", unsafe_allow_html=True)
    st.markdown("---")

    col_nc, col_comm = st.columns(2)

    with col_nc:
        st.markdown("<h4 style='margin-bottom: 0.3em;'>Non-Commercials (Large Speculators)</h4>", unsafe_allow_html=True)
        st.markdown("**All-time**")

        heatline(
            label="Long",
            min_val=row["nc_long_min_all"],
            max_val=row["nc_long_max_all"],
            current_val=row["nc_long"],
            pos=row["nc_long_pos_all"],
            compact=True,
        )

        heatline(
            label="Short",
            min_val=row["nc_short_min_all"],
            max_val=row["nc_short_max_all"],
            current_val=row["nc_short"],
            pos=row["nc_short_pos_all"],
            compact=True,
        )

        heatline(
            label="Total",
            min_val=row["nc_total_min_all"],
            max_val=row["nc_total_max_all"],
            current_val=row["nc_total"],
            pos=row["nc_total_pos_all"],
            compact=True,
        )

        st.markdown("")
        st.markdown("**Last 5 Years**")

        nc_long_pos_5y = row["nc_long_pos_5y"]
        nc_short_pos_5y = row["nc_short_pos_5y"]
        nc_total_pos_5y = row["nc_total_pos_5y"]

        heatline(
            label="Long",
            min_val=row["nc_long_min_5y"],
            max_val=row["nc_long_max_5y"],
            current_val=row["nc_long"],
            pos=nc_long_pos_5y if pd.notna(nc_long_pos_5y) else None,
            disabled=pd.isna(nc_long_pos_5y),
        )

        heatline(
            label="Short",
            min_val=row["nc_short_min_5y"],
            max_val=row["nc_short_max_5y"],
            current_val=row["nc_short"],
            pos=nc_short_pos_5y if pd.notna(nc_short_pos_5y) else None,
            disabled=pd.isna(nc_short_pos_5y),
        )

        heatline(
            label="Total",
            min_val=row["nc_total_min_5y"],
            max_val=row["nc_total_max_5y"],
            current_val=row["nc_total"],
            pos=nc_total_pos_5y if pd.notna(nc_total_pos_5y) else None,
            disabled=pd.isna(nc_total_pos_5y),
        )

    with col_comm:
        st.markdown("<h4 style='margin-bottom: 0.3em;'>Commercials (Hedgers)</h4>", unsafe_allow_html=True)
        st.markdown("**All-time**")

        heatline(
            label="Long",
            min_val=row["comm_long_min_all"],
            max_val=row["comm_long_max_all"],
            current_val=row["comm_long"],
            pos=row["comm_long_pos_all"],
            compact=True,
        )

        heatline(
            label="Short",
            min_val=row["comm_short_min_all"],
            max_val=row["comm_short_max_all"],
            current_val=row["comm_short"],
            pos=row["comm_short_pos_all"],
            compact=True,
        )

        heatline(
            label="Total",
            min_val=row["comm_total_min_all"],
            max_val=row["comm_total_max_all"],
            current_val=row["comm_total"],
            pos=row["comm_total_pos_all"],
            compact=True,
        )

        st.markdown("")
        st.markdown("**Last 5 Years**")

        comm_long_pos_5y = row["comm_long_pos_5y"]
        comm_short_pos_5y = row["comm_short_pos_5y"]
        comm_total_pos_5y = row["comm_total_pos_5y"]

        heatline(
            label="Long",
            min_val=row["comm_long_min_5y"],
            max_val=row["comm_long_max_5y"],
            current_val=row["comm_long"],
            pos=comm_long_pos_5y if pd.notna(comm_long_pos_5y) else None,
            disabled=pd.isna(comm_long_pos_5y),
        )

        heatline(
            label="Short",
            min_val=row["comm_short_min_5y"],
            max_val=row["comm_short_max_5y"],
            current_val=row["comm_short"],
            pos=comm_short_pos_5y if pd.notna(comm_short_pos_5y) else None,
            disabled=pd.isna(comm_short_pos_5y),
        )

        heatline(
            label="Total",
            min_val=row["comm_total_min_5y"],
            max_val=row["comm_total_max_5y"],
            current_val=row["comm_total"],
            pos=comm_total_pos_5y if pd.notna(comm_total_pos_5y) else None,
            disabled=pd.isna(comm_total_pos_5y),
        )

    st.markdown("---")
