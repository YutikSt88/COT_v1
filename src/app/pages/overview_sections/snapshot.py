"""Snapshot section: render position cards for Funds, Commercials, Non-Reported."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.app.pages.overview_sections.common import (
    fmt_num,
    fmt_delta,
    fmt_delta_colored,
    fmt_move_strength,
    render_dual_heatline_html,
    render_flow_rotation_bar_html,
    create_sparkline,
    get_13w_net_data,
    inject_snapshot_css,
    inject_shared_css,
    inject_extremes_css,
)


def render_flow_rotation_section(df_asset: pd.DataFrame, row: dict) -> None:
    """Render Flow vs Rotation section showing composition of weekly net changes."""
    inject_shared_css()
    inject_extremes_css()

    st.markdown(
        """
        <div class="pe-header-container">
            <h4 class="pe-header-title">Weekly Position Structure (Flow vs Rotation)</h4>
            <span class="pe-help">?
                <span class="pe-tip">
                    <div class="pe-tip-line"><strong>Flow vs Rotation</strong></div>
                    <div class="pe-tip-line">Net Delta 1w is the total weekly change.</div>
                    <div class="pe-tip-line">Rotation is the share where long/short shift in opposite directions.</div>
                    <div class="pe-tip-line">All calculations are done in compute.</div>
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    groups = [
        ("Funds", "nc_"),
        ("Commercials", "comm_"),
        ("Non-Reported", "nr_"),
    ]

    all_missing_new = True
    has_old_schema = False
    for _, prefix in groups:
        gross = row.get(f"{prefix}gross_chg_1w")
        net_share = row.get(f"{prefix}net_share_1w")
        if (gross is not None and pd.notna(gross)) or (net_share is not None and pd.notna(net_share)):
            all_missing_new = False
        if (row.get(f"{prefix}inflow_1w") is not None and pd.notna(row.get(f"{prefix}inflow_1w"))) or \
           (row.get(f"{prefix}outflow_1w") is not None and pd.notna(row.get(f"{prefix}outflow_1w"))):
            has_old_schema = True

    if all_missing_new:
        if has_old_schema:
            st.caption("Flow/Rotation is in the old schema. Recompute in compute.")
        else:
            st.caption("Flow/Rotation data is missing in metrics_weekly.parquet.")

    for group_name, prefix in groups:
        net_chg = row.get(f"{prefix}net_chg_1w")
        gross_chg = row.get(f"{prefix}gross_chg_1w")
        rotation = row.get(f"{prefix}rotation_1w")
        rotation_share = row.get(f"{prefix}rotation_share_1w")
        net_share = row.get(f"{prefix}net_share_1w")
        long_chg = row.get(f"{prefix}long_chg_1w")
        short_chg = row.get(f"{prefix}short_chg_1w")

        has_data = (
            (gross_chg is not None and pd.notna(gross_chg) and gross_chg > 0) or
            (net_chg is not None and pd.notna(net_chg))
        )

        if not has_data:
            row_html = f'''
            <div class="flow-rotation-row">
                <span class="flow-rotation-label">{group_name}:</span>
                <div style="flex: 1; min-width: 0;">
                    <span style="color: #6b7280;">N/A</span>
                </div>
            </div>
            '''
        else:
            bar_html = render_flow_rotation_bar_html(
                net_chg=net_chg,
                gross_chg=gross_chg,
                rotation_share=rotation_share,
                net_share=net_share,
                rotation=rotation,
                long_chg=long_chg,
                short_chg=short_chg,
            )

            text_parts = []
            if net_chg is not None and pd.notna(net_chg):
                text_parts.append(f"Net Delta 1w: {fmt_delta(net_chg)}")
            if gross_chg is not None and pd.notna(gross_chg) and gross_chg > 0:
                text_parts.append(f"Gross: {fmt_num(gross_chg)}")
            if rotation is not None and pd.notna(rotation) and rotation > 0:
                rotation_pct_str = f" ({rotation_share*100:.0f}%)" if rotation_share is not None and pd.notna(rotation_share) else ""
                text_parts.append(f"Rotation: {fmt_num(rotation)}{rotation_pct_str}")

            text_html = f'<div class="flow-rotation-text">{" | ".join(text_parts)}</div>' if text_parts else ""

            row_html = f'''
            <div class="flow-rotation-row">
                <span class="flow-rotation-label">{group_name}:</span>
                <div style="flex: 1; min-width: 0;">
                    {bar_html}
                    {text_html}
                </div>
            </div>
            '''

        st.markdown(row_html, unsafe_allow_html=True)


def render_funds_vs_commercials_header() -> None:
    """Render Funds vs Commercials header with info tooltip (toggle is rendered by parent)."""
    inject_shared_css()
    st.markdown(
        """
        <div class="pe-header-container">
            <h4 class="pe-header-title">Funds vs Commercials - Net Balance</h4>
            <span class="pe-help">?
                <span class="pe-tip">
                    <div class="pe-tip-line"><strong>Funds vs Commercials</strong></div>
                    <div class="pe-tip-line">Shared scale for two series to compare funds and commercials.</div>
                    <div class="pe-tip-line">All calculations are done in compute.</div>
                    <div class="pe-tip-line"><strong>Modes:</strong></div>
                    <div class="pe-tip-line">All-time is the full history.</div>
                    <div class="pe-tip-line">5Y is the last five years.</div>
                </span>
            </span>
        </div>
        <div class="fc-legend">
            <span class="fc-legend-text">Legend:</span>
            <span class="fc-legend-item"><span class="fc-legend-dot fc-legend-dot-funds">o</span> Funds</span>
            <span class="fc-legend-item"><span class="fc-legend-dot fc-legend-dot-comm">o</span> Commercials</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_funds_vs_commercials(df_asset: pd.DataFrame, row: dict, current_week: pd.Timestamp, fc_mode: str) -> None:
    """Render Funds vs Commercials comparison section with dual heatlines."""
    inject_extremes_css()

    def get_fc_values(kind: str) -> tuple:
        if kind == "net":
            min_col = f"fc_net_min_{fc_mode}"
            max_col = f"fc_net_max_{fc_mode}"
            pos_nc_col = f"fc_net_pos_nc_{fc_mode}"
            pos_comm_col = f"fc_net_pos_comm_{fc_mode}"
            cur_nc = row.get("nc_net")
            cur_comm = row.get("comm_net")
        else:
            min_col = f"fc_net_chg_min_{fc_mode}"
            max_col = f"fc_net_chg_max_{fc_mode}"
            pos_nc_col = f"fc_net_chg_pos_nc_{fc_mode}"
            pos_comm_col = f"fc_net_chg_pos_comm_{fc_mode}"
            cur_nc = row.get("nc_net_chg_1w")
            cur_comm = row.get("comm_net_chg_1w")
        return (
            row.get(min_col),
            row.get(max_col),
            cur_nc,
            row.get(pos_nc_col),
            cur_comm,
            row.get(pos_comm_col),
        )

    net_min, net_max, net_cur_nc, net_pos_nc, net_cur_comm, net_pos_comm = get_fc_values("net")
    chg_min, chg_max, chg_cur_nc, chg_pos_nc, chg_cur_comm, chg_pos_comm = get_fc_values("chg")

    tooltip_net = (
        f"Funds: Min {fmt_num(net_min)}, Current {fmt_num(net_cur_nc)}, Max {fmt_num(net_max)}<br>"
        f"Commercials: Min {fmt_num(net_min)}, Current {fmt_num(net_cur_comm)}, Max {fmt_num(net_max)}"
    )
    tooltip_chg = (
        f"Funds: Min {fmt_delta(chg_min)}, Current {fmt_delta(chg_cur_nc)}, Max {fmt_delta(chg_max)}<br>"
        f"Commercials: Min {fmt_delta(chg_min)}, Current {fmt_delta(chg_cur_comm)}, Max {fmt_delta(chg_max)}"
    )

    tooltip_net_escaped = tooltip_net.replace('"', "&quot;")
    tooltip_chg_escaped = tooltip_chg.replace('"', "&quot;")

    st.markdown(
        f"""
        <div class="fc-comparison-section">
            <div class="fc-heatline-row">
                <span class="extremes-label">Net positions:</span>
                {render_dual_heatline_html(
                    net_min,
                    net_max,
                    net_cur_nc,
                    net_pos_nc,
                    net_cur_comm,
                    net_pos_comm,
                    tooltip_net_escaped
                )}
            </div>
            <div class="fc-heatline-row">
                <span class="extremes-label">Net Delta 1w:</span>
                {render_dual_heatline_html(
                    chg_min,
                    chg_max,
                    chg_cur_nc,
                    chg_pos_nc,
                    chg_cur_comm,
                    chg_pos_comm,
                    tooltip_chg_escaped
                )}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snapshot(df_asset: pd.DataFrame, row: dict, current_week: pd.Timestamp) -> None:
    """Render Positioning Snapshot section."""
    inject_snapshot_css()

    def with_arrow(delta_val):
        if pd.isna(delta_val):
            return '<span style="color: #6b7280;">N/A</span>'
        if delta_val > 0:
            color = "#10b981"
            sign = "+"
            arrow_svg = (
                '<svg width="10" height="10" viewBox="0 0 12 12" '
                'style="margin-left: 4px; vertical-align: -1px;" '
                f'fill="{color}" xmlns="http://www.w3.org/2000/svg">'
                '<path d="M6 1 L11 6 H8 V11 H4 V6 H1 Z"/></svg>'
            )
        elif delta_val < 0:
            color = "#ef4444"
            sign = ""
            arrow_svg = (
                '<svg width="10" height="10" viewBox="0 0 12 12" '
                'style="margin-left: 4px; vertical-align: -1px; transform: rotate(180deg);" '
                f'fill="{color}" xmlns="http://www.w3.org/2000/svg">'
                '<path d="M6 1 L11 6 H8 V11 H4 V6 H1 Z"/></svg>'
            )
        else:
            color = "#6b7280"
            sign = ""
            arrow_svg = ""
        value = fmt_num(delta_val)
        return f'<span style="color: {color}; font-weight: 600;">{sign}{value}{arrow_svg}</span>'

    st.markdown(
        """
        <div class="ps-header-container">
            <h4 class="ps-header-title">Positioning Snapshot</h4>
            <span class="ps-help">?
                <span class="ps-tip">
                    <div class="ps-tip-line"><strong>Snapshot</strong> is a quick view of current positioning.</div>
                    <div class="ps-tip-line"><strong>Net</strong> = Long - Short.</div>
                    <div class="ps-tip-line"><strong>13W avg</strong> is computed in compute.</div>
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nc_long_13w = row.get("nc_long_ma_13w")
    nc_short_13w = row.get("nc_short_ma_13w")
    nc_total_13w = row.get("nc_total_ma_13w")
    comm_long_13w = row.get("comm_long_ma_13w")
    comm_short_13w = row.get("comm_short_ma_13w")
    comm_total_13w = row.get("comm_total_ma_13w")

    card_funds, card_comm, card_nr = st.columns(3)

    with card_funds:
        net_val = row.get("nc_net", 0)
        net_delta = row.get("nc_net_chg_1w")
        nc_net_13w_data = get_13w_net_data(df_asset, current_week, "nc_net")
        spark_svg_funds = create_sparkline(nc_net_13w_data)
        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-sparkline">
                    {spark_svg_funds}
                </div>
                <div class="position-card-title">Funds</div>
                <div class="position-net-label">Net Positions</div>
                <div class="position-net">{fmt_num(net_val)}</div>
                <div class="position-delta">{with_arrow(net_delta)}</div>
                <div class="position-move-strength">{fmt_move_strength(
                    row.get("nc_net_chg_1w"),
                    row.get("nc_net_move_pct_all"),
                    row.get("nc_net_chg_1w_min_all"),
                    row.get("nc_net_chg_1w_max_all"),
                )}</div>
                <div class="position-details-grid">
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header">13W avg</div>
                    <div class="position-detail-label">Long:</div>
                    <div class="position-detail-value">{fmt_num(row.get("nc_long", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("nc_long_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(nc_long_13w)}</div>
                    <div class="position-detail-label">Short:</div>
                    <div class="position-detail-value">{fmt_num(row.get("nc_short", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("nc_short_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(nc_short_13w)}</div>
                    <div class="position-detail-label">Total:</div>
                    <div class="position-detail-value">{fmt_num(row.get("nc_total", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("nc_total_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(nc_total_13w)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_comm:
        net_val = row.get("comm_net", 0)
        net_delta = row.get("comm_net_chg_1w")
        comm_net_13w_data = get_13w_net_data(df_asset, current_week, "comm_net")
        spark_svg_comm = create_sparkline(comm_net_13w_data)
        st.markdown(
            f"""
            <div class="position-card">
                <div class="position-sparkline">
                    {spark_svg_comm}
                </div>
                <div class="position-card-title">Commercials</div>
                <div class="position-net-label">Net Positions</div>
                <div class="position-net">{fmt_num(net_val)}</div>
                <div class="position-delta">{with_arrow(net_delta)}</div>
                <div class="position-move-strength">{fmt_move_strength(
                    row.get("comm_net_chg_1w"),
                    row.get("comm_net_move_pct_all"),
                    row.get("comm_net_chg_1w_min_all"),
                    row.get("comm_net_chg_1w_max_all"),
                )}</div>
                <div class="position-details-grid">
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header"></div>
                    <div class="position-detail-header">13W avg</div>
                    <div class="position-detail-label">Long:</div>
                    <div class="position-detail-value">{fmt_num(row.get("comm_long", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("comm_long_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(comm_long_13w)}</div>
                    <div class="position-detail-label">Short:</div>
                    <div class="position-detail-value">{fmt_num(row.get("comm_short", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("comm_short_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(comm_short_13w)}</div>
                    <div class="position-detail-label">Total:</div>
                    <div class="position-detail-value">{fmt_num(row.get("comm_total", 0))}</div>
                    <div class="position-detail-delta">{with_arrow(row.get("comm_total_chg_1w"))}</div>
                    <div class="position-detail-13w">{fmt_num(comm_total_13w)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_nr:
        nr_long = row.get("nr_long")
        nr_short = row.get("nr_short")
        nr_total = row.get("nr_total")
        nr_net = row.get("nr_net")

        has_nr_data = (
            (nr_long is not None and pd.notna(nr_long)) or
            (nr_short is not None and pd.notna(nr_short)) or
            (nr_total is not None and pd.notna(nr_total)) or
            (nr_net is not None and pd.notna(nr_net))
        )

        if has_nr_data:
            net_delta = row.get("nr_net_chg_1w")
            long_delta = row.get("nr_long_chg_1w")
            short_delta = row.get("nr_short_chg_1w")
            total_delta = row.get("nr_total_chg_1w")

            nr_long_13w = row.get("nr_long_ma_13w")
            nr_short_13w = row.get("nr_short_ma_13w")
            nr_total_13w = row.get("nr_total_ma_13w")

            nr_net_13w_data = get_13w_net_data(df_asset, current_week, "nr_net") if "nr_net" in df_asset.columns else []
            spark_svg_nr = create_sparkline(nr_net_13w_data)

            st.markdown(
                f"""
                <div class="position-card">
                    <div class="position-sparkline">
                        {spark_svg_nr}
                    </div>
                    <div class="position-card-title">Non-Reported</div>
                    <div class="position-net-label">Net Positions</div>
                    <div class="position-net">{fmt_num(nr_net)}</div>
                    <div class="position-delta">{with_arrow(net_delta)}</div>
                    <div class="position-move-strength">{fmt_move_strength(
                        row.get("nr_net_chg_1w"),
                        row.get("nr_net_move_pct_all"),
                        row.get("nr_net_chg_1w_min_all"),
                        row.get("nr_net_chg_1w_max_all"),
                    )}</div>
                    <div class="position-details-grid">
                        <div class="position-detail-header"></div>
                        <div class="position-detail-header"></div>
                        <div class="position-detail-header"></div>
                        <div class="position-detail-header">13W avg</div>
                        <div class="position-detail-label">Long:</div>
                        <div class="position-detail-value">{fmt_num(nr_long)}</div>
                        <div class="position-detail-delta">{with_arrow(long_delta)}</div>
                        <div class="position-detail-13w">{fmt_num(nr_long_13w)}</div>
                        <div class="position-detail-label">Short:</div>
                        <div class="position-detail-value">{fmt_num(nr_short)}</div>
                        <div class="position-detail-delta">{with_arrow(short_delta)}</div>
                        <div class="position-detail-13w">{fmt_num(nr_short_13w)}</div>
                        <div class="position-detail-label">Total:</div>
                        <div class="position-detail-value">{fmt_num(nr_total)}</div>
                        <div class="position-detail-delta">{with_arrow(total_delta)}</div>
                        <div class="position-detail-13w">{fmt_num(nr_total_13w)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="position-card">
                    <div class="position-card-title">Non-Reported</div>
                    <div class="position-net-label">Net Positions</div>
                    <div class="position-net">N/A</div>
                    <p style="color: #6b7280; font-size: 0.85rem; margin-top: 1rem;">No data in metrics_weekly.parquet</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
