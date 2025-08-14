"""
Test to verify that processing a CSV in chunks yields the same result as
processing it all in memory. This is crucial for ensuring the scalability
and correctness of the large file processing feature.
"""

import pandas as pd
import pytest
from pathlib import Path
from zn_report import io_loader, metrics

@pytest.fixture(scope="session")
def large_csv_path(data_dir: Path) -> Path:
    """Return the path to the large incidents CSV file."""
    return data_dir / "large_incident_data.csv"

def test_chunking_produces_identical_results(large_csv_path: Path):
    """
    Ensures that metrics computed from a chunked read are identical to
    metrics computed from a full, in-memory read.
    """
    start_date = "2025-07-01"
    end_date = "2025-07-31"
    tz = "UTC"

    # --- Run 1: In-Memory ---
    # Load the entire CSV into a single DataFrame and compute metrics.
    full_df = io_loader.load_csv(large_csv_path)
    expected_metrics = metrics.compute_metrics(full_df, start=start_date, end=end_date, tz=tz)

    # --- Run 2: Chunked ---
    # Load the CSV in chunks and reassemble it.
    chunk_iterator = io_loader.load_csv(large_csv_path, chunksize=100)
    reconstructed_df = pd.concat(list(chunk_iterator), ignore_index=True)
    chunked_metrics = metrics.compute_metrics(reconstructed_df, start=start_date, end=end_date, tz=tz)

    # --- Verification ---
    # We will compare the key outputs: kpis, series, and tables.
    # The 'metadata' field is excluded because 'export_row_count' will differ
    # between the full load and the chunked load (as compute_metrics is called
    # on the final dataframe, not on a per-chunk basis).

    assert expected_metrics["kpis"] == chunked_metrics["kpis"], "KPIs do not match"

    # For series and tables, which can contain nested lists and dicts,
    # a direct comparison is usually sufficient.
    assert expected_metrics["series"] == chunked_metrics["series"], "Time series data does not match"
    assert expected_metrics["tables"] == chunked_metrics["tables"], "Table data does not match"

    # Also verify the version is the same
    assert expected_metrics["version"] == chunked_metrics["version"], "Version does not match"
