"""Moves section: render positioning moves cards with delta heatlines."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages.overview_sections.common import (
    inject_shared_css,
    inject_extremes_css,
    render_heatline_html,
)


def render_moves_header() -> None:
    """Render Positioning Moves header with info tooltip (toggle is rendered by parent)."""
    inject_shared_css()
    st.markdown(
        """
        <div class="pe-header-container">
            <h4 class="pe-header-title">Weekly Position Changes (Delta)</h4>
            <span class="pe-help">?
                <span class="pe-tip">
                    <div class="pe-tip-line"><strong>Moves</strong> shows how large the current delta is versus history.</div>
                    <div class="pe-tip-line"><strong>Long / Short / Total / Net (Delta 1w)</strong> are precomputed in compute.</div>
                    <div class="pe-tip-line"><strong>Modes:</strong></div>
                    <div class="pe-tip-line">All-time is the full history.</div>
                    <div class="pe-tip-line">5Y is the last five years.</div>
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_moves(df_asset: pd.DataFrame, row: dict, current_week: pd.Timestamp, moves_mode: str) -> None:
    """
    Render Positioning Moves section (cards only, no header/toggle).

    Args:
        df_asset: DataFrame filtered by market_key (unused, kept for signature consistency)
        row: Current week row as dict (from df_week.iloc[0])
        current_week: Current week timestamp (unused, kept for signature consistency)
        moves_mode: "all" or "5y" (from st.radio toggle, managed by parent)
    """
    inject_extremes_css()

    group_prefix = {
        "Funds": "nc_",
        "Commercials": "comm_",
        "Non-Reported": "nr_",
    }

    move_metrics = [
        ("Long 1w", "long"),
        ("Short 1w", "short"),
        ("Total 1w", "total"),
        ("Net 1w", "net"),
    ]

    def get_move_values(prefix: str, metric: str) -> tuple:
        base = f"{prefix}{metric}_chg_1w"
        if moves_mode == "5y":
            min_col = f"{base}_min_5y"
            max_col = f"{base}_max_5y"
            pos_col = f"{base}_pos_5y"
        else:
            min_col = f"{base}_min_all"
            max_col = f"{base}_max_all"
            pos_col = f"{base}_pos_all"
        return (
            row.get(min_col),
            row.get(max_col),
            row.get(base),
            row.get(pos_col),
        )

    card_moves_funds, card_moves_comm, card_moves_nr = st.columns(3)

    with card_moves_funds:
        prefix = group_prefix["Funds"]
        heatlines_html = []
        for label, metric in move_metrics:
            min_val, max_val, cur_val, pos_val = get_move_values(prefix, metric)
            heatline_html = render_heatline_html(
                min_val,
                max_val,
                cur_val,
                pos_val,
                is_delta=True,
            )
            heatlines_html.append(
                f'<div class="extremes-row"><span class="extremes-label">{label}:</span>{heatline_html}</div>'
            )
        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Funds</div>
                <div class="position-extremes-rows">
                    {''.join(heatlines_html)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_moves_comm:
        prefix = group_prefix["Commercials"]
        heatlines_html = []
        for label, metric in move_metrics:
            min_val, max_val, cur_val, pos_val = get_move_values(prefix, metric)
            heatline_html = render_heatline_html(
                min_val,
                max_val,
                cur_val,
                pos_val,
                is_delta=True,
            )
            heatlines_html.append(
                f'<div class="extremes-row"><span class="extremes-label">{label}:</span>{heatline_html}</div>'
            )
        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Commercials</div>
                <div class="position-extremes-rows">
                    {''.join(heatlines_html)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_moves_nr:
        prefix = group_prefix["Non-Reported"]
        heatlines_html = []
        for label, metric in move_metrics:
            min_val, max_val, cur_val, pos_val = get_move_values(prefix, metric)
            heatline_html = render_heatline_html(
                min_val,
                max_val,
                cur_val,
                pos_val,
                is_delta=True,
            )
            heatlines_html.append(
                f'<div class="extremes-row"><span class="extremes-label">{label}:</span>{heatline_html}</div>'
            )
        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-card-title">Non-Reported</div>
                <div class="position-extremes-rows">
                    {''.join(heatlines_html)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
