"""Overview sections: modular UI components for overview page."""

from src.app.pages.overview_sections.common import (
    fmt_num,
    fmt_delta,
    fmt_delta_colored,
    create_sparkline,
    get_13w_net_data,
    render_heatline_html,
    inject_shared_css,
    inject_snapshot_css,
    inject_extremes_css,
)
from src.app.pages.overview_sections.snapshot import render_snapshot, render_flow_rotation_section, render_funds_vs_commercials, render_funds_vs_commercials_header
from src.app.pages.overview_sections.extremes import render_extremes, render_extremes_header
from src.app.pages.overview_sections.moves import render_moves, render_moves_header
from src.app.pages.overview_sections.charts import render_charts
from src.app.pages.overview_sections.tables import render_tables

__all__ = [
    "fmt_num",
    "fmt_delta",
    "fmt_delta_colored",
    "create_sparkline",
    "get_13w_net_data",
    "render_heatline_html",
    "inject_shared_css",
    "inject_snapshot_css",
    "inject_extremes_css",
    "render_snapshot",
    "render_flow_rotation_section",
    "render_funds_vs_commercials",
    "render_funds_vs_commercials_header",
    "render_extremes",
    "render_extremes_header",
    "render_moves",
    "render_moves_header",
    "render_charts",
    "render_tables",
]
