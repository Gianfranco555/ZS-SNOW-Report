import pytest
import pandas as pd

from zn_report.metrics import compute_metrics


@pytest.fixture(scope="module")
def sample_ticket_df() -> pd.DataFrame:
    """Provides a comprehensive sample DataFrame for testing metrics."""
    data = [
        # 8 tickets resolved within the window (July 15-17)
        {
            "opened_at": "2025-07-14 10:00",
            "resolved_at": "2025-07-15 12:00",
            "state": "Resolved",
            "assigned_to": "Alice",
            "sys_tags": "foo, bar",
            "close_code": "Solved",
            "u_original_assignment_group": "dvn-global-zscaler-operations",
        },
        {
            "opened_at": "2025-07-15 08:00",
            "resolved_at": "2025-07-16 10:00",
            "state": "Resolved",
            "assigned_to": "Bob",
            "sys_tags": "baz; foo",
            "close_code": "Solved Remotely",
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-16 11:00",
            "resolved_at": "2025-07-16 14:00",
            "state": "Resolved",
            "assigned_to": "Alice",
            "sys_tags": "FOO|bar",
            "close_code": "Solved",
            "u_original_assignment_group": "DVN-Global-Zscaler-Operations",
        },
        {
            "opened_at": "2025-07-17 09:00",
            "resolved_at": "2025-07-17 23:50",
            "state": "Resolved",
            "assigned_to": "Charlie",
            "sys_tags": "dup, foo, dup",
            "close_code": "Not Applicable",
            "u_original_assignment_group": pd.NA,
        },
        {
            "opened_at": "2025-07-15 10:00",
            "resolved_at": "2025-07-15 10:00",
            "state": "Resolved",
            "assigned_to": "Bob",
            "sys_tags": "foo; foo",
            "close_code": "",
            "u_original_assignment_group": "Some Other Team",
        },
        {
            "opened_at": "2025-07-15 10:00",
            "resolved_at": "2025-07-16 10:00",
            "state": "Resolved",
            "assigned_to": "Dave",
            "sys_tags": "baz",
            "close_code": "Solved",
            "u_original_assignment_group": "dvn-global-zscaler-operations",
        },
        {
            "opened_at": "2025-07-15 10:00",
            "resolved_at": "2025-07-17 10:00",
            "state": "Resolved",
            "assigned_to": "Dave",
            "sys_tags": "baz",
            "close_code": "Solved Remotely",
            "u_original_assignment_group": "",
        },
        {
            "opened_at": pd.NaT,
            "resolved_at": "2025-07-15 10:00",
            "state": "Resolved",
            "assigned_to": "Charlie",
            "sys_tags": "no-open-date",
            "close_code": "Solved",
            "u_original_assignment_group": "Service Desk",
        },
        # 2 tickets resolved outside the window
        {
            "opened_at": "2025-07-10 10:00",
            "resolved_at": "2025-07-14 10:00",
            "state": "Resolved",
            "assigned_to": "Bob",
            "sys_tags": "irrelevant",
            "close_code": "Solved",
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-18 10:00",
            "resolved_at": "2025-07-19 10:00",
            "state": "Resolved",
            "assigned_to": "Alice",
            "sys_tags": "irrelevant",
            "close_code": "Solved",
            "u_original_assignment_group": "Service Desk",
        },
        # 5 tickets still open
        {
            "opened_at": "2025-07-16 10:00",
            "resolved_at": pd.NaT,
            "state": "In Progress",
            "assigned_to": "Bob",
            "sys_tags": "open",
            "close_code": pd.NaT,
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-17 10:00",
            "resolved_at": pd.NaT,
            "state": "new",
            "assigned_to": "Unassigned",
            "sys_tags": "open, new",
            "close_code": pd.NaT,
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-17 12:00",
            "resolved_at": pd.NaT,
            "state": "On Hold",
            "assigned_to": "Alice",
            "sys_tags": "open, hold",
            "close_code": pd.NaT,
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-16 10:00",
            "resolved_at": pd.NaT,
            "state": "Closed",
            "assigned_to": "Unassigned",
            "sys_tags": "wrong-state",
            "close_code": pd.NaT,
            "u_original_assignment_group": "Service Desk",
        },
        {
            "opened_at": "2025-07-15 18:00",
            "resolved_at": pd.NaT,
            "state": "New",
            "assigned_to": "Unassigned",
            "sys_tags": "new, open",
            "close_code": pd.NaT,
            "u_original_assignment_group": "Service Desk",
        },
    ]
    return pd.DataFrame(data).astype(
        {
            "assigned_to": "string",
            "close_code": "string",
            "state": "string",
            "sys_tags": "string",
            "u_original_assignment_group": "string",
        }
    )


@pytest.fixture(scope="module")
def metrics_results(sample_ticket_df) -> dict:
    """Provides the results of running compute_metrics on the sample_ticket_df."""
    return compute_metrics(
        df=sample_ticket_df.copy(),  # Pass a copy to avoid side effects
        start="2025-07-15",
        end="2025-07-17",
        tz="America/New_York",
    )


def test_envelope_structure(metrics_results: dict):
    """Tests the top-level structure of the metrics envelope."""
    assert isinstance(metrics_results, dict)
    expected_keys = {"version", "metadata", "kpis", "series", "tables"}
    assert set(metrics_results.keys()) == expected_keys
    assert metrics_results["version"] == 3


def test_metadata(metrics_results: dict):
    """Tests the content of the metadata section."""
    meta = metrics_results["metadata"]
    assert meta["source_path"] == ""
    assert meta["tz"] == "America/New_York"
    assert meta["start"] == "2025-07-15"
    assert meta["end"] == "2025-07-17"
    assert meta["calendar_days"] == 3
    assert meta["export_row_count"] == 15  # Updated from 14
    assert meta["warnings"] == [
        "Reports based on an updated-date window may undercount newly opened tickets."
    ]


def test_metadata_dropped_counts(metrics_results: dict):
    """Tests the dropped record counts in metadata."""
    dropped = metrics_results["metadata"]["dropped"]
    assert dropped["opened_at"] == 1
    assert dropped["resolved_at"] == 5  # Updated from 4
    assert dropped["both"] == 0


def test_kpis(metrics_results: dict):
    """Tests the calculated KPIs."""
    kpis = metrics_results["kpis"]
    assert kpis["resolved_count"] == 8
    assert kpis["resolved_per_day_avg"] == 2.67  # 8 / 3 rounded
    # The exact value is 20.26190476, which should round to 20
    assert kpis["avg_ttr_hours"] == 20


def test_kpis_open_by_state_total(metrics_results: dict):
    """Tests the new open_by_state_total KPI."""
    kpis = metrics_results["kpis"]
    assert kpis["Total Open Tickets"] == 4  # 2 + 1 + 1


def test_series_resolved_per_day(metrics_results: dict):
    """Tests the resolved_per_day time series."""
    series = metrics_results["series"]["resolved_per_day"]
    assert series == [
        {"date": "2025-07-15", "count": 3},
        {"date": "2025-07-16", "count": 3},
        {"date": "2025-07-17", "count": 2},
    ]


def test_series_daily_opened(metrics_results: dict):
    """Tests the new daily_opened time series."""
    series = metrics_results["series"]["daily_opened"]
    # Opened dates: 07-15 (5), 07-16 (3), 07-17 (3)
    assert series == [
        {"date": "2025-07-15", "count": 5},
        {"date": "2025-07-16", "count": 3},
        {"date": "2025-07-17", "count": 3},
    ]


def test_series_opened_vs_resolved(metrics_results: dict):
    """Tests the new opened_vs_resolved series."""
    series = metrics_results["series"]["opened_vs_resolved"]
    assert series["dates"] == ["2025-07-15", "2025-07-16", "2025-07-17"]
    assert series["opened"] == [5, 3, 3]
    assert series["resolved"] == [3, 3, 2]


def test_table_resolved_by_assignee(metrics_results: dict):
    """Tests the resolved_by_assignee table for sorting and counts."""
    table = metrics_results["tables"]["resolved_by_assignee"]
    assert len(table) == 4
    expected_order = ["Alice", "Bob", "Charlie", "Dave"]
    actual_order = [row["assignee"] for row in table]
    assert actual_order == expected_order
    for row in table:
        assert row["count"] == 2


def test_table_top_5_tags(metrics_results: dict):
    """Tests the top_5_tags table for parsing, counting, and sorting."""
    table = metrics_results["tables"]["top_5_tags"]
    expected = [
        {"tag": "foo", "count": 5},
        {"tag": "baz", "count": 3},
        {"tag": "bar", "count": 2},
        {"tag": "dup", "count": 1},
        {"tag": "no-open-date", "count": 1},
    ]
    assert table == expected


def test_table_top_5_resolution_codes(metrics_results: dict):
    """Tests the top_5_resolution_codes table for NA handling and sorting."""
    table = metrics_results["tables"]["top_5_resolution_codes"]
    expected = [
        {"code": "Solved", "count": 4},
        {"code": "Solved Remotely", "count": 2},
        {"code": "Not Applicable", "count": 1},
        {"code": "Unspecified", "count": 1},
    ]
    assert table == expected


def test_table_open_by_state(metrics_results: dict):
    """Tests the new open_by_state table."""
    table = metrics_results["tables"]["open_by_state"]
    # Sorted by count (desc), then state (asc)
    expected = [
        {"state": "New", "count": 2, "percent": 50.0},
        {"state": "In Progress", "count": 1, "percent": 25.0},
        {"state": "On Hold", "count": 1, "percent": 25.0},
    ]
    assert table == expected


def test_table_queue_origin(metrics_results: dict):
    """Tests the new queue_origin table for categorization and sorting."""
    table = metrics_results["tables"]["queue_origin"]
    # Sorted by count (desc), then origin (asc)
    # DVN-Global-Zscaler-Operations: 3
    # From Service Desk: 5
    expected = [
        {"origin": "From Service Desk", "count": 5},
        {"origin": "DVN-Global-Zscaler-Operations", "count": 3},
    ]
    assert table == expected


def test_empty_input():
    """Tests that compute_metrics handles an empty DataFrame gracefully."""
    empty_df = pd.DataFrame(
        columns=[
            "opened_at",
            "resolved_at",
            "state",
            "assigned_to",
            "sys_tags",
            "close_code",
            "u_original_assignment_group",
        ]
    )
    metrics = compute_metrics(empty_df, "2025-01-01", "2025-01-03", "UTC")

    assert metrics["kpis"]["resolved_count"] == 0
    assert metrics["kpis"]["resolved_per_day_avg"] == 0.0
    assert metrics["kpis"]["avg_ttr_hours"] == 0
    assert metrics["kpis"]["Total Open Tickets"] == 0

    assert len(metrics["series"]["resolved_per_day"]) == 3
    assert all(d["count"] == 0 for d in metrics["series"]["resolved_per_day"])
    assert len(metrics["series"]["daily_opened"]) == 3
    assert all(d["count"] == 0 for d in metrics["series"]["daily_opened"])
    assert metrics["series"]["opened_vs_resolved"]["opened"] == [0, 0, 0]
    assert metrics["series"]["opened_vs_resolved"]["resolved"] == [0, 0, 0]

    assert metrics["tables"]["resolved_by_assignee"] == []
    assert metrics["tables"]["top_5_tags"] == []
    assert metrics["tables"]["top_5_resolution_codes"] == []
    assert metrics["tables"]["open_by_state"] == []
    assert metrics["tables"]["queue_origin"] == []
