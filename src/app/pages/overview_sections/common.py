"""Common UI helpers for overview sections."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def fmt_num(val):
    """Format number as integer with thousand separators."""
    if pd.isna(val):
        return "N/A"
    try:
        return f"{int(round(val)):,}"
    except (ValueError, TypeError):
        return "N/A"


def fmt_delta(val):
    """Format delta with sign as integer."""
    if pd.isna(val):
        return "N/A"
    sign = "+" if val >= 0 else ""
    return f"{sign}{fmt_num(val)}"


def fmt_delta_colored(val):
    """Format delta with color based on sign as integer."""
    if pd.isna(val):
        return '<span style="color: #6b7280;">N/A</span>'
    if val == 0:
        return '<span style="color: #6b7280;">0</span>'
    if val > 0:
        color = "#10b981"  # green
        sign = "+"
    else:
        color = "#ef4444"  # red
        sign = ""
    value = fmt_num(val)
    return f'<span style="color: {color}; font-weight: 600;">{sign}{value}</span>'


def fmt_oi_sparkline_tooltip(oi_val, oi_chg_1w) -> str:
    """Format tooltip text for OI sparkline (value + delta)."""
    oi_text = fmt_num(oi_val)
    chg_text = fmt_delta(oi_chg_1w)
    return f"OI: {oi_text} | Delta 1w: {chg_text}"


def fmt_move_strength(chg_val, pct_val, min_val, max_val) -> str:
    """
    Format move strength row with delta and percentile.

    Args:
        chg_val: net_chg_1w value (signed delta)
        pct_val: net_move_pct_all value (percentile 0..1)
        min_val: precomputed min value from compute
        max_val: precomputed max value from compute

    Returns:
        HTML string with formatted move strength and tooltip
    """
    if pd.isna(chg_val):
        tooltip_delta = "N/A"
    else:
        tooltip_delta = fmt_delta(chg_val)

    tooltip_min = fmt_delta(min_val) if min_val is not None and pd.notna(min_val) else "N/A"
    tooltip_max = fmt_delta(max_val) if max_val is not None and pd.notna(max_val) else "N/A"

    if pd.isna(pct_val):
        pct_html = '<span style="color: #6b7280;">N/A</span>'
    else:
        pct_rounded = round(pct_val * 100)
        if pct_rounded < 30:
            pct_color = "#6b7280"  # neutral gray
        elif pct_rounded < 60:
            pct_color = "#6fbf73"  # soft green
        elif pct_rounded < 80:
            pct_color = "#f5b93d"  # amber/yellow
        elif pct_rounded < 95:
            pct_color = "#f08c2e"  # orange
        else:
            pct_color = "#ef4444"  # red
        pct_html = f'<span style="color: {pct_color}; font-weight: 600;">{pct_rounded}%</span>'

    tooltip_text = f"Min: {tooltip_min} | Current change: {tooltip_delta} | Max: {tooltip_max}"
    tooltip_escaped = tooltip_text.replace('"', "&quot;")
    return f'<span title="{tooltip_escaped}" style="cursor: help;">Move strength: {pct_html}</span>'


def create_sparkline(values, width=180, height=42, stroke_width=1.5, dot_radius=2):
    """Create SVG sparkline with per-segment coloring."""
    if not values or len(values) < 2:
        return ""

    clean_values = [v for v in values if pd.notna(v)]
    if len(clean_values) < 2:
        return ""

    min_val = min(clean_values)
    max_val = max(clean_values)
    val_range = max_val - min_val if max_val != min_val else 1

    padding = 4
    chart_width = width - 2 * padding
    chart_height = height - 2 * padding

    def get_color(val):
        return "#10b981" if val >= 0 else "#ef4444"

    def val_to_y(val):
        return padding + chart_height - ((val - min_val) / val_range) * chart_height

    def idx_to_x(i):
        return padding + (i / (len(values) - 1)) * chart_width if len(values) > 1 else padding

    def get_val_at_idx(i):
        if i < len(values) and pd.notna(values[i]):
            return values[i]
        for j in range(i, -1, -1):
            if j < len(values) and pd.notna(values[j]):
                return values[j]
        return 0

    segments = []
    zero_y = val_to_y(0)

    orig_to_clean = {}
    clean_idx = 0
    for orig_idx, val in enumerate(values):
        if pd.notna(val):
            orig_to_clean[orig_idx] = clean_idx
            clean_idx += 1

    for i in range(len(clean_values) - 1):
        v_i = clean_values[i]
        v_next = clean_values[i + 1]

        orig_i = None
        orig_next = None
        for orig_idx, clean_idx_val in orig_to_clean.items():
            if clean_idx_val == i:
                orig_i = orig_idx
            if clean_idx_val == i + 1:
                orig_next = orig_idx

        if orig_i is None or orig_next is None:
            continue

        x_i = idx_to_x(orig_i)
        y_i = val_to_y(v_i)
        x_next = idx_to_x(orig_next)
        y_next = val_to_y(v_next)

        if (v_i >= 0 and v_next < 0) or (v_i < 0 and v_next >= 0):
            if v_next != v_i:
                t = (0 - v_i) / (v_next - v_i)
                x_zero = x_i + t * (x_next - x_i)
                y_zero = zero_y

                color1 = get_color(v_i)
                segments.append(
                    f'<line x1="{x_i:.2f}" y1="{y_i:.2f}" x2="{x_zero:.2f}" y2="{y_zero:.2f}" stroke="{color1}" stroke-width="{stroke_width}" stroke-linecap="round" pointer-events="none"/>'
                )

                color2 = get_color(v_next)
                segments.append(
                    f'<line x1="{x_zero:.2f}" y1="{y_zero:.2f}" x2="{x_next:.2f}" y2="{y_next:.2f}" stroke="{color2}" stroke-width="{stroke_width}" stroke-linecap="round" pointer-events="none"/>'
                )
            else:
                color = get_color(v_i)
                segments.append(
                    f'<line x1="{x_i:.2f}" y1="{y_i:.2f}" x2="{x_next:.2f}" y2="{y_next:.2f}" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" pointer-events="none"/>'
                )
        else:
            color = get_color(v_i)
            segments.append(
                f'<line x1="{x_i:.2f}" y1="{y_i:.2f}" x2="{x_next:.2f}" y2="{y_next:.2f}" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" pointer-events="none"/>'
            )

    last_idx = len(values) - 1
    last_val = get_val_at_idx(last_idx)
    last_x = idx_to_x(last_idx)
    last_y = val_to_y(last_val)
    marker_color = get_color(last_val)
    last_dot_svg = f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="{dot_radius}" fill="{marker_color}" pointer-events="none"/>'

    path_svg = "".join(segments)
    spark_svg = f'''<svg width="{width}" height="{height}" style="display: block;" pointer-events="none">
        {path_svg}
        {last_dot_svg}
    </svg>'''

    return spark_svg


def get_13w_net_data(df_asset: pd.DataFrame, current_week: pd.Timestamp, col_name: str) -> list:
    """
    Get last 13 weeks of data up to current week for sparkline visualization.

    This is allowed: sparkline is just visualization of a data slice, not a metric calculation.
    """
    if col_name not in df_asset.columns:
        return []
    df_asset_sorted = df_asset.sort_values("report_date").reset_index(drop=True)
    df_up_to_week = df_asset_sorted[df_asset_sorted["report_date"] <= current_week].copy()
    if df_up_to_week.empty:
        return []
    df_last_13 = df_up_to_week.tail(13)
    return df_last_13[col_name].tolist()


def get_recent_n_data(
    df_asset: pd.DataFrame,
    current_week: pd.Timestamp,
    col_name: str,
    n_weeks: int,
) -> list:
    """
    Get recent N weeks of data up to current week for sparkline visualization.
    """
    if col_name not in df_asset.columns:
        return []
    df_asset_sorted = df_asset.sort_values("report_date").reset_index(drop=True)
    df_up_to_week = df_asset_sorted[df_asset_sorted["report_date"] <= current_week].copy()
    if df_up_to_week.empty:
        return []
    df_last_n = df_up_to_week.tail(n_weeks)
    return df_last_n[col_name].tolist()


def render_heatline_html(min_val, max_val, current_val, pos_val, is_delta: bool = False):
    """
    Render heatline as HTML string for inline use (uses pre-computed pos_val from compute).

    Args:
        min_val: Pre-computed min from compute (for tooltip)
        max_val: Pre-computed max from compute (for tooltip)
        current_val: Current value (for tooltip)
        pos_val: Pre-computed position (0..1) from compute (used for visualization)
        is_delta: If True, format values as delta
    """
    bar_height = 18
    dot_size = 10
    dot_border = 2
    bar_radius = 3

    is_missing = (
        pos_val is None
        or pd.isna(pos_val)
        or min_val is None
        or max_val is None
        or current_val is None
        or pd.isna(min_val)
        or pd.isna(max_val)
        or pd.isna(current_val)
    )

    if is_missing:
        tooltip_text = "No data for this week"
        tooltip_escaped = tooltip_text.replace('"', "&quot;")
        return f'''<div class="cot-heatline" title="{tooltip_escaped}">
            <div class="cot-heatline-bar cot-heatline-missing" style="position: relative; height: {bar_height}px; width: 100%; background: repeating-linear-gradient(to right, #d1d5db 0, #d1d5db 4px, transparent 4px, transparent 8px); border-radius: {bar_radius}px; margin: 0; cursor: pointer;">
                <div class="cot-heatline-dot" style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: {dot_size}px; height: {dot_size}px; background-color: #9ca3af; border: {dot_border}px solid #f3f4f6; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"></div>
            </div>
        </div>'''

    pos_pct = max(0.0, min(100.0, pos_val * 100))
    if is_delta:
        min_str = fmt_delta(min_val)
        max_str = fmt_delta(max_val)
        curr_str = fmt_delta(current_val)
    else:
        min_str = fmt_num(min_val)
        max_str = fmt_num(max_val)
        curr_str = fmt_num(current_val)
    tooltip_text = f"Min: {min_str} | Current: {curr_str} | Max: {max_str}"
    tooltip_escaped = tooltip_text.replace('"', "&quot;")

    dot_bg = "rgba(17, 24, 39, 0.9)"
    dot_border_color = "rgba(255, 255, 255, 0.95)"
    dot_shadow = "0 1px 3px rgba(0,0,0,0.35)"

    html = f'''<div class="cot-heatline" title="{tooltip_escaped}">
        <div class="cot-heatline-bar" style="position: relative; height: {bar_height}px; width: 100%; background: linear-gradient(to right, #4A90E2 0%, #4A90E2 25%, #F5F5F5 50%, #F5F5F5 75%, #E74C3C 100%); border-radius: {bar_radius}px; margin: 0; cursor: pointer;">
            <div class="cot-heatline-dot" style="position: absolute; left: {pos_pct}%; top: 50%; transform: translate(-50%, -50%); width: {dot_size}px; height: {dot_size}px; background-color: {dot_bg}; border: {dot_border}px solid {dot_border_color}; border-radius: 50%; box-shadow: {dot_shadow};"></div>
        </div>
    </div>'''
    return html


def render_dual_heatline_html(
    min_val: float,
    max_val: float,
    cur_a: float,
    pos_a: float,
    cur_b: float,
    pos_b: float,
    tooltip_html: str,
    compact: bool = False,
) -> str:
    """Render dual heatline with two markers on one scale."""
    bar_height = 18
    dot_size = 10
    dot_border = 2
    bar_radius = 3

    pos_a_pct = max(0.0, min(100.0, pos_a * 100)) if pos_a is not None and pd.notna(pos_a) else None
    pos_b_pct = max(0.0, min(100.0, pos_b * 100)) if pos_b is not None and pd.notna(pos_b) else None

    is_missing = (
        min_val is None
        or max_val is None
        or pd.isna(min_val)
        or pd.isna(max_val)
        or (pos_a_pct is None and pos_b_pct is None)
    )
    if is_missing:
        tooltip_text = "No data for this week"
        tooltip_escaped = tooltip_text.replace('"', "&quot;")
        return f'''<div class="cot-heatline cot-heatline-dual" title="{tooltip_escaped}">
            <div class="cot-heatline-bar" style="position: relative; height: {bar_height}px; width: 100%; background: repeating-linear-gradient(to right, #d1d5db 0, #d1d5db 4px, transparent 4px, transparent 8px); border-radius: {bar_radius}px; margin: 0; cursor: pointer;">
                <div class="cot-heatline-dot" style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: {dot_size}px; height: {dot_size}px; background-color: #9ca3af; border: {dot_border}px solid #f3f4f6; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"></div>
            </div>
        </div>'''

    dot_a_bg = "#3b82f6"
    dot_a_border = "#1e40af"
    dot_b_bg = "#ef4444"
    dot_b_border = "#991b1b"
    dot_shadow = "0 1px 3px rgba(0,0,0,0.35)"

    dots_html = []
    if pos_a_pct is not None:
        offset_a = "-2px" if (pos_b_pct is not None and abs(pos_a_pct - pos_b_pct) < 3) else "0px"
        dots_html.append(
            f'<div class="heatline-dot-a" style="position: absolute; left: {pos_a_pct}%; top: calc(50% + {offset_a}); transform: translate(-50%, -50%); width: {dot_size}px; height: {dot_size}px; background-color: {dot_a_bg}; border: {dot_border}px solid {dot_a_border}; border-radius: 50%; box-shadow: {dot_shadow}; z-index: 2;"></div>'
        )
    if pos_b_pct is not None:
        offset_b = "+2px" if (pos_a_pct is not None and abs(pos_a_pct - pos_b_pct) < 3) else "0px"
        dots_html.append(
            f'<div class="heatline-dot-b" style="position: absolute; left: {pos_b_pct}%; top: calc(50% + {offset_b}); transform: translate(-50%, -50%); width: {dot_size}px; height: {dot_size}px; background-color: {dot_b_bg}; border: {dot_border}px solid {dot_b_border}; border-radius: 50%; box-shadow: {dot_shadow}; z-index: 2;"></div>'
        )

    html = f'''<div class="cot-heatline cot-heatline-dual" title="{tooltip_html}">
        <div class="cot-heatline-bar" style="position: relative; height: {bar_height}px; width: 100%; background: linear-gradient(to right, #4A90E2 0%, #4A90E2 25%, #F5F5F5 50%, #F5F5F5 75%, #E74C3C 100%); border-radius: {bar_radius}px; margin: 0; cursor: pointer;">
            {''.join(dots_html)}
        </div>
    </div>'''
    return html


def render_flow_rotation_bar_html(
    net_chg: float | None,
    gross_chg: float | None,
    rotation_share: float | None,
    net_share: float | None,
    rotation: float | None = None,
    long_chg: float | None = None,
    short_chg: float | None = None,
    tooltip_text: str = "",
) -> str:
    """Render Gross vs Net vs Rotation composition bar."""
    bar_height = 14
    bar_radius = 3

    if gross_chg is None or pd.isna(gross_chg) or gross_chg == 0:
        return '<span style="color: #6b7280;">N/A</span>'

    gross_val = float(gross_chg)

    rotation_share_val = float(rotation_share) if rotation_share is not None and pd.notna(rotation_share) else 0.0
    net_share_val = float(net_share) if net_share is not None and pd.notna(net_share) else 0.0

    rotation_share_val = max(0.0, min(1.0, rotation_share_val))
    net_share_val = max(0.0, min(1.0, net_share_val))

    net_pct = net_share_val * 100.0
    rotation_pct = rotation_share_val * 100.0

    segments = []
    if net_pct > 0:
        color_class = "flow-rotation-green" if (net_chg is not None and pd.notna(net_chg) and float(net_chg) >= 0) else "flow-rotation-red"
        segments.append(
            f'<div class="flow-rotation-segment {color_class}" style="width: {net_pct}%;"></div>'
        )

    if rotation_pct > 0:
        segments.append(
            f'<div class="flow-rotation-segment flow-rotation-yellow" style="width: {rotation_pct}%;"></div>'
        )

    if not segments:
        segments_html = '<div class="flow-rotation-segment" style="width: 100%; background-color: #374151;"></div>'
    else:
        segments_html = "".join(segments)

    if not tooltip_text:
        tooltip_lines = []
        if net_chg is not None and pd.notna(net_chg):
            tooltip_lines.append(f"Net Delta 1w: {fmt_delta(net_chg)}")
        if gross_val > 0:
            tooltip_lines.append(f"Gross: {fmt_num(gross_val)}")
        if rotation is not None and pd.notna(rotation) and rotation > 0:
            rot_share_pct = f"{rotation_share_val*100:.0f}%" if rotation_share is not None and pd.notna(rotation_share) else ""
            if rot_share_pct:
                tooltip_lines.append(f"Rotation: {fmt_num(rotation)} ({rot_share_pct})")
            else:
                tooltip_lines.append(f"Rotation: {fmt_num(rotation)}")
        tooltip_text = " | ".join(tooltip_lines)

    tooltip_escaped = tooltip_text.replace('"', "&quot;")

    html = f'''<div class="flow-rotation-bar-container" title="{tooltip_escaped}">
        <div class="flow-rotation-bar" style="height: {bar_height}px; border-radius: {bar_radius}px; background-color: #374151; position: relative; overflow: hidden; display: flex;">
            {segments_html}
        </div>
    </div>'''
    return html


def inject_shared_css() -> None:
    """Inject shared CSS styles for headers and tooltips (called by both Snapshot and Extremes)."""
    st.markdown(
        """
        <style>
        .ps-header-container,
        .pe-header-container {
            display: flex;
            align-items: center;
            margin-bottom: 0.3rem;
        }
        .ps-header-title,
        .pe-header-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0;
            margin-right: 0.4rem;
        }
        .ps-help,
        .pe-help {
            position: relative;
            display: inline-block;
            cursor: help;
            color: #6b7280;
            font-size: 0.85rem;
            line-height: 1;
            vertical-align: middle;
        }
        .ps-tip,
        .pe-tip {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            left: 20px;
            top: -8px;
            width: 340px;
            background-color: #1f2937;
            color: #f9fafb;
            font-size: 12px;
            line-height: 1.3;
            padding: 10px 12px;
            border-radius: 8px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.25);
            z-index: 1000;
            transition: opacity 0.2s ease-in-out;
            pointer-events: none;
        }
        .ps-help:hover .ps-tip,
        .pe-help:hover .pe-tip {
            visibility: visible;
            opacity: 1;
        }
        .ps-tip-line,
        .pe-tip-line {
            margin: 0;
            padding: 0;
            margin-bottom: 4px;
        }
        .ps-tip-line:last-child,
        .pe-tip-line:last-child {
            margin-bottom: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_snapshot_css() -> None:
    """Inject CSS styles for Snapshot section (includes shared headers if not already injected)."""
    inject_shared_css()
    st.markdown(
        """
        <style>
        .position-card {
            background-color: #f0f2f6;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            margin-top: 0.5rem;
            position: relative;
        }
        .position-card-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 0.75rem;
            color: #1f2937;
        }
        .position-sparkline {
            position: absolute;
            top: 14px;
            right: 16px;
            width: 180px;
            height: 42px;
        }
        .position-sparkline svg {
            display: block;
            pointer-events: none;
        }
        .position-sparkline svg * {
            pointer-events: none;
        }
        .position-net-label {
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 0.3rem;
            font-weight: 500;
        }
        .position-net {
            font-size: 2rem;
            font-weight: 700;
            color: #1f2937;
            margin: 0.3rem 0;
        }
        .position-delta {
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        .oi-meta {
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 0.3rem;
        }
        .oi-meta strong {
            color: #111827;
            font-weight: 600;
        }
        .oi-risk-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            background: #e5e7eb;
            color: #111827;
        }
        .oi-risk-low {
            background: #d1fae5;
            color: #065f46;
        }
        .oi-risk-elevated {
            background: #fef3c7;
            color: #92400e;
        }
        .oi-risk-high {
            background: #fee2e2;
            color: #991b1b;
        }
        .oi-panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 12px;
        }
        .oi-panel {
            background: #f3f4f6;
            border-radius: 0.5rem;
            padding: 0.75rem 0.9rem;
        }
        .oi-panel-title {
            font-size: 0.8rem;
            font-weight: 600;
            color: #6b7280;
            margin-bottom: 0.4rem;
        }
        .oi-panel-row {
            font-size: 0.85rem;
            color: #374151;
            margin-bottom: 0.35rem;
        }
        .oi-panel-row:last-child {
            margin-bottom: 0;
        }
        .oi-panel-value {
            font-weight: 600;
            color: #111827;
        }
        .oi-percentile-label {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: -10px;
        }
        .position-move-strength {
            font-size: 0.85rem;
            margin-bottom: 1rem;
            color: #6b7280;
        }
        .weekly-move-block {
            margin-top: 10px;
            background-color: #f0f2f6;
            border-radius: 0.5rem;
            padding: 1rem;
        }
        .weekly-move-header {
            font-size: 0.9rem;
            font-weight: 600;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }
        .weekly-move-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            min-height: 18px;
        }
        .weekly-move-row:last-child {
            margin-bottom: 0;
        }
        .weekly-move-label {
            color: #6b7280;
            font-weight: 600;
            font-size: 0.9rem;
            width: 90px;
            flex-shrink: 0;
        }
        .weekly-move-heatline {
            flex: 1;
            min-width: 0;
        }
        .position-details-grid {
            display: grid;
            grid-template-columns: auto 1fr auto 80px;
            gap: 0.5rem 0.8rem;
            margin: 0.5rem 0;
            font-size: 0.9rem;
            align-items: center;
        }
        .position-detail-header {
            font-size: 0.75rem;
            color: #6b7280;
            font-weight: 500;
            text-align: right;
        }
        .position-detail-label {
            color: #6b7280;
        }
        .position-detail-value {
            color: #1f2937;
            font-weight: 600;
            text-align: right;
        }
        .position-detail-delta {
            text-align: right;
        }
        .position-detail-13w {
            color: #6b7280;
            font-size: 0.85rem;
            text-align: right;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_extremes_css() -> None:
    """Inject CSS styles for Extremes section (includes shared headers if not already injected)."""
    inject_shared_css()
    st.markdown(
        """
        <style>
        .position-extremes-rows {
            margin-top: 0.5rem;
        }
        .extremes-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            min-height: 18px;
        }
        .extremes-row:last-child {
            margin-bottom: 0;
        }
        .extremes-label {
            color: #6b7280;
            font-weight: 600;
            font-size: 0.9rem;
            width: 90px;
            flex-shrink: 0;
        }
        .extremes-heatline {
            flex: 1;
            min-width: 0;
        }
        .cot-heatline {
            flex: 1;
            min-width: 0;
        }
        .cot-heatline-bar {
            position: relative;
        }
        .cot-heatline-dot {
            position: absolute;
            top: 50%;
            transform: translate(-50%, -50%);
        }
        .cot-heatline-dual {
            flex: 1;
            min-width: 0;
        }
        .heatline-dot-a {
            z-index: 2;
        }
        .heatline-dot-b {
            z-index: 2;
        }
        .fc-comparison-section {
            margin-top: 1rem;
        }
        .fc-heatline-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            min-height: 18px;
        }
        .fc-heatline-row:last-child {
            margin-bottom: 0;
        }
        .flow-rotation-bar-container {
            flex: 1;
            min-width: 0;
            cursor: pointer;
        }
        .flow-rotation-bar {
            height: 14px;
            border-radius: 3px;
            background-color: #374151;
            position: relative;
            overflow: hidden;
            display: flex;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
        }
        .flow-rotation-segment {
            height: 100%;
            flex-shrink: 0;
            opacity: 0.9;
        }
        .flow-rotation-green {
            background-color: #2EA97D;
        }
        .flow-rotation-red {
            background-color: #D6655D;
        }
        .flow-rotation-yellow {
            background-color: #D1A21D;
        }
        .flow-rotation-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            min-height: 18px;
        }
        .flow-rotation-row:last-child {
            margin-bottom: 0;
        }
        .flow-rotation-label {
            color: #6b7280;
            font-weight: 600;
            font-size: 0.9rem;
            width: 90px;
            flex-shrink: 0;
        }
        .flow-rotation-text {
            font-size: 0.75rem;
            color: #9ca3af;
            margin-top: 2px;
        }
        .fc-legend {
            font-size: 12px;
            opacity: 0.7;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .fc-legend-text {
            font-weight: 500;
        }
        .fc-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }
        .fc-legend-dot {
            display: inline-block;
        }
        .fc-legend-dot-funds {
            color: #3b82f6;
        }
        .fc-legend-dot-comm {
            color: #ef4444;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_charts_css() -> None:
    """Inject CSS styles for Charts section."""
    st.markdown(
        """
        <style>
        .charts-toggles {
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
