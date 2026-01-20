"""Overview MVP page: asset analytics with week navigation and tabs."""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from src.app.ui_state import (
    APP_VERSION,
    get_categories_and_markets,
    get_selected_category,
    get_selected_asset,
    initialize_selection_defaults,
    set_selected_category,
    set_selected_asset,
)
from src.common.paths import ProjectPaths
from src.app.pages.overview_sections import (
    render_snapshot,
    render_flow_rotation_section,
    render_funds_vs_commercials,
    render_funds_vs_commercials_header,
    render_extremes,
    render_extremes_header,
    render_moves,
    render_moves_header,
    render_charts,
    render_tables,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@st.cache_data
def _load_metrics(path_str: str, mtime: float) -> pd.DataFrame:
    """Load metrics_weekly.parquet with cache invalidation by mtime."""
    return pd.read_parquet(path_str)


def _render_market_traffic_light(row: dict) -> None:
    """Render Market Traffic Light block with 3 cards (all-time columns only)."""
    st.markdown(
        """
        <style>
        .tl-card {
            background-color: #f0f2f6;
            padding: 1.2rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            margin-top: 0.5rem;
            min-height: 260px;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .tl-card-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            color: #1f2937;
        }
        .tl-card-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        .tl-headline {
            font-size: 1rem;
            font-weight: 700;
            margin: 0 0 0.6rem 0;
            color: #111827;
        }
        .tl-headline span {
            font-weight: 700;
        }
        .tl-label {
            color: #6b7280;
            font-weight: 600;
            font-size: 0.85rem;
            margin-right: 6px;
        }
        .tl-value {
            color: #111827;
            font-weight: 700;
        }
        .tl-consensus-text,
        .tl-explain {
            font-size: 13px;
            line-height: 1.4;
            color: #6b7280;
            font-weight: 400;
        }
        .tl-consensus-text:first-of-type,
        .tl-explain:first-of-type {
            margin-top: 6px;
        }
        .tl-metric {
            font-size: 0.85rem;
            margin-bottom: 0.4rem;
            color: #374151;
        }
        .tl-headline .tl-sep {
            color: #9ca3af;
            font-weight: 400;
            padding: 0 6px;
        }
        .tl-signal-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #e5e7eb;
            color: #111827;
            margin-left: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    from src.app.pages.overview_sections.common import inject_shared_css
    inject_shared_css()

    st.markdown(
        """
        <div class="ps-header-container">
            <h4 class="ps-header-title">Market Traffic Light</h4>
            <span class="ps-help">?
                <span class="ps-tip">
                    <div class="ps-tip-line"><strong>Activity</strong> - weekly activity level.</div>
                    <div class="ps-tip-line"><strong>Flow</strong> - flow quality assessment.</div>
                    <div class="ps-tip-line"><strong>Positioning</strong> - current positioning state.</div>
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    def pick_str(val):
        if val is None or pd.isna(val):
            return ""
        text = str(val)
        return text.strip()

    def color_for_value(kind, value):
        if not value:
            return "#9ca3af"
        key = value.strip().lower()
        if kind == "activity":
            return {
                "quiet": "#9ca3af",
                "active": "#3b82f6",
                "aggressive": "#f97316",
            }.get(key, "#111827")
        if kind == "flow":
            return {
                "directional": "#10b981",
                "mixed": "#facc15",
                "rotational": "#9ca3af",
            }.get(key, "#111827")
        if kind == "positioning":
            return {
                "neutral": "#9ca3af",
                "crowded": "#ef4444",
                "unwound": "#3b82f6",
                "extreme": "#ef4444",
            }.get(key, "#111827")
        if kind == "consensus":
            return {
                "asymmetric": "#f97316",
                "alignment": "#10b981",
                "conflict": "#ef4444",
                "mixed": "#9ca3af",
            }.get(key, "#9ca3af")
        return "#111827"

    def headline_span(kind, value):
        import html
        text = value or "N/A"
        color = color_for_value(kind, value)
        return f'<span style="color: {color};">{html.escape(text)}</span>'

    funds_activity = pick_str(row.get("activity_funds"))
    funds_flow = pick_str(row.get("flow_funds"))
    funds_position = pick_str(row.get("positioning_funds"))

    comm_activity = pick_str(row.get("activity_commercials"))
    comm_flow = pick_str(row.get("flow_commercials"))
    comm_position = pick_str(row.get("positioning_commercials"))

    conflict_level = pick_str(row.get("conflict_level"))
    traffic_signal = row.get("cot_traffic_signal")

    consensus_text_map = {
        "high": "Funds and Commercials are in directional conflict.",
        "medium": "Partial directional conflict between Funds and Commercials.",
        "low": "No directional conflict detected.",
    }

    card_funds, card_comm, card_consensus = st.columns(3)

    with card_funds:
        import html
        funds_activity_display = funds_activity or "N/A"
        funds_flow_display = funds_flow or "N/A"
        funds_position_display = funds_position or "N/A"
        funds_tip = ""
        if funds_activity and funds_flow and funds_position:
            funds_tip = (
                f"Funds are {funds_activity} with {funds_flow}; positioning is {funds_position}."
            )
        funds_tip_display = html.escape(funds_tip) if funds_tip else ""
        funds_html = f"""
        <div class="tl-card">
            <div class="tl-card-title">Funds</div>
            <div class="tl-card-content">
                <div class="tl-headline">
                    {headline_span("activity", funds_activity)}
                    <span class="tl-sep">/</span>
                    {headline_span("flow", funds_flow)}
                    <span class="tl-sep">/</span>
                    {headline_span("positioning", funds_position)}
                </div>
                <div class="tl-metric"><span class="tl-label">Activity:</span> <span class="tl-value">{html.escape(funds_activity_display)}</span></div>
                <div class="tl-metric"><span class="tl-label">Flow:</span> <span class="tl-value">{html.escape(funds_flow_display)}</span></div>
                <div class="tl-metric"><span class="tl-label">Positioning:</span> <span class="tl-value">{html.escape(funds_position_display)}</span></div>
        """
        if funds_tip_display:
            funds_html += f'<div class="tl-explain" title="{funds_tip_display}">{funds_tip_display}</div>'
        funds_html += """
            </div>
        </div>
        """
        st.markdown(funds_html, unsafe_allow_html=True)

    with card_comm:
        comm_activity_display = comm_activity or "N/A"
        comm_flow_display = comm_flow or "N/A"
        comm_position_display = comm_position or "N/A"
        comm_tip = ""
        if comm_activity and comm_flow and comm_position:
            comm_tip = (
                f"Commercials are {comm_activity} with {comm_flow}; positioning is {comm_position}."
            )
        comm_tip_display = html.escape(comm_tip) if comm_tip else ""
        comm_html = f"""
        <div class="tl-card">
            <div class="tl-card-title">Commercials</div>
            <div class="tl-card-content">
                <div class="tl-headline">
                    {headline_span("activity", comm_activity)}
                    <span class="tl-sep">/</span>
                    {headline_span("flow", comm_flow)}
                    <span class="tl-sep">/</span>
                    {headline_span("positioning", comm_position)}
                </div>
                <div class="tl-metric"><span class="tl-label">Activity:</span> <span class="tl-value">{html.escape(comm_activity_display)}</span></div>
                <div class="tl-metric"><span class="tl-label">Flow:</span> <span class="tl-value">{html.escape(comm_flow_display)}</span></div>
                <div class="tl-metric"><span class="tl-label">Positioning:</span> <span class="tl-value">{html.escape(comm_position_display)}</span></div>
        """
        if comm_tip_display:
            comm_html += f'<div class="tl-explain" title="{comm_tip_display}">{comm_tip_display}</div>'
        comm_html += """
            </div>
        </div>
        """
        st.markdown(comm_html, unsafe_allow_html=True)

    with card_consensus:
        import html
        conflict_display = conflict_level or "N/A"
        conflict_key = conflict_level.strip().lower() if conflict_level else ""
        consensus_note = consensus_text_map.get(conflict_key, "N/A")
        consensus_note_display = html.escape(consensus_note)
        consensus_head = headline_span("consensus", conflict_display)
        signal_badge = ""
        if traffic_signal is not None and pd.notna(traffic_signal):
            signal_badge = f'<span class="tl-signal-badge">{traffic_signal}</span>'
        consensus_html = f"""
        <div class="tl-card">
            <div class="tl-card-title">Market Consensus</div>
            <div class="tl-card-content">
                <div class="tl-headline">{consensus_head}{signal_badge}</div>
                <div class="tl-consensus-text">{consensus_note_display}</div>
            </div>
        </div>
        """
        st.markdown(consensus_html, unsafe_allow_html=True)


def _render_oi_gauge_svg(pos: float | None, mode_label: str) -> str:
    """Render OI gauge SVG as HTML string."""
    if pos is None or pd.isna(pos):
        return (
            "<div style=\"color: #6b7280; font-size: 0.75rem; padding-top: 15px; "
            "padding-bottom: 15px; text-align: center;\">No data</div>"
        )

    pct = max(0, min(100, float(pos) * 100))
    if pct < 20:
        color = "#ef4444"
    elif pct < 40:
        color = "#f97316"
    elif pct < 60:
        color = "#eab308"
    elif pct < 80:
        color = "#84cc16"
    else:
        color = "#10b981"

    width = 240
    height = 140
    center_x = width / 2
    center_y = height - 10
    radius = 64
    stroke_width = 10
    circumference = 3.14159 * radius
    dash_length = circumference * (pct / 100)
    dash_gap = circumference * 2
    text_x = center_x
    text_y = center_y - 24

    svg_html = f"""
<svg width="{width}" height="{height}" style="display: block;">
  <path d="M {center_x - radius} {center_y} A {radius} {radius} 0 0 1 {center_x + radius} {center_y}"
        fill="none" stroke="#e5e7eb" stroke-width="{stroke_width}" stroke-linecap="round"/>
  <path d="M {center_x - radius} {center_y} A {radius} {radius} 0 0 1 {center_x + radius} {center_y}"
        fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round"
        stroke-dasharray="{dash_length} {dash_gap}"/>
  <text x="{text_x}" y="{text_y}" text-anchor="middle" font-size="28" font-weight="700" fill="#111827">{int(round(pct))}%</text>
</svg>
"""

    return f"<div>{svg_html}</div>"


def _render_market_open_interest(
    df_asset: pd.DataFrame,
    row: dict,
    current_week: pd.Timestamp,
    mode: str = "All-time",
) -> None:
    """Render Market Open Interest card in Snapshot style with gauge."""
    from src.app.pages.overview_sections.common import (
        fmt_num,
        fmt_delta_colored,
        fmt_oi_sparkline_tooltip,
        create_sparkline,
        get_recent_n_data,
        inject_snapshot_css,
    )

    inject_snapshot_css()

    oi = row.get("open_interest")
    oi_chg_1w = row.get("open_interest_chg_1w")
    oi_chg_1w_pct = row.get("open_interest_chg_1w_pct")
    oi_pct_5y = row.get("open_interest_pct_5y")
    oi_pct_all = row.get("open_interest_pct_all")
    oi_pos_5y = row.get("open_interest_pos_5y")
    oi_pos_all = row.get("open_interest_pos_all")
    oi_regime = row.get("oi_regime")
    oi_z_52w = row.get("oi_z_52w")
    oi_risk_level = row.get("oi_risk_level")
    oi_delta_4w = row.get("oi_delta_4w")
    oi_acceleration = row.get("oi_acceleration")
    oi_driver = row.get("oi_driver")
    accel_threshold = (
        row.get("oi_accel_small_threshold")
        if row.get("oi_accel_small_threshold") is not None
        else row.get("oi_accel_threshold")
        if row.get("oi_accel_threshold") is not None
        else row.get("oi_acceleration_threshold")
    )

    if mode == "5Y":
        oi_percentile = oi_pct_5y if pd.notna(oi_pct_5y) else oi_pos_5y if pd.notna(oi_pos_5y) else oi_pos_all
        oi_pct_label = oi_pct_5y if pd.notna(oi_pct_5y) else oi_pos_5y
    else:
        oi_percentile = oi_pct_all if pd.notna(oi_pct_all) else oi_pos_all
        oi_pct_label = oi_pct_all if pd.notna(oi_pct_all) else oi_pos_all

    oi_26w_data = get_recent_n_data(df_asset, current_week, "open_interest", 26)
    spark_svg = create_sparkline(oi_26w_data, width=270, height=63, stroke_width=2, dot_radius=3)

    def fmt_delta_pct_colored(pct_val):
        if pd.isna(pct_val):
            return '<span style="color: #6b7280;">N/A</span>'
        if pct_val == 0:
            return '<span style="color: #6b7280;">0.00%</span>'
        if pct_val > 0:
            color = "#10b981"
            sign = "+"
        else:
            color = "#ef4444"
            sign = ""
        value = f"{pct_val * 100:.2f}%"
        return f'<span style="color: {color}; font-weight: 600;">{sign}{value}</span>'

    gauge_html = _render_oi_gauge_svg(oi_percentile, mode)

    def fmt_pct_label(val):
        if pd.isna(val):
            return "N/A"
        return f"{int(round(val * 100))}%"

    percentile_label = fmt_pct_label(oi_pct_label) if pd.notna(oi_pct_label) else "N/A"
    percentile_mode_label = "Percentile (5Y)" if mode == "5Y" else "Percentile (All-time)"

    regime_map = {
        "Expansion_Early": "Expansion (Early)",
        "Expansion_Late": "Expansion (Late)",
        "Distribution": "Distribution",
        "Rebuild": "Rebuild",
        "Neutral": "Neutral",
        "Mixed": "Mixed",
        "N/A": "N/A",
    }
    regime_text = regime_map.get(str(oi_regime), "N/A") if oi_regime is not None else "N/A"

    if pd.isna(oi_z_52w):
        zscore_text = "N/A"
    else:
        zscore_text = f"{float(oi_z_52w):.2f}"

    risk_text = str(oi_risk_level) if oi_risk_level is not None else "N/A"
    risk_key = risk_text.strip().lower()
    risk_class = "oi-risk-badge"
    if risk_key == "low":
        risk_class = "oi-risk-badge oi-risk-low"
    elif risk_key == "elevated":
        risk_class = "oi-risk-badge oi-risk-elevated"
    elif risk_key == "high":
        risk_class = "oi-risk-badge oi-risk-high"

    if pd.isna(oi_acceleration):
        accel_text = "N/A"
    else:
        threshold = float(accel_threshold) if accel_threshold is not None and pd.notna(accel_threshold) else 0.0
        if abs(float(oi_acceleration)) <= threshold:
            accel_text = "Flat"
        elif float(oi_acceleration) > 0:
            accel_text = "Positive"
        else:
            accel_text = "Negative"

    driver_map = {
        "Funds": "Recent OI changes are primarily associated with speculative Funds flows.",
        "Commercials": "Recent OI changes are primarily associated with Commercial hedging flows.",
        "Mixed": "Recent OI changes are driven by a mix of Funds and Commercials.",
        "None": "Net COT flows are negligible this week.",
        "N/A": "N/A",
    }
    driver_text = driver_map.get(str(oi_driver), "N/A") if oi_driver is not None else "N/A"

    def fmt_delta_or_na(val):
        return fmt_delta_colored(val) if val is not None and pd.notna(val) else '<span style="color: #6b7280;">N/A</span>'

    sparkline_tip = fmt_oi_sparkline_tooltip(oi, oi_chg_1w)
    sparkline_tip_escaped = sparkline_tip.replace('"', "&quot;")
    sparkline_html = (
        f"<div title=\"{sparkline_tip_escaped}\">{spark_svg}</div>"
        if spark_svg
        else "<div style=\"color: #6b7280; font-size: 0.75rem; text-align: center;\">No data</div>"
    )

    card_html = f"""
<div class="position-card">
  <div style="display: flex; align-items: center; gap: 48px;">
    <div style="flex: 0 0 240px;">
      <div class="position-card-title">Open Interest</div>
      <div class="oi-meta" title="Total number of outstanding contracts.">Open Interest (contracts)</div>
      <div class="position-net">{fmt_num(oi)}</div>
      <div class="oi-meta" title="Week-over-week change in open interest (absolute).">Delta 1w: <strong>{fmt_delta_colored(oi_chg_1w)}</strong></div>
      <div class="oi-meta" title="Week-over-week change in open interest (percent).">Delta 1w %: <strong>{fmt_delta_pct_colored(oi_chg_1w_pct)}</strong></div>
      <div class="oi-meta" title="Interpretive regime based on delta, acceleration, and z-score.">Regime: <strong>{regime_text}</strong></div>
      <div class="oi-meta" title="Distance from 52-week mean, in standard deviations.">Z-score (52w): <strong>{zscore_text}</strong></div>
      <div class="oi-meta" title="Stress indicator based on OI extremity and COT conflict.">Risk: <span class="{risk_class}">{risk_text}</span></div>
    </div>
    <div style="flex: 0 0 180px; display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-start; margin-top: -20px;">
      {gauge_html}
      <div class="oi-percentile-label" title="Position of current OI within historical distribution.">{percentile_mode_label}: {percentile_label}</div>
    </div>
    <div style="flex: 1;"></div>
    <div style="flex: 0 0 280px; margin-top: -20px;">
      <div class="oi-meta" title="OI trend over the last 26 weeks.">OI trend (26w)</div>
      {sparkline_html}
    </div>
  </div>
  <div class="oi-panels">
    <div class="oi-panel">
      <div class="oi-panel-title" title="Acceleration = Delta 1w - (Delta 4w / 4). Positive means accelerating growth.">Momentum</div>
      <div class="oi-panel-row">Delta 1w: <span class="oi-panel-value">{fmt_delta_or_na(oi_chg_1w)}</span></div>
      <div class="oi-panel-row" title="Acceleration = Delta 1w - (Delta 4w / 4). Positive means accelerating growth.">Delta 4w: <span class="oi-panel-value">{fmt_delta_or_na(oi_delta_4w)}</span></div>
      <div class="oi-panel-row" title="Acceleration = Delta 1w - (Delta 4w / 4). Positive means accelerating growth.">Acceleration: <span class="oi-panel-value">{fmt_delta_or_na(oi_acceleration)} ({accel_text})</span></div>
    </div>
    <div class="oi-panel">
      <div class="oi-panel-title">Driver</div>
      <div class="oi-panel-row">{driver_text}</div>
    </div>
  </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


def render() -> None:
    """Render the Overview MVP page."""
    initialize_selection_defaults()
    categories, category_to_markets = get_categories_and_markets()

    if not categories:
        st.error("No markets.yaml configuration.")
        return

    selected_category = get_selected_category()
    selected_asset = get_selected_asset()

    with st.sidebar:
        st.markdown("### Navigation")
        current_page = st.session_state.get("page", "overview")

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

        st.markdown("---")
        st.markdown("### Filters")

        category_index = categories.index(selected_category) if selected_category in categories else 0
        selected_category_ui = st.selectbox(
            "Category",
            options=categories,
            index=category_index,
            key="overview_category_select",
        )
        if selected_category_ui != selected_category:
            set_selected_category(selected_category_ui)
            selected_category = selected_category_ui

        markets_in_category = category_to_markets.get(selected_category, [])
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]

        if market_options:
            asset_index = market_options.index(selected_asset) if selected_asset in market_options else 0
            selected_asset_ui = st.selectbox(
                "Asset",
                options=market_options,
                index=asset_index,
                key="overview_asset_select",
            )
            if selected_asset_ui != selected_asset:
                set_selected_asset(selected_asset_ui)
                selected_asset = selected_asset_ui
        else:
            st.warning("No assets in this category.")
            selected_asset = None

        if selected_asset:
            paths = ProjectPaths(REPO_ROOT)
            metrics_path = paths.data / "compute" / "metrics_weekly.parquet"
            if metrics_path.exists():
                mtime = metrics_path.stat().st_mtime
                df_sidebar = _load_metrics(str(metrics_path), mtime)
                if not df_sidebar.empty:
                    df_sidebar = df_sidebar.copy()
                    df_sidebar["report_date"] = pd.to_datetime(df_sidebar["report_date"])
                    df_sidebar_asset = (
                        df_sidebar[df_sidebar["market_key"] == selected_asset]
                        .sort_values("report_date")
                        .reset_index(drop=True)
                    )
                    weeks_sidebar = sorted(pd.to_datetime(df_sidebar_asset["report_date"].dropna()).unique())
                    if weeks_sidebar:
                        if st.session_state.get("overview_last_asset") != selected_asset:
                            st.session_state["overview_week_index"] = len(weeks_sidebar) - 1
                            st.session_state["overview_last_asset"] = selected_asset
                        if "overview_week_index" not in st.session_state:
                            st.session_state["overview_week_index"] = len(weeks_sidebar) - 1
                        if st.session_state["overview_week_index"] >= len(weeks_sidebar):
                            st.session_state["overview_week_index"] = len(weeks_sidebar) - 1

                        st.markdown("---")
                        st.markdown("### Week")
                        nav_left, nav_center, nav_right = st.columns([1, 1, 1])
                        with nav_left:
                            if st.button(
                                "Prev",
                                key="sidebar_week_prev",
                                use_container_width=False,
                                disabled=st.session_state["overview_week_index"] <= 0,
                            ):
                                st.session_state["overview_week_index"] = max(
                                    st.session_state["overview_week_index"] - 1, 0
                                )
                                st.rerun()
                        with nav_center:
                            week_label = pd.to_datetime(
                                weeks_sidebar[st.session_state["overview_week_index"]]
                            ).strftime("%Y-%m-%d")
                            st.markdown(
                                f"""
                                <div style="text-align: center; margin-bottom: 6px;">
                                  <div>{week_label}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with nav_right:
                            if st.button(
                                "Next",
                                key="sidebar_week_next",
                                use_container_width=False,
                                disabled=st.session_state["overview_week_index"] >= len(weeks_sidebar) - 1,
                            ):
                                st.session_state["overview_week_index"] = min(
                                    st.session_state["overview_week_index"] + 1, len(weeks_sidebar) - 1
                                )
                                st.rerun()

        st.markdown("---")
        with st.expander("Data update (admin)", expanded=False):
            st.caption("Local update. Runs full pipeline: ingest -> normalize -> compute.")
            if st.button("Run compute", key="run_compute_button", use_container_width=True):
                env = os.environ.copy()
                existing = env.get("PYTHONPATH", "")
                env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing if existing else "")

                steps = [
                    ("ingest", ["-m", "src.ingest.run_ingest", "--root", str(REPO_ROOT), "--log-level", "INFO"]),
                    ("normalize", ["-m", "src.normalize.run_normalize", "--root", str(REPO_ROOT), "--log-level", "INFO"]),
                    ("compute", ["-m", "src.compute.run_compute", "--root", str(REPO_ROOT), "--log-level", "INFO"]),
                ]

                with st.spinner("Running full pipeline..."):
                    for step_name, args in steps:
                        cmd = [sys.executable, *args]
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            cwd=str(REPO_ROOT),
                            env=env,
                        )
                        if result.returncode != 0:
                            st.error(f"{step_name} failed.")
                            if result.stdout:
                                st.code(result.stdout)
                            if result.stderr:
                                st.code(result.stderr)
                            return
                        if result.stdout:
                            st.code(result.stdout)

                st.success("Pipeline finished successfully.")
                # Force reload of metrics and reset week index after compute.
                st.cache_data.clear()
                st.session_state.pop("overview_last_asset", None)
                st.session_state.pop("overview_week_index", None)
                st.rerun()

        st.markdown("---")
        st.caption(f"Version: {APP_VERSION}")

    if not selected_asset:
        st.warning("Select an asset.")
        return

    paths = ProjectPaths(REPO_ROOT)
    metrics_path = paths.data / "compute" / "metrics_weekly.parquet"
    if not metrics_path.exists():
        st.error("metrics_weekly.parquet not found.")
        return

    mtime_ns = metrics_path.stat().st_mtime_ns
    df = _load_metrics(str(metrics_path), mtime_ns)

    if df.empty:
        st.warning("metrics_weekly.parquet is empty.")
        return

    df = df.copy()
    df["report_date"] = pd.to_datetime(df["report_date"])
    df_asset = df[df["market_key"] == selected_asset].sort_values("report_date").reset_index(drop=True)

    if df_asset.empty:
        st.warning("No data for selected asset.")
        return

    weeks = sorted(pd.to_datetime(df_asset["report_date"].dropna()).unique())
    if not weeks:
        st.warning("No dates in data.")
        return

    if st.session_state.get("overview_last_asset") != selected_asset:
        st.session_state["overview_week_index"] = len(weeks) - 1
        st.session_state["overview_last_asset"] = selected_asset

    if "overview_week_index" not in st.session_state:
        st.session_state["overview_week_index"] = len(weeks) - 1
    if st.session_state["overview_week_index"] >= len(weeks):
        st.session_state["overview_week_index"] = len(weeks) - 1

    week_index = st.session_state["overview_week_index"]

    header_col1, header_col2 = st.columns([2, 3])
    with header_col1:
        st.markdown(f"## {selected_asset}")
    with header_col2:
        st.markdown(
            """
            <style>
            div[data-testid="stButton"][data-testid*="week_"] > button {
                padding: 0.2rem 0.6rem !important;
                min-height: 1.6rem !important;
                font-size: 0.85rem !important;
                min-width: 72px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        nav_col1, nav_col2, nav_col3 = st.columns([3.5, 1, 0.5])
        with nav_col1:
            prev_spacer, prev_btn_col = st.columns([12, 2])
            with prev_spacer:
                st.markdown("")
            with prev_btn_col:
                if st.button("Prev", key="week_prev", use_container_width=False, disabled=week_index <= 0):
                    st.session_state["overview_week_index"] = max(week_index - 1, 0)
                    st.rerun()
        with nav_col2:
            week_label = pd.to_datetime(weeks[week_index]).strftime("%Y-%m-%d")
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 6px;">
                  <div>{week_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with nav_col3:
            if st.button(
                "Next",
                key="week_next",
                use_container_width=False,
                disabled=week_index >= len(weeks) - 1,
            ):
                st.session_state["overview_week_index"] = min(week_index + 1, len(weeks) - 1)
                st.rerun()

    current_week = pd.to_datetime(weeks[week_index])
    df_week = df_asset[df_asset["report_date"] == current_week]
    if df_week.empty:
        st.warning("No data for selected week.")
        return
    row = df_week.iloc[0].to_dict()

    _render_market_traffic_light(row)

    tab_positions, tab_oi, tab_charts, tab_table = st.tabs(
        ["Positions", "Open Interest", "Charts", "Table"]
    )

    with tab_positions:
        render_snapshot(df_asset, row, current_week)
        render_flow_rotation_section(df_asset, row)

        render_funds_vs_commercials_header()
        fc_mode = st.radio(
            "Scale",
            options=["all", "5y"],
            format_func=lambda x: "All-time" if x == "all" else "5Y",
            horizontal=True,
            key="fc_mode",
        )
        render_funds_vs_commercials(df_asset, row, current_week, fc_mode)

        render_moves_header()
        moves_mode = st.radio(
            "Mode",
            options=["all", "5y"],
            format_func=lambda x: "All-time" if x == "all" else "5Y",
            horizontal=True,
            key="moves_mode",
        )
        render_moves(df_asset, row, current_week, moves_mode)

        render_extremes_header()
        extremes_mode = st.radio(
            "Mode",
            options=["All-time", "5Y"],
            format_func=lambda x: "All-time" if x == "All-time" else "5Y",
            horizontal=True,
            key="extremes_mode",
        )
        render_extremes(row, extremes_mode)

    with tab_oi:
        st.markdown("### Open Interest")
        st.caption("Open Interest, delta 1w, and percentile vs history.")
        oi_mode = st.radio(
            "Mode",
            options=["All-time", "5Y"],
            format_func=lambda x: "All-time" if x == "All-time" else "5Y",
            horizontal=True,
            key="oi_mode",
        )
        _render_market_open_interest(df_asset, row, current_week, mode=oi_mode)

    with tab_charts:
        render_charts(df_asset, row=row)

    with tab_table:
        render_tables(df_asset, row=row)
