from unittest.mock import MagicMock, patch

import pytest
from zn_report.report import _create_docx_report
from zn_report.config import Config, Branding, Style, Layout, Palette


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


@pytest.fixture
def mock_docx():
    """Fixture to mock the entire docx library."""
    with patch("zn_report.report.docx") as mock_docx_lib:
        # Basic setup for a mock document and table
        mock_document = MagicMock()
        mock_table = MagicMock()

        # When a document is created, return our mock
        mock_docx_lib.Document.return_value = mock_document
        # When a table is added, return our mock
        mock_document.add_table.return_value = mock_table

        # Mock cell text access
        def get_mock_cell(row, col):
            cell = MagicMock()
            cell.text = ""
            return cell

        mock_table.cell.side_effect = get_mock_cell

        # Capture the number of columns when add_table is called
        num_cols = 0

        def add_table_side_effect(rows, cols):
            nonlocal num_cols
            num_cols = cols
            return mock_table

        mock_document.add_table.side_effect = add_table_side_effect

        # Mock row creation and cell access within rows
        mock_rows = []

        def add_row():
            row = MagicMock()
            # Use the captured number of columns
            row.cells = [MagicMock() for _ in range(num_cols)]
            for cell in row.cells:
                # Make paragraph and run accessible for bolding
                run = MagicMock()
                run.bold = False  # Default to not bold
                para = MagicMock()
                para.runs = [run]
                cell.paragraphs = [para]

                # Allow direct text setting on cell and run
                def set_text(c, val):
                    c._text = val
                    run.text = val

                cell.text = ""
                type(cell).text = property(lambda c: c._text, set_text)

            mock_rows.append(row)
            return row

        mock_table.add_row.side_effect = add_row

        yield mock_docx_lib, mock_table, mock_rows


def test_docx_table_render_with_total(mock_docx, sample_config):
    """Verify DOCX table rendering for list[dict] with a 'count' column."""
    mock_docx_lib, mock_table, mock_rows = mock_docx

    metrics = {
        "tables": {
            "my_table": [
                {"name": "A", "count": 10},
                {"name": "B", "count": 20},
            ]
        }
    }

    _create_docx_report(metrics, {}, sample_config)

    # 2 data rows + 1 total row
    assert mock_table.add_row.call_count == 3

    # Check total row content
    total_row = mock_rows[-1]
    assert total_row.cells[0].text == "Total"
    assert total_row.cells[1].text == "30"
    # Check bolding
    assert total_row.cells[0].paragraphs[0].runs[0].bold is True
    assert total_row.cells[1].paragraphs[0].runs[0].bold is True


def test_docx_table_render_no_total(mock_docx, sample_config):
    """Verify DOCX table rendering for list[dict] without a 'count' column."""
    mock_docx_lib, mock_table, mock_rows = mock_docx

    metrics = {
        "tables": {
            "my_table": [
                {"name": "A", "value": 10},
                {"name": "B", "value": 20},
            ]
        }
    }

    _create_docx_report(metrics, {}, sample_config)

    # 2 data rows, no total row
    assert mock_table.add_row.call_count == 2
