"""Tests for the chart generation module."""

from __future__ import annotations

from pathlib import Path

import pytest

from zn_report.charts import render_charts
from zn_report.config import Palette, Style


@pytest.fixture
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


@pytest.fixture
def sample_metrics() -> dict:
    """Provides a sample metrics dictionary for chart generation tests."""
    return {
        "series": {
            "resolved_per_day": [
                {"date": "2025-07-15", "count": 5},
                {"date": "2025-07-16", "count": 8},
            ],
            "opened_vs_resolved": {
                "dates": ["2025-07-15", "2025-07-16"],
                "opened": [10, 12],
                "resolved": [5, 8],
            },
        },
        "kpis": {
            "open_by_state": {"New": 10, "In Progress": 5, "On Hold": 2},
        },
        "tables": {
            "resolved_by_assignee": [
                {"assignee": "Agent Smith", "count": 25},
                {"assignee": "Agent Brown", "count": 15},
            ],
            "top_5_tags": [
                {"tag": "tag-a", "count": 50},
                {"tag": "tag-b", "count": 40},
                {"tag": "tag-c", "count": 30},
            ],
        },
    }


def test_render_charts_smoke(
    sample_metrics: dict, chart_style: Style, tmp_path: Path
) -> None:
    """
    Smoke test for render_charts.

    Verifies that the function runs without errors, creates the expected files,
    and returns the correct dictionary structure.
    """
    # Act
    result_paths = render_charts(sample_metrics, chart_style, tmp_path)

    # Assert
    # 1. Check return type and keys
    assert isinstance(result_paths, dict)
    expected_chart_ids = {
        "resolved_per_day",
        "opened_vs_resolved",
        "open_by_state",
        "resolved_by_assignee",
        "top_5_tags",
    }
    assert set(result_paths.keys()) == expected_chart_ids

    # 2. Check that files were created
    for chart_id, file_path in result_paths.items():
        assert isinstance(file_path, Path)
        assert file_path.name == f"{chart_id}.png"
        assert file_path.exists()
        assert file_path.is_file()
        # Check that file is not empty
        assert file_path.stat().st_size > 0


def test_render_charts_with_empty_data(chart_style: Style, tmp_path: Path) -> None:
    """
    Test that render_charts runs gracefully with empty metrics.

    Verifies that placeholder/empty charts are created without errors.
    """
    empty_metrics = {
        "series": {"resolved_per_day": [], "opened_vs_resolved": {}},
        "kpis": {"open_by_state": {}},
        "tables": {"resolved_by_assignee": [], "top_5_tags": []},
    }

    # Act
    result_paths = render_charts(empty_metrics, chart_style, tmp_path)

    # Assert
    assert len(result_paths) == 5
    for file_path in result_paths.values():
        assert file_path.exists()
        assert file_path.stat().st_size > 0
