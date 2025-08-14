import pandas as pd
from zn_report.metrics import compute_metrics


def test_open_by_state_processing():
    """Verify 'open_by_state' sorting, percentage, and KPI structure."""
    data = {
        "state": [
            "New",
            "New",
            "New",
            "New",
            "In Progress",
            "In Progress",
            "On Hold",
            "On Hold",
            "On Hold",
            "Resolved",  # This should be ignored
            "New",  # To make New 5, In Progress 2, On Hold 3
        ],
        # No resolved_at for these tickets, so they are considered open
        "resolved_at": [pd.NaT] * 11,
        "opened_at": ["2023-01-01 12:00:00"] * 11,
    }
    df = pd.DataFrame(data)

    metrics = compute_metrics(df, start="2023-01-01", end="2023-01-02", tz="UTC")

    # 1. Verify 'open_by_state' is NOT in kpis
    assert "open_by_state" not in metrics["kpis"]
    assert "Total Open Tickets" in metrics["kpis"]
    # Open states are New, In Progress, On Hold. "Resolved" state is ignored.
    # Total = 5 (New) + 2 (In Progress) + 3 (On Hold) = 10
    assert metrics["kpis"]["Total Open Tickets"] == 10

    # 2. Verify the table data is sorted correctly and has percentages
    table_data = metrics["tables"]["open_by_state"]

    # Expected order: New (5), On Hold (3), In Progress (2)
    expected_order = ["New", "On Hold", "In Progress"]
    actual_order = [d["state"] for d in table_data]
    assert actual_order == expected_order

    # 3. Verify percentage calculation
    # New: 5/10 = 50.0%
    # On Hold: 3/10 = 30.0%
    # In Progress: 2/10 = 20.0%
    assert table_data[0]["percent"] == 50.0
    assert table_data[1]["percent"] == 30.0
    assert table_data[2]["percent"] == 20.0


def test_open_by_state_empty():
    """Verify behavior with no open tickets."""
    data = {
        "state": ["Resolved", "Resolved"],
        "resolved_at": ["2023-01-01 12:00:00"] * 2,
        "opened_at": ["2023-01-01 12:00:00"] * 2,
    }
    df = pd.DataFrame(data)
    metrics = compute_metrics(df, start="2023-01-01", end="2023-01-02", tz="UTC")

    assert metrics["kpis"]["Total Open Tickets"] == 0
    assert not metrics["tables"]["open_by_state"]  # Should be an empty list
