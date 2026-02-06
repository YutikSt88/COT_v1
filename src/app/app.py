"""Main Streamlit app entry point (imported by app.py)."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st
from src.app.auth import require_authentication, render_auth_sidebar


def main() -> None:
    """Run the Streamlit app."""
    # Ensure repo root is on sys.path so "import src.*" works under Streamlit.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # CRITICAL: set_page_config MUST be the FIRST Streamlit command
    st.set_page_config(
        page_title="COT Dashboard",
        page_icon="COT",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Hide Streamlit multipage menu (if auto-detected) - we use custom navigation
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not require_authentication():
        st.stop()

    render_auth_sidebar()

    # Deterministic routing: use only st.session_state["page"]
    if "page" not in st.session_state:
        st.session_state["page"] = "market"

    page = st.session_state.get("page", "market")

    try:
        current_page = page

        if current_page not in ["market", "overview", "signals"]:
            st.error(f"Unknown page: '{current_page}'")
            st.write("Expected pages: market, overview, signals")
            st.write(f"Resolved page: {page}")
            st.warning("Resetting to 'market'. Refresh to apply.")
            st.session_state["page"] = "market"
            st.stop()

        if current_page == "overview":
            from src.app.pages.overview_mvp import render as render_overview_mvp
            render_overview_mvp()
        elif current_page == "market":
            from src.app.pages.market import render as render_market
            render_market()
        elif current_page == "signals":
            from src.app.pages.signals import render as render_signals
            render_signals()
        else:
            st.error(f"Unknown page: '{current_page}'")
            st.write("Expected pages: market, overview, signals")
            st.write(f"Resolved page: {page}")
            st.stop()
    except Exception as e:
        st.error("Error loading page")
        st.exception(e)

        st.code(traceback.format_exc(), language="python")

        print("=" * 80)
        print(f"ERROR: Failed to load page '{page}'")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80)

        with st.expander("Debug Information", expanded=True):
            st.write("**Exception Type:**", type(e).__name__)
            st.write("**Exception Message:**", str(e))
            st.write("**Current Page:**", page)
            st.write("**Session State Keys:**", list(st.session_state.keys()))

            selected_category = st.session_state.get("selected_category")
            selected_asset = st.session_state.get("selected_asset")
            st.write("**Selected Category:**", selected_category)
            st.write("**Selected Asset:**", selected_asset)

            root = Path(".").resolve()
            metrics_path = root / "data" / "compute" / "metrics_weekly.parquet"
            st.write("**metrics_weekly.parquet exists:**", metrics_path.exists())
            if metrics_path.exists():
                st.write("**metrics_weekly.parquet path:**", str(metrics_path))

        st.stop()


if __name__ == "__main__":
    main()
