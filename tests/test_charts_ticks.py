from pathlib import Path
from unittest.mock import MagicMock, patch

from zn_report.charts import render_charts
from zn_report.config import Config, Branding, Style, Layout, Palette
import pytest


@pytest.fixture
def sample_config() -> Config:
    """Provides a default Config object for testing."""
    return Config(
        title="Test Report",
        branding=Branding(logo_path=None, footer="Test Footer"),
        style=Style(
            palette=Palette(
                primary="#000000",
                secondary="#444444",
                accent="#ff0000",
                muted="#888888",
                categorical=["#ff0000", "#00ff00", "#0000ff"],
            ),
            font_family="sans-serif",
        ),
        layout=Layout(show_resolution_codes_chart=True, show_top_tags_chart=True),
    )


@patch("zn_report.charts.plt")
def test_date_axis_formatter(mock_plt, sample_config):
    """Verify that date-based charts have the correct date formatter set."""
    # 1. Setup mock data for all charts to ensure the render loop runs
    metrics = {
        "series": {
            "resolved_per_day": [{"date": "2023-01-01", "count": 1}],
            "opened_vs_resolved": {
                "dates": ["2023-01-01"],
                "opened": [1],
                "resolved": [1],
            },
        },
        "kpis": {"open_by_state": {"New": 1}},
        "tables": {
            "resolved_by_assignee": [{"assignee": "A", "count": 1}],
            "top_5_tags": [{"tag": "T", "count": 1}],
        },
    }
    out_dir = Path("/tmp/charts_test")

    # We need to track formatter calls per-axis object
    ax_mocks = []

    def subplots_side_effect(*args, **kwargs):
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        # Store the formatter object itself to inspect its attributes later
        ax_mock.xaxis.set_major_formatter.side_effect = lambda f: setattr(
            ax_mock, "_formatter_obj", f
        )
        ax_mocks.append(ax_mock)
        return fig_mock, ax_mock

    mock_plt.subplots.side_effect = subplots_side_effect

    # 2. Call the function
    render_charts(metrics, sample_config.style, out_dir)

    # 3. Assertions
    # Find the axes corresponding to the date-based charts
    resolved_per_day_ax = ax_mocks[0]  # Based on order in render_charts
    opened_vs_resolved_ax = ax_mocks[1]
    resolved_by_assignee_ax = ax_mocks[2]
    top_5_tags_ax = ax_mocks[3]

    # Check that the formatter was called on the correct axes
    assert resolved_per_day_ax.xaxis.set_major_formatter.call_count == 1
    assert opened_vs_resolved_ax.xaxis.set_major_formatter.call_count == 1

    # Check the format string passed to the formatter
    formatter1 = resolved_per_day_ax.xaxis.set_major_formatter.call_args[0][0]
    assert formatter1.fmt == "%Y-%m-%d"

    formatter2 = opened_vs_resolved_ax.xaxis.set_major_formatter.call_args[0][0]
    assert formatter2.fmt == "%Y-%m-%d"

    # Check that other charts were not affected
    assert resolved_by_assignee_ax.xaxis.set_major_formatter.call_count == 0
    assert top_5_tags_ax.xaxis.set_major_formatter.call_count == 0
