"""Tests for the chart generation module."""

import pytest
import pandas as pd
from pathlib import Path

from zn_report.charts import render_charts
from zn_report.config import Palette, Style
from zn_report.metrics import compute_metrics
from tests.helpers import check_golden_file_hash


@pytest.fixture(scope="session")
def chart_style() -> Style:
    """Provides a default Style object for tests."""
    return Style(
        font_family="sans-serif",
        palette=Palette(
            primary="#000000",
            secondary="#444444",
            accent="#ff0000",
            muted="#888888",
            categorical=["#ff0000", "#00ff00", "#0000ff"],
        ),
    )


@pytest.fixture(scope="session")
def processed_metrics(shared_df: pd.DataFrame) -> dict:
    """
    Provides a sample metrics dictionary derived from the shared DataFrame.
    This ensures the chart data is based on a realistic, shared fixture.
    """
    return compute_metrics(shared_df, start="2025-07-01", end="2025-07-31", tz="UTC")


def test_render_charts_golden(
    processed_metrics: dict, chart_style: Style, tmp_path: Path
):
    """
    Golden file test for render_charts.

    Verifies that the function generates charts that match their golden versions.
    """
    # Act
    result_paths = render_charts(processed_metrics, chart_style, tmp_path)

    # Assert
    # This set must match the keys in the `chart_definitions` dict in charts.py
    expected_chart_ids = {
        "resolved_per_day",
        "opened_vs_resolved",
        "resolved_by_assignee",
        "top_5_tags",
    }
    assert set(result_paths.keys()) == expected_chart_ids

    for chart_id, file_path in result_paths.items():
        assert file_path.exists()
        assert file_path.stat().st_size > 0
        # The test name for the golden file should not include the extension
        check_golden_file_hash(file_path, f"chart_{chart_id}.png")


def test_render_charts_with_empty_data(chart_style: Style, tmp_path: Path):
    """
    Test that render_charts runs gracefully with empty metrics.
    Verifies that placeholder/empty charts are created without errors.
    """
    empty_df = pd.DataFrame(
        columns=[
            "opened_at",
            "resolved_at",
            "state",
            "sys_tags",
            "assigned_to",
            "close_code",
            "u_original_assignment_group",
        ]
    )
    empty_metrics = compute_metrics(
        empty_df, start="2025-01-01", end="2025-01-31", tz="UTC"
    )

    # Act
    result_paths = render_charts(empty_metrics, chart_style, tmp_path)

    # Assert
    # We expect all charts defined in charts.py to be generated, even if empty
    assert len(result_paths) == 4
    for file_path in result_paths.values():
        assert file_path.exists()
        # We don't check the hash for empty charts, just that they are created
        assert file_path.stat().st_size > 0
