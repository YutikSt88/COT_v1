"""Extremes section: render positioning extremes cards."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages.overview_sections.common import (
    inject_extremes_css,
    inject_shared_css,
    render_heatline_html,
)


def get_extreme_values(row: dict, extremes_mode: str, group_prefix: str, metric: str) -> tuple:
    """
    Read min, max, pos values from compute columns (no calculation).
    Returns (min, max, pos, current).
    """
    if extremes_mode == "All-time":
        min_suffix = "_min_all"
        max_suffix = "_max_all"
        pos_suffix = "_pos_all"
    else:
        min_suffix = "_min_5y"
        max_suffix = "_max_5y"
        pos_suffix = "_pos_5y"

    min_col = f"{group_prefix}{metric}{min_suffix}"
    max_col = f"{group_prefix}{metric}{max_suffix}"
    pos_col = f"{group_prefix}{metric}{pos_suffix}"
    current_col = f"{group_prefix}{metric}"

    min_val = row.get(min_col)
    max_val = row.get(max_col)
    pos_val = row.get(pos_col)
    current_val = row.get(current_col)

    return min_val, max_val, pos_val, current_val


def render_extremes_header() -> None:
    """Render Positioning Extremes header with info tooltip (toggle is rendered by parent)."""
    inject_shared_css()
    st.markdown(
        """
        <div class="pe-header-container">
            <h4 class="pe-header-title">Positioning Extremes</h4>
            <span class="pe-help">?
                <span class="pe-tip">
                    <div class="pe-tip-line"><strong>Extremes</strong> show where the current level sits vs history.</div>
                    <div class="pe-tip-line"><strong>Long / Short / Total / Net</strong> are precomputed in compute.</div>
                    <div class="pe-tip-line"><strong>Modes:</strong></div>
                    <div class="pe-tip-line">All-time is the full history.</div>
                    <div class="pe-tip-line">5Y is the last five years.</div>
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_extremes(row: dict, extremes_mode: str) -> None:
    """Render Positioning Extremes section (cards only, no header/toggle)."""
    inject_extremes_css()

    card_ext_funds, card_ext_comm, card_ext_nr = st.columns(3)

    with card_ext_funds:
        min_val, max_val, pos_val, current_val = get_extreme_values(row, extremes_mode, "nc_", "long")
        min_val_short, max_val_short, pos_val_short, current_val_short = get_extreme_values(row, extremes_mode, "nc_", "short")
        min_val_total, max_val_total, pos_val_total, current_val_total = get_extreme_values(row, extremes_mode, "nc_", "total")
        min_val_net, max_val_net, pos_val_net, current_val_net = get_extreme_values(row, extremes_mode, "nc_", "net")

        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Funds</div>
                <div class="position-extremes-rows">
                    <div class="extremes-row">
                        <span class="extremes-label">Long:</span>
                        {render_heatline_html(min_val, max_val, current_val, pos_val, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Short:</span>
                        {render_heatline_html(min_val_short, max_val_short, current_val_short, pos_val_short, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Total:</span>
                        {render_heatline_html(min_val_total, max_val_total, current_val_total, pos_val_total, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Net:</span>
                        {render_heatline_html(min_val_net, max_val_net, current_val_net, pos_val_net, is_delta=False)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_ext_comm:
        min_val, max_val, pos_val, current_val = get_extreme_values(row, extremes_mode, "comm_", "long")
        min_val_short, max_val_short, pos_val_short, current_val_short = get_extreme_values(row, extremes_mode, "comm_", "short")
        min_val_total, max_val_total, pos_val_total, current_val_total = get_extreme_values(row, extremes_mode, "comm_", "total")
        min_val_net, max_val_net, pos_val_net, current_val_net = get_extreme_values(row, extremes_mode, "comm_", "net")

        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Commercials</div>
                <div class="position-extremes-rows">
                    <div class="extremes-row">
                        <span class="extremes-label">Long:</span>
                        {render_heatline_html(min_val, max_val, current_val, pos_val, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Short:</span>
                        {render_heatline_html(min_val_short, max_val_short, current_val_short, pos_val_short, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Total:</span>
                        {render_heatline_html(min_val_total, max_val_total, current_val_total, pos_val_total, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Net:</span>
                        {render_heatline_html(min_val_net, max_val_net, current_val_net, pos_val_net, is_delta=False)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_ext_nr:
        min_val, max_val, pos_val, current_val = get_extreme_values(row, extremes_mode, "nr_", "long")
        min_val_short, max_val_short, pos_val_short, current_val_short = get_extreme_values(row, extremes_mode, "nr_", "short")
        min_val_total, max_val_total, pos_val_total, current_val_total = get_extreme_values(row, extremes_mode, "nr_", "total")
        min_val_net, max_val_net, pos_val_net, current_val_net = get_extreme_values(row, extremes_mode, "nr_", "net")

        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Non-Reported</div>
                <div class="position-extremes-rows">
                    <div class="extremes-row">
                        <span class="extremes-label">Long:</span>
                        {render_heatline_html(min_val, max_val, current_val, pos_val, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Short:</span>
                        {render_heatline_html(min_val_short, max_val_short, current_val_short, pos_val_short, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Total:</span>
                        {render_heatline_html(min_val_total, max_val_total, current_val_total, pos_val_total, is_delta=False)}
                    </div>
                    <div class="extremes-row">
                        <span class="extremes-label">Net:</span>
                        {render_heatline_html(min_val_net, max_val_net, current_val_net, pos_val_net, is_delta=False)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
