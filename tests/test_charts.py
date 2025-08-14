"""Tests for the chart generation module."""

import hashlib
import pytest
import pandas as pd
from pathlib import Path

from zn_report.charts import render_charts
from zn_report.config import Palette, Style
from zn_report.metrics import compute_metrics

# Golden file directory
GOLDEN_DIR = Path(__file__).parent / "golden"

def get_file_hash(path: Path) -> str:
    """Computes the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def check_golden_file(generated_path: Path, test_name: str):
    """
    Checks a generated file against its golden file version.

    If the golden file does not exist, it's created.
    """
    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / f"{test_name}.png.sha256"

    generated_hash = get_file_hash(generated_path)

    if not golden_path.exists():
        golden_path.write_text(generated_hash)
        pytest.skip(f"Golden file '{golden_path.name}' created. Please review and commit.")

    expected_hash = golden_path.read_text().strip()
    assert generated_hash == expected_hash, f"Hash mismatch for {test_name}"

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
        "open_by_state",
        "resolved_by_assignee",
        "top_5_tags",
    }
    assert set(result_paths.keys()) == expected_chart_ids

    for chart_id, file_path in result_paths.items():
        assert file_path.exists()
        assert file_path.stat().st_size > 0
        check_golden_file(file_path, f"chart_{chart_id}")

def test_render_charts_with_empty_data(chart_style: Style, tmp_path: Path):
    """
    Test that render_charts runs gracefully with empty metrics.
    Verifies that placeholder/empty charts are created without errors.
    """
    empty_df = pd.DataFrame(columns=["opened_at", "resolved_at", "state", "sys_tags", "assigned_to", "close_code", "u_original_assignment_group"])
    empty_metrics = compute_metrics(empty_df, start="2025-01-01", end="2025-01-31", tz="UTC")

    # Act
    result_paths = render_charts(empty_metrics, chart_style, tmp_path)

    # Assert
    # We expect all charts defined in charts.py to be generated, even if empty
    assert len(result_paths) == 5
    for file_path in result_paths.values():
        assert file_path.exists()
        # We don't check the hash for empty charts, just that they are created
        assert file_path.stat().st_size > 0
