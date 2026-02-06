"""Market Radar page: snapshot of hottest markets and conflicts."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
import html

import pandas as pd
import streamlit as st

from src.app.ui_state import APP_VERSION, set_selected_asset, set_selected_category
from src.common.paths import ProjectPaths

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@st.cache_data
def _load_market_radar(path_str: str, mtime: float) -> pd.DataFrame:
    """Load market_radar_latest.parquet with cache invalidation by mtime."""
    return pd.read_parquet(path_str)


@st.cache_data
def _load_market_positioning(path_str: str, mtime: float) -> pd.DataFrame:
    """Load market_positioning_latest.parquet with cache invalidation by mtime."""
    return pd.read_parquet(path_str)


def _init_filters() -> None:
    """Initialize filter defaults."""
    defaults = {
        "mr_view": "Table",
        "mr_hot_only": True,
        "mr_sort_by": "Hot score",
        "mr_conflict": "Any",
        "mr_oi_risk": "Any",
        "mr_funds_crowding": "Any",
        "mr_signal": "Any",
        "mr_show_empty": False,
        "mr_advanced_open": False,
        "mr_relax_msg": "",
        "mr_confirmed_imbalance_only": False,
        "mr_spec_crowding_only": False,
        "mr_commercial_opposition_only": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _signal_badge(signal_val) -> tuple[str, str]:
    """Return badge label and CSS class for signal value."""
    if signal_val is None or pd.isna(signal_val):
        return "N/A", "badge-neutral"
    try:
        sig = int(signal_val)
    except (TypeError, ValueError):
        return "N/A", "badge-neutral"
    if sig > 0:
        return f"+{sig}", "badge-bull"
    if sig < 0:
        return f"{sig}", "badge-bear"
    return "0", "badge-neutral"


def _summary_line(row: pd.Series) -> str:
    """Build a 1-line summary with max 2 clauses."""
    clauses = []
    conflict = row.get("conflict_level")
    if conflict == "High":
        clauses.append("Directional conflict between Funds and Commercials.")
    elif conflict == "Medium":
        clauses.append("Partial directional conflict.")

    funds_z = row.get("net_z_52w_funds")
    if funds_z is not None and pd.notna(funds_z):
        z_val = float(funds_z)
        if abs(z_val) >= 2.0:
            clauses.append(f"Funds extreme (Z={z_val:+.1f}).")
        elif abs(z_val) >= 1.5:
            clauses.append(f"Funds crowded (Z={z_val:+.1f}).")

    regime_map = {
        "Expansion_Early": "OI expansion (early).",
        "Expansion_Late": "OI expansion (late).",
        "Distribution": "OI distribution.",
        "Rebuild": "OI rebuild.",
        "Neutral": "OI neutral.",
        "Mixed": "OI mixed.",
    }
    oi_regime = row.get("oi_regime")
    if oi_regime in regime_map:
        clauses.append(regime_map[oi_regime])

    if not clauses:
        return "No major signals."
    if len(clauses) == 1:
        return clauses[0]
    return f"{clauses[0]} {clauses[1]}"


def _build_tags(row: pd.Series, max_tags: int = 3) -> list[str]:
    """Return first 2-3 tags from why_tags."""
    why_tags = row.get("why_tags")
    if why_tags is not None and pd.notna(why_tags):
        tags = [t.strip() for t in str(why_tags).split("|") if t.strip()]
        if tags:
            return tags[:max_tags]
    return ["No tags"]


def _expectation_label(signal_val) -> tuple[str, str]:
    """Map cot_traffic_signal to expectation label + class."""
    if signal_val is None or pd.isna(signal_val):
        return "Neutral", "expect-neutral"
    try:
        sig = float(signal_val)
    except (TypeError, ValueError):
        return "Neutral", "expect-neutral"
    if sig >= 1:
        return "Upside bias", "expect-up"
    if sig <= -1:
        return "Downside risk", "expect-down"
    return "Neutral", "expect-neutral"


def _fmt_k(val) -> str:
    """Format numeric value as k with sign."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if num > 0 else ""
    return f"{sign}{num/1000:.0f}k"


def _fmt_pct(val) -> str:
    """Format numeric value as percent."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "N/A"
    pct = num * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def _fmt_num(val, decimals: int = 0) -> str:
    """Format numeric with thousands separators and optional decimals."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if num > 0 else ""
    if decimals == 0:
        return f"{sign}{num:,.0f}"
    return f"{sign}{num:,.{decimals}f}"


def _fmt_pct_from_ratio(val) -> str:
    """Format ratio as percent with 1 decimal."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        num = float(val) * 100
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if num > 0 else ""
    return f"{sign}{num:.1f}%"


def _delta_class(val, threshold: float) -> str:
    """Return CSS class based on threshold."""
    if val is None or pd.isna(val):
        return "cell-neutral"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "cell-neutral"
    if num > threshold:
        return "cell-pos"
    if num < -threshold:
        return "cell-neg"
    return "cell-neutral"


def _z_class(val, threshold: float = 1.5) -> str:
    """Return CSS class for z-score highlight."""
    if val is None or pd.isna(val):
        return "z-neutral"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "z-neutral"
    if abs(num) >= threshold:
        return "z-crowded"
    return "z-neutral"


def _conflict_class(val) -> str:
    """Return CSS class for conflict level."""
    if val == "High":
        return "conflict-high"
    if val == "Medium":
        return "conflict-med"
    return "conflict-low"


def _active_filter_pills(categories_all: list[str], selected_categories: list[str]) -> list[str]:
    """Build active filter pills."""
    pills = []
    if st.session_state["mr_hot_only"]:
        pills.append("Hot only")
    if selected_categories and len(selected_categories) != len(categories_all):
        pills.append(f"Category: {', '.join(selected_categories)}")
    if st.session_state["mr_conflict"] != "Any":
        pills.append(f"Conflict: {st.session_state['mr_conflict']}")
    if st.session_state["mr_oi_risk"] != "Any":
        pills.append(f"OI Risk: {st.session_state['mr_oi_risk']}")
    if st.session_state["mr_funds_crowding"] != "Any":
        pills.append("Funds: Crowded")
    if st.session_state["mr_signal"] != "Any":
        pills.append(f"Signal: {st.session_state['mr_signal']}")
    if st.session_state.get("mr_confirmed_imbalance_only"):
        pills.append("Confirmed Imbalance")
    if st.session_state.get("mr_spec_crowding_only"):
        pills.append("Speculative Crowding")
    if st.session_state.get("mr_commercial_opposition_only"):
        pills.append("Commercial Opposition")
    return pills


def _apply_filters(df: pd.DataFrame, selected_categories: list[str]) -> pd.DataFrame:
    """Apply current filters to dataframe."""
    df_out = df.copy()
    if selected_categories:
        df_out = df_out[df_out["category"].isin(selected_categories)]

    if st.session_state["mr_conflict"] == "High only":
        df_out = df_out[df_out["conflict_level"] == "High"]

    if st.session_state["mr_oi_risk"] == "Elevated+":
        df_out = df_out[df_out["oi_risk_level"].isin(["Elevated", "High"])]
    elif st.session_state["mr_oi_risk"] == "High only":
        df_out = df_out[df_out["oi_risk_level"] == "High"]

    if st.session_state["mr_funds_crowding"] == "Crowded (abs Z >= 1.5)":
        df_out = df_out[df_out["net_z_52w_funds"].abs() >= 1.5]

    if st.session_state["mr_signal"] == "Bull (+1,+2)":
        df_out = df_out[df_out["cot_traffic_signal"].isin([1, 2])]
    elif st.session_state["mr_signal"] == "Bear (-1,-2)":
        df_out = df_out[df_out["cot_traffic_signal"].isin([-1, -2])]
    elif st.session_state["mr_signal"] == "Neutral (0)":
        df_out = df_out[df_out["cot_traffic_signal"] == 0]

    if st.session_state["mr_hot_only"]:
        df_out = df_out[df_out["is_hot"] == True]

    if st.session_state.get("mr_confirmed_imbalance_only"):
        if "confirmed_imbalance" in df_out.columns:
            df_out = df_out[df_out["confirmed_imbalance"] == True]
    if st.session_state.get("mr_spec_crowding_only"):
        if "funds_crowded" in df_out.columns:
            df_out = df_out[df_out["funds_crowded"] == True]
    if st.session_state.get("mr_commercial_opposition_only"):
        if "commercial_opposition" in df_out.columns:
            df_out = df_out[df_out["commercial_opposition"] == True]

    return df_out


def _sort_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sort dataframe based on selection."""
    sort_by = st.session_state["mr_sort_by"]
    if sort_by == "Hot score":
        key = pd.to_numeric(df.get("hot_score"), errors="coerce")
    elif sort_by == "Signal":
        key = pd.to_numeric(df.get("cot_traffic_signal"), errors="coerce")
    elif sort_by == "OI risk":
        risk_map = {"High": 3, "Elevated": 2, "Low": 1}
        key = df.get("oi_risk_level").map(risk_map)
    elif sort_by == "Conflict":
        conflict_map = {"High": 3, "Medium": 2, "Low": 1}
        key = df.get("conflict_level").map(conflict_map)
    elif sort_by == "Funds z (abs)":
        key = pd.to_numeric(df.get("net_z_52w_funds"), errors="coerce").abs()
    elif sort_by == "OI z (abs)":
        key = pd.to_numeric(df.get("oi_z_52w"), errors="coerce").abs()
    else:
        key = pd.Series([0] * len(df), index=df.index)
    return df.assign(_sort_val=key).sort_values("_sort_val", ascending=False)


def _relax_filters(df: pd.DataFrame, selected_categories: list[str]) -> str:
    """Relax filters in priority order until >= 5 rows."""
    relaxed = []
    order = [
        ("mr_signal", "Any"),
        ("mr_funds_crowding", "Any"),
        ("mr_oi_risk", "Any"),
        ("mr_conflict", "Any"),
    ]
    for key, target in order:
        if st.session_state[key] != target:
            st.session_state[key] = target
            relaxed.append(key)
            df_try = _apply_filters(df, selected_categories)
            if len(df_try) >= 5:
                break
    df_after = _apply_filters(df, selected_categories)
    if relaxed:
        label_map = {
            "mr_signal": "Signal",
            "mr_funds_crowding": "Funds Crowding",
            "mr_oi_risk": "OI Risk",
            "mr_conflict": "Conflict",
        }
        relaxed_labels = ", ".join([label_map[r] for r in relaxed])
        return f"Filters were relaxed automatically to show {len(df_after)} markets ({relaxed_labels})."
    return ""


def _reset_filters_state() -> None:
    """Reset filters to defaults (keeps category selection)."""
    for key, val in {
        "mr_hot_only": True,
        "mr_sort_by": "Hot score",
        "mr_conflict": "Any",
        "mr_oi_risk": "Any",
        "mr_funds_crowding": "Any",
        "mr_signal": "Any",
        "mr_show_empty": False,
        "mr_confirmed_imbalance_only": False,
        "mr_spec_crowding_only": False,
        "mr_commercial_opposition_only": False,
    }.items():
        st.session_state[key] = val
    st.session_state["mr_relax_msg"] = ""


def _get_scalar_count(df: pd.DataFrame, col: str, fallback: int | None = None) -> str:
    """Return scalar count from a column or fallback."""
    if col in df.columns:
        series = df[col].dropna()
        if not series.empty:
            try:
                return str(int(series.iloc[0]))
            except (TypeError, ValueError):
                pass
    if fallback is None:
        return "N/A"
    return str(int(fallback))


def _assets_line(df_subset: pd.DataFrame, limit: int = 6) -> str:
    """Build a short assets line for KPI cards."""
    names = df_subset.get("market_name", pd.Series()).dropna().unique().tolist()
    if not names:
        return "None"
    visible = names[:limit]
    extra = len(names) - len(visible)
    line = ", ".join([str(x) for x in visible])
    if extra > 0:
        line = f"{line} +{extra}"
    return line


def render() -> None:
    """Render the Market Radar page."""
    _init_filters()

    paths = ProjectPaths(REPO_ROOT)
    radar_path = paths.data / "compute" / "market_radar_latest.parquet"
    positioning_path = paths.data / "compute" / "market_positioning_latest.parquet"
    if not radar_path.exists():
        st.error("market_radar_latest.parquet not found.")
        return
    if not positioning_path.exists() and st.session_state.get("mr_view", "Table") == "Table":
        st.error("market_positioning_latest.parquet not found.")
        return

    df = _load_market_radar(str(radar_path), radar_path.stat().st_mtime)
    if df.empty:
        st.warning("market_radar_latest.parquet is empty.")
        return

    df = df.copy()
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"])
        latest_date_radar = df["report_date"].max()
        df = df[df["report_date"] == latest_date_radar].copy()
    else:
        latest_date_radar = None

    df_pos = pd.DataFrame()
    latest_date_pos = None
    if positioning_path.exists():
        df_pos = _load_market_positioning(str(positioning_path), positioning_path.stat().st_mtime)
        if not df_pos.empty and "report_date" in df_pos.columns:
            df_pos["report_date"] = pd.to_datetime(df_pos["report_date"])
            latest_date_pos = df_pos["report_date"].max()
            df_pos = df_pos[df_pos["report_date"] == latest_date_pos].copy()

    categories_present = df.get("category", pd.Series()).dropna().unique().tolist()

    st.markdown(
        """
        <style>
        .market-row {
          padding: 10px 12px;
          border-bottom: 1px solid #1f2937;
        }
        .market-name {
          font-weight: 700;
          color: #111827;
        }
        .market-head {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .expect-badge {
          font-size: 12px;
          font-weight: 700;
          padding: 3px 8px;
          border-radius: 999px;
          line-height: 1;
        }
        .expect-up { background: #dcfce7; color: #166534; }
        .expect-neutral { background: #fef9c3; color: #854d0e; }
        .expect-down { background: #fee2e2; color: #991b1b; }
        .badge {
          font-size: 12px;
          font-weight: 700;
          padding: 3px 8px;
          border-radius: 999px;
          line-height: 1;
        }
        .badge-bull { background: #dcfce7; color: #166534; }
        .badge-neutral { background: #fef9c3; color: #854d0e; }
        .badge-bear { background: #fee2e2; color: #991b1b; }
        .market-summary {
          color: #9ca3af;
          font-size: 12px;
        }
        .facts-row {
          font-size: 12px;
          color: #e5e7eb;
          margin-top: 4px;
        }
        .chip {
          display: inline-block;
          font-size: 12px;
          padding: 3px 8px;
          border-radius: 999px;
          background: #eef2f7;
          color: #374151;
          margin-right: 6px;
        }
        .market-meta {
          font-size: 12px;
          color: #6b7280;
          text-align: right;
        }
        .filter-pill {
          display: inline-block;
          font-size: 12px;
          padding: 3px 8px;
          border-radius: 999px;
          background: #111827;
          color: #f9fafb;
          margin-right: 6px;
          margin-top: 6px;
        }
        .empty-state {
          text-align: center;
          background: #f8fafc;
          border: 1px dashed #d1d5db;
          padding: 18px;
          border-radius: 12px;
          margin: 14px 0;
        }
        .kpi-card {
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 10px 12px;
        }
        .kpi-title {
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 4px;
        }
        .kpi-value {
          font-size: 20px;
          font-weight: 700;
          color: #111827;
        }
        section[data-testid="stMain"] button[kind="primary"],
        section[data-testid="stMain"] button[kind="secondary"],
        section[data-testid="stMain"] [data-testid^="baseButton-"] {
          background: #ffffff !important;
          border: 1px solid #e5e7eb !important;
          border-radius: 12px !important;
          padding: 10px 12px !important;
          text-align: left !important;
          color: #111827 !important;
          font-weight: 700 !important;
          line-height: 1.25 !important;
          white-space: pre-line !important;
        }
        section[data-testid="stMain"] button[kind="primary"] *,
        section[data-testid="stMain"] button[kind="secondary"] *,
        section[data-testid="stMain"] [data-testid^="baseButton-"] * {
          background-color: #ffffff !important;
          color: #111827 !important;
          border-color: #e5e7eb !important;
          white-space: pre-line !important;
        }
        section[data-testid="stMain"] button[kind="primary"]:hover,
        section[data-testid="stMain"] button[kind="secondary"]:hover,
        section[data-testid="stMain"] [data-testid^="baseButton-"]:hover {
          border-color: #cbd5f5 !important;
          background: #f1f5f9 !important;
        }
        section[data-testid="stMain"] button[kind="primary"]:active,
        section[data-testid="stMain"] button[kind="primary"]:focus,
        section[data-testid="stMain"] button[kind="primary"]:focus-visible,
        section[data-testid="stMain"] button[kind="secondary"]:active,
        section[data-testid="stMain"] button[kind="secondary"]:focus,
        section[data-testid="stMain"] button[kind="secondary"]:focus-visible,
        section[data-testid="stMain"] [data-testid^="baseButton-"]:active,
        section[data-testid="stMain"] [data-testid^="baseButton-"]:focus,
        section[data-testid="stMain"] [data-testid^="baseButton-"]:focus-visible {
          background-color: #ffffff !important;
          color: #111827 !important;
          border-color: #cbd5f5 !important;
          box-shadow: none !important;
        }
        .top-hot-card {
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 10px 12px;
        }
        .top-hot-title {
          font-size: 14px;
          font-weight: 700;
          color: #111827;
          margin-bottom: 4px;
        }
        .top-hot-meta {
          font-size: 12px;
          color: #6b7280;
        }
        .asset-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 8px;
          margin-bottom: 12px;
        }
        .asset-chip {
          background: #111827;
          color: #f9fafb;
          padding: 3px 8px;
          border-radius: 999px;
          font-size: 12px;
        }
        .table-header {
          font-size: 12px;
          font-weight: 700;
          color: #9ca3af;
          padding: 6px 2px;
        }
        .table-cell {
          font-size: 12px;
          color: #e5e7eb;
          padding: 6px 2px;
        }
        .table-cell.num {
          text-align: right;
          font-variant-numeric: tabular-nums;
        }
        .table-wrap {
          overflow-x: auto;
          border: 1px solid #1f2937;
          border-radius: 12px;
          background: #0b0f1a;
          padding: 10px;
        }
        .radar-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        .radar-table th,
        .radar-table td {
          padding: 8px 10px;
          border-bottom: 1px solid #1f2937;
          vertical-align: middle;
        }
        .radar-table th {
          text-align: left;
          color: #9ca3af;
          font-weight: 600;
          white-space: nowrap;
        }
        .radar-table td.num {
          text-align: right;
          font-variant-numeric: tabular-nums;
        }
        .cell-pos { color: #16a34a; }
        .cell-neg { color: #dc2626; }
        .cell-neutral { color: #9ca3af; }
        .z-crowded {
          color: #111827;
          background: #fef3c7;
          border-radius: 999px;
          padding: 2px 6px;
          font-weight: 700;
        }
        .z-neutral { color: #9ca3af; }
        .conflict-high { color: #dc2626; font-weight: 700; }
        .conflict-med { color: #d97706; font-weight: 700; }
        .conflict-low { color: #9ca3af; }
        .tag-chip {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 999px;
          background: #111827;
          color: #e5e7eb;
          font-size: 11px;
          margin-right: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Navigation")
        current_page = st.session_state.get("page", "market")
        if st.button("Market", type="primary" if current_page == "market" else "secondary", use_container_width=True):
            if current_page != "market":
                st.session_state["page"] = "market"
                st.rerun()
        if st.button("Overview", type="primary" if current_page == "overview" else "secondary", use_container_width=True):
            if current_page != "overview":
                st.session_state["page"] = "overview"
                st.rerun()
        if st.button("Signals", type="primary" if current_page == "signals" else "secondary", use_container_width=True):
            if current_page != "signals":
                st.session_state["page"] = "signals"
                st.rerun()

        st.markdown("---")
        st.markdown("### Filters")
        st.session_state["mr_view"] = st.radio(
            "View",
            ["Table", "Cards"],
            index=["Table", "Cards"].index(st.session_state["mr_view"]),
        )
        st.session_state["mr_hot_only"] = st.checkbox("Hot only", value=st.session_state["mr_hot_only"])
        selected_categories = st.multiselect(
            "Category",
            options=categories_present,
            default=categories_present,
        )
        st.session_state["mr_sort_by"] = st.selectbox(
            "Sort by",
            ["Hot score", "Signal", "OI risk"],
            index=["Hot score", "Signal", "OI risk"].index(st.session_state["mr_sort_by"]),
        )

        if st.button("More filters v"):
            st.session_state["mr_advanced_open"] = not st.session_state["mr_advanced_open"]

        if st.session_state["mr_advanced_open"]:
            st.markdown("#### Advanced filters")
            st.caption("Advanced filters narrow the view to very specific situations.")
            st.session_state["mr_conflict"] = st.selectbox("Conflict", ["Any", "High only"], index=["Any", "High only"].index(st.session_state["mr_conflict"]))
            st.session_state["mr_oi_risk"] = st.selectbox("OI Risk", ["Any", "Elevated+", "High only"], index=["Any", "Elevated+", "High only"].index(st.session_state["mr_oi_risk"]))
            st.session_state["mr_funds_crowding"] = st.selectbox("Funds Crowding", ["Any", "Crowded (abs Z >= 1.5)"], index=["Any", "Crowded (abs Z >= 1.5)"].index(st.session_state["mr_funds_crowding"]))
            st.session_state["mr_signal"] = st.selectbox("Signal", ["Any", "Bull (+1,+2)", "Bear (-1,-2)", "Neutral (0)"], index=["Any", "Bull (+1,+2)", "Bear (-1,-2)", "Neutral (0)"].index(st.session_state["mr_signal"]))
            st.session_state["mr_show_empty"] = st.checkbox("Show empty categories", value=st.session_state["mr_show_empty"])
            if st.button("Reset filters"):
                _reset_filters_state()
                st.rerun()

        st.markdown("---")
        st.caption(f"Version: {APP_VERSION}")

    # Summary header
    date_source = latest_date_radar
    if st.session_state.get("mr_view") == "Table" and pd.notna(latest_date_pos):
        date_source = latest_date_pos
    date_label = pd.to_datetime(date_source).strftime("%Y-%m-%d") if pd.notna(date_source) else "N/A"
    st.markdown("## Market Radar")
    st.caption(f"Report date: {date_label}")

    hot_count = int((df.get("is_hot") == True).sum()) if "is_hot" in df.columns else 0
    high_conflict = int((df.get("conflict_level") == "High").sum()) if "conflict_level" in df.columns else 0
    confirmed_imbalance = int((df.get("confirmed_imbalance") == True).sum()) if "confirmed_imbalance" in df.columns else 0
    speculative_crowding = int((df.get("funds_crowded") == True).sum()) if "funds_crowded" in df.columns else 0
    commercial_opposition = int((df.get("commercial_opposition") == True).sum()) if "commercial_opposition" in df.columns else 0
    oi_risk_elevated_high = 0
    if "oi_risk_level" in df.columns:
        oi_risk_elevated_high = int(df["oi_risk_level"].isin(["Elevated", "High"]).sum())

    hot_df = df[df.get("is_hot") == True] if "is_hot" in df.columns else df.iloc[0:0]
    conflict_df = df[df.get("conflict_level") == "High"] if "conflict_level" in df.columns else df.iloc[0:0]
    imbalance_df = df[df.get("confirmed_imbalance") == True] if "confirmed_imbalance" in df.columns else df.iloc[0:0]
    spec_df = df[df.get("funds_crowded") == True] if "funds_crowded" in df.columns else df.iloc[0:0]
    comm_opp_df = df[df.get("commercial_opposition") == True] if "commercial_opposition" in df.columns else df.iloc[0:0]
    oi_risk_df = (
        df[df.get("oi_risk_level").isin(["Elevated", "High"])]
        if "oi_risk_level" in df.columns
        else df.iloc[0:0]
    )

    st.markdown('<div class="kpi-wrap">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            f"Hot markets\n{_get_scalar_count(df, 'hot_markets_count', hot_count)}\n{_assets_line(hot_df)}",
            key="kpi_hot",
            use_container_width=True,
            type="secondary",
        ):
            _reset_filters_state()
            st.session_state["mr_hot_only"] = True
            st.rerun()
    with c2:
        if st.button(
            f"High conflict\n{_get_scalar_count(df, 'high_conflict_count', high_conflict)}\n{_assets_line(conflict_df)}",
            key="kpi_conflict",
            use_container_width=True,
            type="secondary",
            help="Number of markets where Funds and Commercials are in directional conflict (conflict level = High).",
        ):
            _reset_filters_state()
            st.session_state["mr_hot_only"] = False
            st.session_state["mr_conflict"] = "High only"
            st.rerun()
    with c3:
        if st.button(
            f"Confirmed Imbalance\n{_get_scalar_count(df, 'confirmed_imbalance_count', confirmed_imbalance)}\n{_assets_line(imbalance_df)}",
            key="kpi_imbalance",
            use_container_width=True,
            type="secondary",
            help="Markets where Funds are crowded (|Z_funds| >= 1.5) and Commercials are positioned in the opposite direction.",
        ):
            _reset_filters_state()
            st.session_state["mr_hot_only"] = False
            st.session_state["mr_confirmed_imbalance_only"] = True
            st.rerun()

    if st.session_state.get("mr_advanced_open"):
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button(
                f"Speculative Crowding\n{_get_scalar_count(df, 'speculative_crowding_count', speculative_crowding)}\n{_assets_line(spec_df)}",
                key="kpi_spec_crowding",
                use_container_width=True,
                type="secondary",
            ):
                _reset_filters_state()
                st.session_state["mr_hot_only"] = False
                st.session_state["mr_spec_crowding_only"] = True
                st.rerun()
        with a2:
            if st.button(
                f"Commercial Opposition\n{_get_scalar_count(df, 'commercial_opposition_count', commercial_opposition)}\n{_assets_line(comm_opp_df)}",
                key="kpi_comm_opp",
                use_container_width=True,
                type="secondary",
            ):
                _reset_filters_state()
                st.session_state["mr_hot_only"] = False
                st.session_state["mr_commercial_opposition_only"] = True
                st.rerun()
        with a3:
            if st.button(
                f"OI Risk Elevated/High\n{_get_scalar_count(df, 'oi_risk_elevated_high_count', oi_risk_elevated_high)}\n{_assets_line(oi_risk_df)}",
                key="kpi_oi_risk",
                use_container_width=True,
                type="secondary",
            ):
                _reset_filters_state()
                st.session_state["mr_hot_only"] = False
                st.session_state["mr_oi_risk"] = "Elevated+"
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    df_filtered = _apply_filters(df, selected_categories)
    df_filtered = _sort_df(df_filtered)

    if st.session_state["mr_view"] == "Cards" and not hot_df.empty and "hot_score" in hot_df.columns:
        top_hot = hot_df.sort_values("hot_score", ascending=False).head(3)
        st.markdown("### Top 3 Hot")
        cols = st.columns(3)
        for idx, (_, row) in enumerate(top_hot.iterrows()):
            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="top-hot-card">
                        <div class="top-hot-title">{row.get("market_name", "N/A")}</div>
                        <div class="top-hot-meta">Hot score: {row.get("hot_score", "N/A")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    if st.session_state["mr_view"] == "Table":
        df_table = df_pos.copy()
        if df_table.empty:
            st.warning("market_positioning_latest.parquet is empty.")
            return
        df_radar_filtered = _apply_filters(df, selected_categories)
        allowed_ids = df_radar_filtered.get("market_id", pd.Series()).dropna().unique().tolist()
        if allowed_ids:
            df_table = df_table[df_table["market_id"].isin(allowed_ids)]
        if selected_categories:
            df_table = df_table[df_table["category"].isin(selected_categories)]
        df_table = df_table.copy()
        df_table["_sort_val"] = pd.to_numeric(df_table.get("cot_traffic_signal"), errors="coerce").abs()
        df_table = df_table.sort_values("_sort_val", ascending=False)

        if df_table.empty:
            st.markdown(
                """
                <div class="empty-state">
                    <div style="font-weight: 700; margin-bottom: 6px;">No markets match current filters</div>
                    <div style="color: #6b7280; margin-bottom: 8px;">Try resetting to default.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Reset"):
                _reset_filters_state()
                st.rerun()
            return

        sections_html = []
        for category in df_table.get("category", pd.Series()).dropna().unique().tolist():
            df_cat = df_table[df_table["category"] == category]
            if df_cat.empty:
                continue
            rows_html = []
            for _, row in df_cat.iterrows():
                expect_text, expect_class = _expectation_label(row.get("cot_traffic_signal"))
                funds_delta = row.get("funds_net_chg_1w")
                funds_pct = row.get("funds_pct_oi_chg_1w")
                comm_delta = row.get("comm_net_chg_1w")
                comm_pct = row.get("comm_pct_oi_chg_1w")
                oi_delta = row.get("open_interest_chg_1w")
                oi_pct = row.get("open_interest_chg_1w_pct")
                funds_z = row.get("funds_z_52w")
                comm_z = row.get("comm_z_52w")

                tags = _build_tags(row)
                tags_html = "".join([f'<span class="tag-chip">{html.escape(t)}</span>' for t in tags])

                rows_html.append(
                    f"""
                    <tr>
                      <td>{html.escape(str(row.get("market_name", "N/A")))}</td>
                      <td><span class="expect-badge {expect_class}">{expect_text}</span></td>
                      <td class="num {_delta_class(funds_delta, 1000)}">{_fmt_num(funds_delta)}</td>
                      <td class="num {_delta_class(funds_pct, 0.01)}">{_fmt_pct_from_ratio(funds_pct)}</td>
                      <td class="num {_delta_class(comm_delta, 1000)}">{_fmt_num(comm_delta)}</td>
                      <td class="num {_delta_class(comm_pct, 0.01)}">{_fmt_pct_from_ratio(comm_pct)}</td>
                      <td class="num {_delta_class(oi_delta, 1000)}">{_fmt_num(oi_delta)}</td>
                      <td class="num {_delta_class(oi_pct, 0.01)}">{_fmt_pct_from_ratio(oi_pct)}</td>
                      <td class="{_conflict_class(row.get("conflict_level"))}">{html.escape(str(row.get("conflict_level", "N/A")))}</td>
                      <td class="num {_z_class(funds_z)}">{_fmt_num(funds_z, 2)}</td>
                      <td class="num {_z_class(comm_z)}">{_fmt_num(comm_z, 2)}</td>
                      <td>{tags_html}</td>
                    </tr>
                    """
                )
            section_html = f"""
            <div class="table-section">
              <div class="table-title">{html.escape(str(category))}</div>
              <div class="table-wrap">
                <table class="radar-table">
                  <thead>
                    <tr>
                      <th>Market</th>
                      <th>Expectation</th>
                      <th>Funds Delta Net (1w)</th>
                      <th>Funds %OI change</th>
                      <th>Commercials Delta Net (1w)</th>
                      <th>Commercials %OI change</th>
                      <th>OI Delta (1w)</th>
                      <th>OI % change</th>
                      <th>Conflict</th>
                      <th>Funds Z (52w)</th>
                      <th>Commercials Z (52w)</th>
                      <th>Tags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {''.join(rows_html)}
                  </tbody>
                </table>
              </div>
            </div>
            """
            sections_html.append(section_html)

        st.markdown("### Table view")
        header_cols = st.columns([1.2, 1.4, 1.2, 1.1, 1.5, 1.2, 1.1, 1.1, 0.9, 1.1, 1.2, 1.8])
        headers = [
            "Market",
            "Expectation",
            "Funds Delta Net (1w)",
            "Funds %OI change",
            "Commercials Delta Net (1w)",
            "Commercials %OI change",
            "OI Delta (1w)",
            "OI % change",
            "Conflict",
            "Funds Z (52w)",
            "Commercials Z (52w)",
            "Tags",
        ]
        for col, label in zip(header_cols, headers):
            col.markdown(f'<div class="table-header">{label}</div>', unsafe_allow_html=True)

        for category in df_table.get("category", pd.Series()).dropna().unique().tolist():
            df_cat = df_table[df_table["category"] == category]
            if df_cat.empty:
                continue
            st.markdown(f"#### {category}")
            for _, row in df_cat.iterrows():
                cols = st.columns([1.2, 1.4, 1.2, 1.1, 1.5, 1.2, 1.1, 1.1, 0.9, 1.1, 1.2, 1.8])
                expect_text, expect_class = _expectation_label(row.get("cot_traffic_signal"))
                funds_delta = row.get("funds_net_chg_1w")
                funds_pct = row.get("funds_pct_oi_chg_1w")
                comm_delta = row.get("comm_net_chg_1w")
                comm_pct = row.get("comm_pct_oi_chg_1w")
                oi_delta = row.get("open_interest_chg_1w")
                oi_pct = row.get("open_interest_chg_1w_pct")
                funds_z = row.get("funds_z_52w")
                comm_z = row.get("comm_z_52w")

                tags = _build_tags(row)
                tags_html = "".join([f'<span class="tag-chip">{html.escape(t)}</span>' for t in tags])

                with cols[0]:
                    if st.button(
                        str(row.get("market_name", "N/A")),
                        key=f"mr_table_open_{row.get('market_id')}",
                        use_container_width=True,
                    ):
                        if row.get("category"):
                            set_selected_category(row.get("category"))
                        set_selected_asset(row.get("market_id"))
                        st.session_state["page"] = "overview"
                        st.rerun()
                cols[1].markdown(
                    f'<span class="expect-badge {expect_class}">{expect_text}</span>',
                    unsafe_allow_html=True,
                )
                cols[2].markdown(
                    f'<div class="table-cell num {_delta_class(funds_delta, 1000)}">{_fmt_num(funds_delta)}</div>',
                    unsafe_allow_html=True,
                )
                cols[3].markdown(
                    f'<div class="table-cell num {_delta_class(funds_pct, 0.01)}">{_fmt_pct_from_ratio(funds_pct)}</div>',
                    unsafe_allow_html=True,
                )
                cols[4].markdown(
                    f'<div class="table-cell num {_delta_class(comm_delta, 1000)}">{_fmt_num(comm_delta)}</div>',
                    unsafe_allow_html=True,
                )
                cols[5].markdown(
                    f'<div class="table-cell num {_delta_class(comm_pct, 0.01)}">{_fmt_pct_from_ratio(comm_pct)}</div>',
                    unsafe_allow_html=True,
                )
                cols[6].markdown(
                    f'<div class="table-cell num {_delta_class(oi_delta, 1000)}">{_fmt_num(oi_delta)}</div>',
                    unsafe_allow_html=True,
                )
                cols[7].markdown(
                    f'<div class="table-cell num {_delta_class(oi_pct, 0.01)}">{_fmt_pct_from_ratio(oi_pct)}</div>',
                    unsafe_allow_html=True,
                )
                cols[8].markdown(
                    f'<div class="table-cell {_conflict_class(row.get("conflict_level"))}">{html.escape(str(row.get("conflict_level", "N/A")))}</div>',
                    unsafe_allow_html=True,
                )
                cols[9].markdown(
                    f'<div class="table-cell num {_z_class(funds_z)}">{_fmt_num(funds_z, 2)}</div>',
                    unsafe_allow_html=True,
                )
                cols[10].markdown(
                    f'<div class="table-cell num {_z_class(comm_z)}">{_fmt_num(comm_z, 2)}</div>',
                    unsafe_allow_html=True,
                )
                cols[11].markdown(tags_html, unsafe_allow_html=True)
            st.markdown("---")
        return

    if df_filtered.empty:
        pills = _active_filter_pills(categories_present, selected_categories)
        st.markdown(
            """
            <div class="empty-state">
                <div style="font-weight: 700; margin-bottom: 6px;">No markets match current filters</div>
                <div style="color: #6b7280; margin-bottom: 8px;">Try relaxing some filters or reset to default.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if pills:
            pills_html = "".join([f'<span class="filter-pill">{p}</span>' for p in pills])
            st.markdown(pills_html, unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Relax filters"):
                msg = _relax_filters(df, selected_categories)
                st.session_state["mr_relax_msg"] = msg
                st.rerun()
        with col_b:
            if st.button("Reset to default"):
                _reset_filters_state()
                st.rerun()
        return

    if st.session_state.get("mr_relax_msg"):
        st.info(st.session_state["mr_relax_msg"])

    st.markdown("---")

    base_df = df.copy()
    if selected_categories:
        base_df = base_df[base_df["category"].isin(selected_categories)]
    base_df = _apply_filters(base_df, selected_categories)
    base_df = _sort_df(base_df)

    for category in categories_present:
        df_cat = df_filtered[df_filtered["category"] == category]
        df_cat_all = base_df[base_df["category"] == category]

        if df_cat.empty and not st.session_state["mr_show_empty"]:
            continue

        st.markdown(f"### {category}")
        if df_cat.empty and st.session_state["mr_show_empty"]:
            st.caption("No markets found.")
            st.markdown("---")
            continue

        show_key = f"mr_show_all_{category}"
        if show_key not in st.session_state:
            st.session_state[show_key] = False

        df_show = df_cat_all if st.session_state[show_key] else df_cat
        df_show = _sort_df(df_show)
        limit = len(df_show) if st.session_state[show_key] else min(5, len(df_show))

        for _, row in df_show.head(limit).iterrows():
            expect_text, expect_class = _expectation_label(row.get("cot_traffic_signal"))
            tags = _build_tags(row)

            funds_delta = _fmt_k(row.get("funds_net_delta_1w"))
            funds_pct = _fmt_pct(row.get("funds_pct_oi_change"))
            comm_delta = _fmt_k(row.get("comm_net_delta_1w"))
            comm_pct = _fmt_pct(row.get("comm_pct_oi_change"))
            oi_delta = _fmt_k(row.get("open_interest_chg_1w"))
            oi_pct = _fmt_pct(row.get("open_interest_chg_1w_pct"))

            facts = (
                f"Funds: Delta Net {funds_delta} ({funds_pct}) | "
                f"Commercials: Delta Net {comm_delta} ({comm_pct}) | "
                f"OI: Delta {oi_delta} ({oi_pct})"
            )

            st.markdown('<div class="market-row">', unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    str(row.get("market_name", "N/A")),
                    key=f"mr_open_{row.get('market_id')}",
                    use_container_width=True,
                ):
                    if row.get("category"):
                        set_selected_category(row.get("category"))
                    set_selected_asset(row.get("market_id"))
                    st.session_state["page"] = "overview"
                    st.rerun()
            with col2:
                st.markdown(
                    f'<span class="expect-badge {expect_class}">{expect_text}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown(f'<div class="facts-row">{facts}</div>', unsafe_allow_html=True)
            tag_html = "".join([f'<span class="chip">{t}</span>' for t in tags])
            st.markdown(tag_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if len(df_cat_all) > 5 and not st.session_state[show_key]:
            if st.button("Show more", key=f"mr_show_more_{category}"):
                st.session_state[show_key] = True
                st.rerun()
        elif st.session_state[show_key] and len(df_cat_all) > 5:
            if st.button("Show less", key=f"mr_show_less_{category}"):
                st.session_state[show_key] = False
                st.rerun()

        st.markdown("---")
