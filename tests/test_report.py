import os
import shutil
from pathlib import Path

import docx
import pytest
from zn_report.config import Config, load_config
from zn_report.report import assemble_report

GOLDEN_FILES_DIR = Path(__file__).parent / "golden"
ASSETS_DIR = Path(__file__).parent / "assets"


@pytest.fixture
def sample_config() -> Config:
    """Return a sample Config object."""
    return load_config(
        {
            "title": "Test Report",
            "branding": {"footer": "Test Footer"},
        }
    )


@pytest.fixture
def sample_metrics() -> dict:
    """Return a sample metrics dictionary."""
    return {
        "version": 3,
        "metadata": {
            "source_path": "test.csv",
            "tz": "UTC",
            "start": "2023-01-01",
            "end": "2023-01-31",
            "calendar_days": 31,
            "export_row_count": 100,
            "dropped": {"opened_at": 0, "resolved_at": 0, "both": 0},
            "warnings": [],
        },
        "kpis": {
            "resolved_count": 50,
            "resolved_per_day_avg": 1.61,
            "avg_ttr_hours": 24.5,
            "open_by_state_total": 5,
        },
        "series": {},
        "tables": {
            "resolved_per_assignee": [
                ["assignee", "count"],
                ["User A", 25],
                ["User B", 25],
            ],
            "top_tags": [["tag", "count"], ["tag1", 10], ["tag2", 15]],
        },
    }


from PIL import Image


@pytest.fixture
def sample_chart_paths(tmp_path: Path) -> dict[str, Path]:
    """Create real dummy chart files and return their paths."""
    # Create a simple, valid 1x1 PNG image
    dummy_image = Image.new("RGB", (1, 1), color="red")
    dummy_chart_path = tmp_path / "dummy_chart.png"
    dummy_image.save(dummy_chart_path, "PNG")

    charts = {
        "daily_resolved_chart": tmp_path / "daily_resolved.png",
        "opened_vs_resolved_chart": tmp_path / "opened_vs_resolved.png",
    }
    for path in charts.values():
        shutil.copy(dummy_chart_path, path)
    return charts


def _verify_docx(path: Path):
    """Verify the content of the generated DOCX file."""
    doc = docx.Document(path)

    # Verify title (first paragraph should be a heading)
    title_paragraph = doc.paragraphs[0]
    assert title_paragraph.text == "Test Report"
    assert title_paragraph.style.name.startswith("Heading")

    # Verify content
    all_text = [p.text for p in doc.paragraphs]
    assert "Resolved Count: 50" in all_text
    assert "Resolved Per Assignee" in all_text

    # Verify image count
    # Note: This is a simple check. A more robust check might involve
    # iterating through block items to find all images.
    image_count = len(doc.inline_shapes)
    assert image_count == 2


def test_assemble_report(
    tmp_path: Path,
    sample_config: Config,
    sample_metrics: dict,
    sample_chart_paths: dict[str, Path],
):
    """Test the report assembly for both PDF and DOCX."""
    # Set SOURCE_DATE_EPOCH for deterministic PDF generation
    os.environ["SOURCE_DATE_EPOCH"] = "1672531200"  # 2023-01-01

    template_path = Path("templates/report.html.j2")

    # --- Test PDF Generation ---
    pdf_output_path = tmp_path / "report.pdf"
    golden_pdf_path = GOLDEN_FILES_DIR / "golden_report.pdf"

    assemble_report(
        metrics=sample_metrics,
        chart_paths=sample_chart_paths,
        config=sample_config,
        template_path=template_path,
        output_path=pdf_output_path,
    )

    assert pdf_output_path.exists()

    # Generate golden file if it doesn't exist
    if not golden_pdf_path.exists():
        GOLDEN_FILES_DIR.mkdir(exist_ok=True)
        shutil.copy(pdf_output_path, golden_pdf_path)
        pytest.skip(f"Golden file generated at {golden_pdf_path}. Re-run tests.")

    # Compare with golden file
    assert pdf_output_path.read_bytes() == golden_pdf_path.read_bytes()

    # --- Test DOCX Generation ---
    docx_output_path = tmp_path / "report.docx"
    assemble_report(
        metrics=sample_metrics,
        chart_paths=sample_chart_paths,
        config=sample_config,
        template_path=template_path,  # Not used for docx, but required
        output_path=docx_output_path,
    )

    assert docx_output_path.exists()
    _verify_docx(docx_output_path)

    del os.environ["SOURCE_DATE_EPOCH"]
