import subprocess
import sys
from pathlib import Path

import pytest
from zn_report.cli import cli_main
from zn_report.exceptions import FileIOError

# Path to the sample data
DATA_DIR = Path(__file__).parent / "data"
VALID_CSV = DATA_DIR / "sample_incidents.csv"


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Helper to run the CLI tool."""
    command = [sys.executable, "-m", "zn_report.cli"] + args
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_cli_successful_run(tmp_path):
    """Test a successful run of the CLI that produces a report."""
    output_pdf = tmp_path / "report.pdf"
    args = [
        "--csv",
        str(VALID_CSV),
        "--start",
        "2025-07-01",
        "--end",
        "2025-07-31",
        "--out",
        str(output_pdf),
    ]

    result = run_cli(args)

    assert (
        result.returncode == 0
    ), f"CLI should exit with 0 on success. Stdout: {result.stdout}"
    assert output_pdf.exists(), "The report file should be created."

    # Check for key success messages in stdout
    stdout = result.stdout
    assert "Loaded 3 rows" in stdout
    assert "Metrics: resolved=2" in stdout
    assert f"Report written to {output_pdf}" in stdout


def test_cli_invalid_date_range():
    """Test that the CLI exits with code 2 for an invalid date range."""
    args = [
        "--csv",
        str(VALID_CSV),
        "--start",
        "2025-08-01",
        "--end",
        "2025-07-31",
    ]

    result = run_cli(args)

    assert result.returncode == 2
    assert (
        "Start date (2025-08-01) cannot be after end date (2025-07-31)" in result.stdout
    )


def test_cli_csv_not_found():
    """Test that the CLI exits with code 5 if the CSV file is not found."""
    non_existent_csv = "non_existent_file.csv"
    args = [
        "--csv",
        non_existent_csv,
        "--start",
        "2025-07-01",
        "--end",
        "2025-07-31",
    ]

    result = run_cli(args)

    assert result.returncode == 5
    assert f"CSV file not found at '{non_existent_csv}'" in result.stdout


def test_cli_missing_headers():
    """Test that the CLI exits with code 2 if the CSV is missing headers."""
    missing_header_csv = DATA_DIR / "missing_header.csv"
    args = [
        "--csv",
        str(missing_header_csv),
        "--start",
        "2025-07-01",
        "--end",
        "2025-07-31",
    ]

    result = run_cli(args)

    assert result.returncode == 2
    assert "Missing required headers" in result.stdout


def test_cli_all_rows_dropped():
    """Test that the CLI exits with code 3 if all rows are unusable."""
    all_bad_dates_csv = DATA_DIR / "all_bad_dates.csv"
    args = [
        "--csv",
        str(all_bad_dates_csv),
        "--start",
        "2025-07-01",
        "--end",
        "2025-07-31",
    ]

    result = run_cli(args)

    assert result.returncode == 3
    assert "All rows were dropped after date parsing" in result.stdout


def test_cli_render_failure(monkeypatch, caplog):
    """Test that the CLI exits with code 4 on a rendering failure."""

    # Simulate an error during the report assembly phase
    def mock_assemble_report(*args, **kwargs):
        raise ValueError("Simulated rendering error")

    monkeypatch.setattr("zn_report.report.assemble_report", mock_assemble_report)

    # Patch sys.argv to simulate CLI arguments
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zn-report",
            "--csv",
            str(VALID_CSV),
            "--start",
            "2025-07-01",
            "--end",
            "2025-07-31",
        ],
    )

    # The app calls sys.exit(), which raises SystemExit.
    # We catch it and check the exit code.
    with pytest.raises(SystemExit) as e:
        cli_main()

    assert e.type == SystemExit
    assert e.value.code == 4

    # Check that the error message was logged
    assert (
        "Error during report rendering/assembly: Simulated rendering error"
        in caplog.text
    )


def test_cli_io_error_during_processing(monkeypatch, caplog):
    """Test that the CLI exits with code 5 on an I/O error during processing."""

    # This tests a more subtle I/O error than a simple file-not-found.
    # We mock the underlying pandas reader to raise an error during iteration.
    def mock_read_csv(*args, **kwargs):
        # Simulate a generic I/O error
        raise FileIOError("Simulated read error")

    monkeypatch.setattr("zn_report.io_loader.load_csv", mock_read_csv)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zn-report",
            "--csv",
            str(VALID_CSV),  # File exists, but will fail during read
            "--start",
            "2025-07-01",
            "--end",
            "2025-07-31",
        ],
    )

    with pytest.raises(SystemExit) as e:
        cli_main()

    assert e.type == SystemExit
    assert e.value.code == 5
    assert "Simulated read error" in caplog.text
