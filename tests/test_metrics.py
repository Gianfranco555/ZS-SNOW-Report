"""
Unit tests for the Metrics Engine (UPT v3).
"""
import pandas as pd
import pytest
from zn_report import metrics


@pytest.fixture
def sample_tickets_df() -> pd.DataFrame:
    """Provides a comprehensive sample of ticket data for testing."""
    data = [
        # 0: Basic resolved case in window
        {
            "opened_at": "2023-10-01T10:00:00Z", "resolved_at": "2023-10-02T12:00:00Z",
            "assigned_to": "User A", "state": "Closed", "close_code": "Resolved by User",
            "sys_tags": "metric, upt, zscaler"
        },
        # 1: Resolved, complex tags, tie-breaker assignee
        {
            "opened_at": "2023-10-02T11:00:00Z", "resolved_at": "2023-10-03T14:00:00Z",
            "assigned_to": "Zeta, Adam", "state": "Closed", "close_code": "Customer Unresponsive",
            "sys_tags": "upt; ZSCALER, api| duo" # mixed delimiters, case, spaces
        },
        # 2: Resolved, tie-breaker assignee
        {
            "opened_at": "2023-10-03T12:00:00Z", "resolved_at": "2023-10-04T16:00:00Z",
            "assigned_to": "Zeta, Adam", "state": "Closed", "close_code": "Resolved by User",
            "sys_tags": "metric, api"
        },
        # 3: Resolved, another tie-breaker assignee to test sorting
        {
            "opened_at": "2023-10-03T13:00:00Z", "resolved_at": "2023-10-05T18:00:00Z",
            "assigned_to": "Alpha, Bravo", "state": "Closed", "close_code": "Resolved by Change",
            "sys_tags": "api, change"
        },
        # 4: Also resolved, same assignee
        {
            "opened_at": "2023-10-04T14:00:00Z", "resolved_at": "2023-10-06T20:00:00Z",
            "assigned_to": "Alpha, Bravo", "state": "Closed", "close_code": "Resolved by Change",
            "sys_tags": "api, change, duo"
        },
        # 5: Resolved outside window (after)
        {
            "opened_at": "2023-10-05T15:00:00Z", "resolved_at": "2023-11-01T10:00:00Z",
            "assigned_to": "User A", "state": "Closed", "close_code": "Resolved by User", "sys_tags": ""
        },
        # 6: Resolved outside window (before)
        {
            "opened_at": "2023-09-28T16:00:00Z", "resolved_at": "2023-09-30T10:00:00Z",
            "assigned_to": "User B", "state": "Closed", "close_code": "Resolved by User", "sys_tags": "legacy"
        },
        # 7: Still open, 'New' state
        {
            "opened_at": "2023-10-08T17:00:00Z", "resolved_at": pd.NaT,
            "assigned_to": "User C", "state": "New", "close_code": pd.NaT, "sys_tags": "triage"
        },
        # 8: Still open, 'In Progress' state (mixed case)
        {
            "opened_at": "2023-10-09T18:00:00Z", "resolved_at": pd.NaT,
            "assigned_to": "User A", "state": "in progress", "close_code": pd.NaT, "sys_tags": "investigation"
        },
        # 9: Still open, 'On Hold' state
        {
            "opened_at": "2023-10-10T19:00:00Z", "resolved_at": pd.NaT,
            "assigned_to": "Unassigned", "state": "On Hold", "close_code": pd.NaT, "sys_tags": "waiting"
        },
        # 10: Still open, but state should be ignored
        {
            "opened_at": "2023-10-10T20:00:00Z", "resolved_at": pd.NaT,
            "assigned_to": "User A", "state": "Awaiting User", "close_code": pd.NaT, "sys_tags": "info-needed"
        },
        # 11: Dropped, missing opened_at
        {
            "opened_at": pd.NaT, "resolved_at": "2023-10-02T10:00:00Z",
            "assigned_to": "User D", "state": "Closed", "close_code": "Resolved by User", "sys_tags": "bad-data"
        },
        # 12: Dropped, missing both dates
        {
            "opened_at": pd.NaT, "resolved_at": pd.NaT,
            "assigned_to": "User E", "state": "New", "close_code": pd.NaT, "sys_tags": "bad-data"
        },
        # 13: Resolved, but close_code is NaN -> "Unspecified"
        {
            "opened_at": "2023-10-01T09:00:00Z", "resolved_at": "2023-10-01T18:00:00Z",
            "assigned_to": "User B", "state": "Closed", "close_code": pd.NaT, "sys_tags": "metric"
        },
        # 14-16: More data for top 5 codes
        {
            "opened_at": "2023-10-01T10:00:00Z", "resolved_at": "2023-10-07T10:00:00Z",
            "assigned_to": "User C", "state": "Closed", "close_code": "Duplicate", "sys_tags": "dup"
        },
        {
            "opened_at": "2023-10-01T11:00:00Z", "resolved_at": "2023-10-08T11:00:00Z",
            "assigned_to": "User C", "state": "Closed", "close_code": "No Action Required", "sys_tags": "no-action"
        },
        {
            "opened_at": "2023-10-01T12:00:00Z", "resolved_at": "2023-10-09T12:00:00Z",
            "assigned_to": "User C", "state": "Closed", "close_code": "No Action Required", "sys_tags": "no-action"
        },
    ]
    return pd.DataFrame(data)


# --- Basic Structure and Metadata Tests ---

def test_envelope_structure_and_types(sample_tickets_df):
    """
    Verify the basic structure and types of the output envelope.
    """
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    assert isinstance(result, dict)
    assert all(k in result for k in ["metadata", "kpis", "series", "tables"])
    assert isinstance(result["metadata"], dict)
    assert isinstance(result["kpis"], dict)
    assert isinstance(result["series"], dict)
    assert isinstance(result["tables"], dict)
    assert result["metadata"]["version"] == 3

def test_metadata_calculation(sample_tickets_df):
    """Verify metadata fields are calculated correctly."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    meta = result["metadata"]
    assert meta["tz"] == "America/New_York"
    assert meta["start"] == "2023-10-01"
    assert meta["end"] == "2023-10-10"
    assert meta["calendar_days"] == 10
    assert meta["export_row_count"] == 17
    assert meta["dropped"] == {"opened_at": 1, "resolved_at": 0, "both": 1}
    assert "updated-window may undercount opened" in meta["warnings"]

def test_kpi_calculations(sample_tickets_df):
    """Verify all KPI metrics."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    kpis = result["kpis"]
    # 10 tickets resolved in window (0-4, 11, 13, 14-16)
    assert kpis["resolved_count"] == 10
    assert kpis["resolved_per_day_avg"] == 1.0  # 10 / 10
    # TTR for 9 tickets (ticket 11 is resolved but has no open date).
    # TTRs (h): 26, 27, 28, 53, 54, 9, 144, 168, 192. Sum=701. Avg=701/9=77.88...
    assert kpis["avg_ttr_hours"] == pytest.approx(77.88888888888889)

    open_states = kpis["open_by_state"]
    assert open_states["New"] == 1
    assert open_states["In Progress"] == 1
    assert open_states["On Hold"] == 1

def test_series_resolved_per_day(sample_tickets_df):
    """Verify the daily resolved series has zero-filled buckets."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    series = result["series"]["resolved_per_day"]
    assert len(series) == 10  # 10 days in window

    counts = {item["date"]: item["count"] for item in series}
    assert counts["2023-10-01"] == 1  # Ticket 13
    assert counts["2023-10-02"] == 2  # Tickets 0, 11
    assert counts["2023-10-03"] == 1  # Ticket 1
    assert counts["2023-10-04"] == 1  # Ticket 2
    assert counts["2023-10-05"] == 1  # Ticket 3
    assert counts["2023-10-06"] == 1  # Ticket 4
    assert counts["2023-10-07"] == 1  # Ticket 14
    assert counts["2023-10-08"] == 1  # Ticket 15
    assert counts["2023-10-09"] == 1  # Ticket 16
    assert counts["2023-10-10"] == 0  # No resolutions

def test_table_resolved_by_assignee_sorting_and_tiebreak(sample_tickets_df):
    """Verify assignee table sorting (count desc, name asc)."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    table = result["tables"]["resolved_by_assignee"]

    # Expected: User C (3), Alpha, Bravo (2), Zeta, Adam (2), User A (1), User B (1), User D (1)
    assert len(table) == 6
    assert [row["assignee"] for row in table] == [
        "User C", "Alpha, Bravo", "Zeta, Adam", "User A", "User B", "User D"
    ]
    assert [row["count"] for row in table] == [3, 2, 2, 1, 1, 1]

def test_table_top_5_resolution_codes(sample_tickets_df):
    """Verify top 5 resolution codes, including NA handling and sorting."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    table = result["tables"]["top_5_resolution_codes"]

    # Expected Counts: Resolved by User (3), No Action Required (2), Resolved by Change (2), ...
    # Expected Order (Count DESC, Name ASC):
    # 1. Resolved by User (3)
    # 2. No Action Required (2)
    # 3. Resolved by Change (2)
    # 4. Customer Unresponsive (1)
    # 5. Duplicate (1)
    assert len(table) == 5
    assert [row["resolution_code"] for row in table] == [
        "Resolved by User", "No Action Required", "Resolved by Change", "Customer Unresponsive", "Duplicate"
    ]
    assert [row["count"] for row in table] == [3, 2, 2, 1, 1]


def test_table_top_5_tags(sample_tickets_df):
    """Verify tag parsing, splitting, cleaning, and ranking with deterministic sort."""
    result = metrics.compute_metrics(
        df=sample_tickets_df,
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    table = result["tables"]["top_5_tags"]

    # Expected Counts: api(4), metric(3), change(2), duo(2), no-action(2), upt(2), zscaler(2)
    # Expected Order (Count DESC, Name ASC):
    # 1. api (4)
    # 2. metric (3)
    # 3. change (2)
    # 4. duo (2)
    # 5. no-action (2)
    assert len(table) == 5
    assert [row["tag"] for row in table] == [
        "api", "metric", "change", "duo", "no-action"
    ]
    assert [row["count"] for row in table] == [4, 3, 2, 2, 2]

def test_empty_dataframe_input():
    """Ensure the function handles an empty DataFrame without errors."""
    result = metrics.compute_metrics(
        df=pd.DataFrame(),
        start="2023-10-01",
        end="2023-10-10",
        tz="America/New_York"
    )
    assert result["kpis"]["resolved_count"] == 0
    assert result["kpis"]["resolved_per_day_avg"] == 0.0
    assert result["kpis"]["avg_ttr_hours"] == 0.0
    assert result["kpis"]["open_by_state"] == {"New": 0, "In Progress": 0, "On Hold": 0}
    assert len(result["series"]["resolved_per_day"]) == 10
    assert all(d["count"] == 0 for d in result["series"]["resolved_per_day"])
    assert result["tables"]["resolved_by_assignee"] == []
    assert result["tables"]["top_5_resolution_codes"] == []
    assert result["tables"]["top_5_tags"] == []
    assert result["metadata"]["export_row_count"] == 0
    assert result["metadata"]["dropped"] == {"opened_at": 0, "resolved_at": 0, "both": 0}
