import pandas as pd
import pytest
from zn_report.metrics import compute_metrics


@pytest.mark.parametrize(
    "ttr_hours, expected",
    [
        (10.5, 11),  # Test half-up rounding
        (10.4, 10),  # Test rounding down
        (10.6, 11),  # Test rounding up
        (10.0, 10),  # Test whole number
        (pd.NA, 0),  # Test handling of NA
        (float("nan"), 0),  # Test handling of NaN
    ],
)
def test_avg_ttr_rounding_and_nan(ttr_hours, expected):
    """Verify avg_ttr_hours rounding and NaN handling."""
    # Create a minimal DataFrame for testing
    data = {
        "opened_at": ["2023-01-01 12:00:00"],
        "resolved_at": ["2023-01-01 12:00:00"],  # Placeholder, will be overwritten
    }
    df = pd.DataFrame(data)
    df["opened_at"] = pd.to_datetime(df["opened_at"])

    if pd.isna(ttr_hours):
        # Create a case that results in NaN mean by having no resolved tickets in window
        df["resolved_at"] = pd.to_datetime(["2024-01-01 12:00:00"])
    else:
        # Set the TTR delta to the desired value in hours
        df["resolved_at"] = df["opened_at"] + pd.to_timedelta(ttr_hours, unit="h")

    metrics = compute_metrics(df, start="2023-01-01", end="2023-01-02", tz="UTC")
    assert metrics["kpis"]["avg_ttr_hours"] == expected
