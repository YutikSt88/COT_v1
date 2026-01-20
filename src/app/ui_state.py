"""UI state management for Streamlit app."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.common.paths import ProjectPaths

# Version constant (single source of truth)
APP_VERSION = "COT_v1.2.8"


def get_project_paths():
    """Get project paths (cached)."""
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(root)


@st.cache_data
def load_markets_config():
    """Load markets.yaml config (cached)."""
    paths = get_project_paths()
    config_path = paths.configs / "markets.yaml"
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@st.cache_data
def get_categories_and_markets():
    """Get categories and markets grouped by category."""
    config = load_markets_config()
    if config is None:
        return [], {}
    
    markets = config.get("markets", [])
    categories = sorted(set(m.get("category") for m in markets if m.get("category")))
    category_to_markets = {}
    for market in markets:
        category = market.get("category")
        if category:
            if category not in category_to_markets:
                category_to_markets[category] = []
            category_to_markets[category].append(market)
    return categories, category_to_markets


def initialize_selection_defaults():
    """Initialize selection defaults if not set."""
    categories, category_to_markets = get_categories_and_markets()
    
    if not categories:
        return
    
    # Initialize category if not set
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = categories[0]
    
    # Initialize asset if not set or invalid
    selected_category = st.session_state.get("selected_category")
    if selected_category and selected_category in category_to_markets:
        markets_in_category = category_to_markets[selected_category]
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
        
        if market_options:
            current_asset = st.session_state.get("selected_asset")
            # If current asset is not in the category, pick first available
            if not current_asset or current_asset not in market_options:
                st.session_state["selected_asset"] = market_options[0]
        else:
            st.session_state["selected_asset"] = None
    else:
        st.session_state["selected_asset"] = None


def get_selected_category() -> str | None:
    """Get selected category from session state."""
    initialize_selection_defaults()
    return st.session_state.get("selected_category")


def set_selected_category(category: str) -> None:
    """Set selected category in session state."""
    st.session_state["selected_category"] = category
    # Reset asset when category changes
    categories, category_to_markets = get_categories_and_markets()
    if category in category_to_markets:
        markets_in_category = category_to_markets[category]
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
        if market_options:
            st.session_state["selected_asset"] = market_options[0]
        else:
            st.session_state["selected_asset"] = None


def get_selected_asset() -> str | None:
    """Get selected asset (market_key) from session state."""
    initialize_selection_defaults()
    return st.session_state.get("selected_asset")


def set_selected_asset(asset: str) -> None:
    """Set selected asset (market_key) in session state."""
    st.session_state["selected_asset"] = asset


# Legacy alias for compatibility
def get_selected_market_key() -> str | None:
    """Get selected market_key (alias for get_selected_asset)."""
    return get_selected_asset()


def set_selected_market_key(market_key: str) -> None:
    """Set selected market_key (alias for set_selected_asset)."""
    set_selected_asset(market_key)


def render_sidebar(current_page: str = "market") -> None:
    """Render sidebar with page navigation, category/asset selection.
    
    Args:
        current_page: Current page name ("market", "overview", etc.) - used for page button highlighting
    """
    categories, category_to_markets = get_categories_and_markets()
    
    if not categories:
        st.sidebar.warning("No markets configured (markets.yaml).")
        return
    
    with st.sidebar:
        # Page navigation: custom buttons with visual highlighting (no "Pages" header)
        page_options = ["Market", "Overview"]
        page_mapping = {"Market": "market", "Overview": "overview"}
        
        # Get current page display name
        current_page_display = "Market" if current_page == "market" else "Overview"
        
        # Inject custom CSS for selected button styling (bold + blue color)
        st.markdown("""
        <style>
        button[data-testid*="page_btn_"][kind="primary"] {
            font-weight: bold !important;
            background-color: #1f77b4 !important;
            border-color: #1f77b4 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Render page buttons with custom styling
        for page_display in page_options:
            is_selected = (page_display == current_page_display)
            page_key = page_mapping[page_display]
            
            # Custom styling: selected page gets primary button (blue + bold via CSS)
            if is_selected:
                # Selected: primary button (will be styled bold + blue via CSS)
                button_type = "primary"
            else:
                # Not selected: secondary button (gray)
                button_type = "secondary"
            
            if st.button(page_display, key=f"page_btn_{page_key}", type=button_type, use_container_width=True):
                if not is_selected:
                    st.session_state["page"] = page_key
                    st.rerun()
        
        st.markdown("---")
        
        # Initialize defaults (only if not set)
        initialize_selection_defaults()
        
        # Get current values from session state (before selectbox)
        prev_category = st.session_state.get("selected_category")
        
        # Category selection - NO on_change, NO automatic rerun
        category_index = categories.index(prev_category) if prev_category and prev_category in categories else 0
        
        selected_category = st.selectbox(
            "Category",
            options=categories,
            index=category_index if categories else None,
            key="sidebar_category_select",
        )
        
        # Store category in our session state key (sync with selectbox key)
        st.session_state["selected_category"] = selected_category
        
        # Asset selection (filtered by category) - NO on_change, NO automatic rerun
        markets_in_category = category_to_markets.get(selected_category, [])
        market_options = [m.get("market_key") for m in markets_in_category if m.get("market_key")]
        
        # SAFE: Reset asset ONLY if category changed AND asset is invalid for new category
        if selected_category != prev_category:
            # Category changed - reset asset to first available
            if market_options:
                st.session_state["selected_asset"] = market_options[0]
            else:
                st.session_state["selected_asset"] = None
        else:
            # Category unchanged - validate current asset is still valid
            current_asset = st.session_state.get("selected_asset")
            if market_options:
                if current_asset and current_asset not in market_options:
                    # Asset invalid for current category - reset to first
                    st.session_state["selected_asset"] = market_options[0]
            else:
                st.session_state["selected_asset"] = None
        
        # Now render asset selectbox with validated state
        if market_options:
            current_asset = st.session_state.get("selected_asset")
            # Ensure current_asset is in options (safety check)
            if current_asset not in market_options:
                current_asset = market_options[0]
                st.session_state["selected_asset"] = current_asset
            
            asset_index = market_options.index(current_asset) if current_asset in market_options else 0
            
            selected_asset = st.selectbox(
                "Asset",
                options=market_options,
                index=asset_index,
                key="sidebar_asset_select",
            )
            
            # Store asset in our session state key (sync with selectbox key)
            st.session_state["selected_asset"] = selected_asset
        else:
            st.session_state["selected_asset"] = None
        
        # Version removed from here - it's displayed in overview_mvp.py at the bottom
        
