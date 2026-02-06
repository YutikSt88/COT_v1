"""Shared UI and data helpers for terminal-style Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.common.paths import ProjectPaths
from src.compute.build_market_radar import build_market_radar_latest

# _terminal_ui.py -> pages -> app -> src -> <repo_root>
REPO_ROOT = Path(__file__).resolve().parents[3]


@st.cache_data
def load_radar_latest(path_str: str, mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(path_str)
    if df.empty:
        return df
    if "report_date" in df.columns:
        df = df.copy()
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        latest = df["report_date"].max()
        df = df[df["report_date"] == latest].copy()
    return df


@st.cache_data
def load_metrics(path_str: str, mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(path_str)
    if "report_date" in df.columns:
        df = df.copy()
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    return df


def get_compute_paths() -> tuple[Path, Path]:
    paths = ProjectPaths(REPO_ROOT)
    return paths.data / "compute" / "market_radar_latest.parquet", paths.data / "compute" / "metrics_weekly.parquet"


def load_radar_with_fallback(radar_path: Path, metrics_path: Path) -> tuple[pd.DataFrame, str]:
    """Load radar parquet; if missing, build in-memory from metrics_weekly."""
    if radar_path.exists():
        df = load_radar_latest(str(radar_path), radar_path.stat().st_mtime)
        return df, "radar"

    if metrics_path.exists():
        metrics = load_metrics(str(metrics_path), metrics_path.stat().st_mtime)
        if metrics.empty:
            return pd.DataFrame(), "metrics_empty"

        market_name_map: dict[str, str] = {}
        if "market_key" in metrics.columns:
            names = (
                metrics[["market_key"]]
                .dropna()
                .drop_duplicates()
                .assign(market_name=lambda x: x["market_key"].astype(str))
            )
            market_name_map = dict(zip(names["market_key"].astype(str), names["market_name"].astype(str)))

        radar = build_market_radar_latest(metrics, market_name_map)
        if not radar.empty and "report_date" in radar.columns:
            radar["report_date"] = pd.to_datetime(radar["report_date"], errors="coerce")
            latest = radar["report_date"].max()
            radar = radar[radar["report_date"] == latest].copy()
        return radar, "metrics_fallback"

    return pd.DataFrame(), "missing_all"


def signal_state_from_row(row: pd.Series) -> str:
    sig = pd.to_numeric(row.get("cot_traffic_signal"), errors="coerce")
    z = pd.to_numeric(row.get("net_z_52w_funds"), errors="coerce")
    oi_risk = str(row.get("oi_risk_level") or "")
    if (pd.notna(z) and abs(float(z)) >= 2.0) or oi_risk == "High":
        return "extreme"
    if pd.notna(sig) and sig >= 1:
        return "bullish"
    if pd.notna(sig) and sig <= -1:
        return "bearish"
    return "neutral"


def apply_terminal_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          --cot-bg: #0a111b;
          --cot-panel: #101b2a;
          --cot-border: #233247;
          --cot-text: #e5edf8;
          --cot-dim: #8ea0b8;
          --cot-green: #22c55e;
          --cot-red: #ef4444;
          --cot-amber: #f59e0b;
          --cot-cyan: #38bdf8;
        }

        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
          background: var(--cot-bg);
          color: var(--cot-text);
        }

        [data-testid="stSidebar"] {
          background: #0f1724;
          border-right: 1px solid var(--cot-border);
        }

        .cot-panel {
          background: var(--cot-panel);
          border: 1px solid var(--cot-border);
          border-radius: 10px;
          padding: 12px 14px;
        }

        .cot-kpi-label {
          color: var(--cot-dim);
          font-size: 12px;
          margin-bottom: 4px;
        }

        .cot-kpi-value {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: 30px;
          line-height: 1;
          font-weight: 700;
        }

        .cot-muted { color: var(--cot-dim); }

        .cot-pill {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 999px;
          background: #162235;
          border: 1px solid #253752;
          font-size: 11px;
          color: var(--cot-dim);
          margin-right: 6px;
        }

        .cot-grid-gap { margin-top: 6px; margin-bottom: 6px; }

        .stDataFrame, [data-testid="stDataFrame"] {
          border: 1px solid var(--cot-border);
          border-radius: 10px;
          overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav(current_page: str) -> None:
    with st.sidebar:
        st.markdown("### Navigation")
        for label, key in [("Dashboard", "market"), ("Market Detail", "overview"), ("Signals", "signals")]:
            if st.button(
                label,
                type="primary" if current_page == key else "secondary",
                use_container_width=True,
                key=f"nav_{key}",
            ):
                if st.session_state.get("page") != key:
                    st.session_state["page"] = key
                    st.rerun()
