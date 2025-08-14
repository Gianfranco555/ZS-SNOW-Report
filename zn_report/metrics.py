from __future__ import annotations

import re
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pandas as pd

from zn_report.time_ops import derive_buckets, parse_dates


def _get_top_tags(series: pd.Series, n: int) -> list[dict[str, Any]]:
    """Helper to parse, count, and return top N tags with tie-breaking."""
    if series.empty or series.isna().all():
        return []

    def _process_row(tag_string: str) -> list[str]:
        if pd.isna(tag_string) or not tag_string.strip():
            return []
        # Split by delimiters, clean, lowercase, and filter blanks
        tags = [t.strip().lower() for t in re.split(r"[,;|]", tag_string) if t.strip()]
        # De-dup per row and return as a sorted list for determinism
        return sorted(list(set(tags)))

    # Process all rows, explode into a single series of tags, and count them
    all_tags = series.apply(_process_row).explode().dropna()
    if all_tags.empty:
        return []

    counts = Counter(all_tags)
    # Sort by count (desc), then tag (asc) for tie-breaking
    sorted_tags = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    # Format for output
    return [{"tag": tag, "count": count} for tag, count in sorted_tags[:n]]


def compute_metrics(
    df: pd.DataFrame, start: str | date, end: str | date, tz: str
) -> dict[str, Any]:
    """
    Computes UPT v3 metrics from a DataFrame of ticket data.

    Args:
        df: Input DataFrame with ticket data.
        start: The start of the reporting window (inclusive).
        end: The end of the reporting window (inclusive).
        tz: The timezone for date operations.

    Returns:
        A dictionary containing the UPT v3 metrics envelope.
    """
    # 1. Initial setup & Date Handling
    export_row_count = len(df)
    source_path = ""  # Per spec, to be overwritten by CLI if available

    # Use time_ops to get a clean date range and tz-aware df
    buckets = derive_buckets(start, end, tz)
    calendar_days = len(buckets)

    # Convert date columns to tz-aware datetime objects. This is a key step
    # for all downstream calculations.
    proc_df = parse_dates(df, tz)

    # 2. Calculate dropped counts
    # Based on NaT in core date fields AFTER parsing
    opened_na = proc_df["opened_at"].isna()
    resolved_na = proc_df["resolved_at"].isna()

    # Using .sum() on boolean Series returns numpy int types; cast to standard int
    dropped_opened_at = int(opened_na.sum())
    dropped_resolved_at = int(resolved_na.sum())
    dropped_both = int((opened_na & resolved_na).sum())

    # 3. Formulate warnings
    # The UPT v3 spec requires this warning as its methodology, which focuses on
    # resolved tickets, can undercount tickets that were opened but not resolved
    # within the same window.
    warnings = [
        "Reports based on an updated-date window may undercount newly opened tickets."
    ]

    # 4. Assemble metadata payload
    # Note: buckets list can be empty if start > end, though upstream logic
    # should prevent this. Handle gracefully just in case.
    start_str = str(buckets[0]) if buckets else str(start)
    end_str = str(buckets[-1]) if buckets else str(end)

    metadata = {
        "source_path": source_path,
        "tz": tz,
        "start": start_str,
        "end": end_str,
        "calendar_days": calendar_days,
        "export_row_count": export_row_count,
        "dropped": {
            "opened_at": dropped_opened_at,
            "resolved_at": dropped_resolved_at,
            "both": dropped_both,
        },
        "warnings": warnings,
    }

    # 5. Filter data for KPI calculations
    # The primary filter is for tickets resolved within the reporting window.
    resolved_df = pd.DataFrame(columns=proc_df.columns)
    start_ts = None
    end_ts = None
    if buckets:
        # Create tz-aware timestamps for the start and end of the date range
        start_ts = pd.Timestamp(buckets[0], tz=tz)
        end_ts = pd.Timestamp(buckets[-1], tz=tz).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        resolved_mask = proc_df["resolved_at"].between(
            start_ts, end_ts, inclusive="both"
        )
        # Drop rows where mask is NA (i.e., resolved_at is NaT)
        resolved_df = proc_df[resolved_mask.fillna(False)].copy()

    # 6. Calculate KPIs
    resolved_count = len(resolved_df)
    resolved_per_day_avg = (
        round(resolved_count / calendar_days, 2) if calendar_days > 0 else 0.0
    )

    # TTR (Time to Resolution) in hours
    if not resolved_df.empty and "opened_at" in resolved_df:
        # Ensure both date columns are present before calculating delta
        ttr_deltas = resolved_df["resolved_at"] - resolved_df["opened_at"]
        # Convert Timedelta to total hours, then take mean. Result is float.
        avg_ttr_hours_float = ttr_deltas.dt.total_seconds().mean() / 3600
        if pd.isna(avg_ttr_hours_float):  # Mean of empty or all-NaT series is NaN
            avg_ttr_hours = 0
        else:
            # Round half-up to nearest whole number
            avg_ttr_hours = int(
                Decimal(str(avg_ttr_hours_float)).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
    else:
        avg_ttr_hours = 0

    # Open states: count tickets that are NOT resolved yet, by state.
    # Per spec, this is case-insensitive for a fixed list of states.
    open_states = ["New", "In Progress", "On Hold"]
    open_df = proc_df[proc_df["resolved_at"].isna()]

    if "state" in open_df.columns and not open_df.empty:
        # Normalize state column for case-insensitive matching
        state_counts = open_df["state"].str.lower().value_counts()
        open_by_state = {
            state: int(state_counts.get(state.lower(), 0)) for state in open_states
        }
    else:
        open_by_state = {state: 0 for state in open_states}

    open_by_state_total = sum(open_by_state.values())

    kpis = {
        "resolved_count": resolved_count,
        "resolved_per_day_avg": resolved_per_day_avg,
        "avg_ttr_hours": avg_ttr_hours,
        "Total Open Tickets": open_by_state_total,
    }

    # 7. Calculate Time Series data
    # resolved_per_day: count of tickets resolved on each calendar day in window.
    if not resolved_df.empty:
        resolved_dates = resolved_df["resolved_at"].dt.date
        resolved_daily_counts = resolved_dates.value_counts().to_dict()
    else:
        resolved_daily_counts = {}

    resolved_per_day = [
        {"date": b.strftime("%Y-%m-%d"), "count": resolved_daily_counts.get(b, 0)}
        for b in buckets
    ]

    # daily_opened: count of tickets opened on each calendar day in window
    opened_df_in_window = pd.DataFrame(columns=proc_df.columns)
    if start_ts and end_ts:
        opened_mask = proc_df["opened_at"].between(start_ts, end_ts, inclusive="both")
        opened_df_in_window = proc_df[opened_mask.fillna(False)].copy()

    if not opened_df_in_window.empty:
        opened_dates = opened_df_in_window["opened_at"].dt.date
        opened_daily_counts = opened_dates.value_counts().to_dict()
    else:
        opened_daily_counts = {}

    daily_opened = [
        {"date": b.strftime("%Y-%m-%d"), "count": opened_daily_counts.get(b, 0)}
        for b in buckets
    ]

    # opened_vs_resolved: combination of daily opened and resolved counts
    opened_vs_resolved = {
        "dates": [b.strftime("%Y-%m-%d") for b in buckets],
        "opened": [d["count"] for d in daily_opened],
        "resolved": [d["count"] for d in resolved_per_day],
    }

    series = {
        "resolved_per_day": resolved_per_day,
        "daily_opened": daily_opened,
        "opened_vs_resolved": opened_vs_resolved,
    }

    # 8. Calculate Tables
    # Table: open_by_state
    if open_by_state_total > 0:
        # Sort by count (desc), then state name (asc)
        sorted_states = sorted(
            open_by_state.items(), key=lambda item: (-item[1], item[0])
        )
        open_by_state_table = [
            {
                "state": state,
                "count": count,
                "percent": round((count / open_by_state_total) * 100, 1),
            }
            for state, count in sorted_states
            if count > 0
        ]
    else:
        open_by_state_table = []

    tables = {
        "resolved_by_assignee": [],
        "top_5_tags": [],
        "top_5_resolution_codes": [],
        "open_by_state": open_by_state_table,
        "queue_origin": [],
    }
    if not resolved_df.empty:
        # Table: Resolved by Assignee
        if "assigned_to" in resolved_df.columns:
            assignee_counts = resolved_df["assigned_to"].value_counts()
            df_assignees = assignee_counts.reset_index()
            df_assignees.columns = ["assignee", "count"]
            df_assignees = df_assignees.sort_values(
                by=["count", "assignee"], ascending=[False, True]
            )
            tables["resolved_by_assignee"] = [
                {"assignee": row.assignee, "count": int(row.count)}
                for row in df_assignees.itertuples()
            ]

        # Table: Top 5 Tags
        if "sys_tags" in resolved_df.columns:
            tables["top_5_tags"] = _get_top_tags(resolved_df["sys_tags"], n=5)

        # Table: Top 5 Resolution Codes
        if "close_code" in resolved_df.columns:
            codes = (
                resolved_df["close_code"]
                .fillna("Unspecified")
                .replace("", "Unspecified")
            )
            code_counts = codes.value_counts()
            df_codes = code_counts.reset_index()
            df_codes.columns = ["code", "count"]
            df_codes = df_codes.sort_values(
                by=["count", "code"], ascending=[False, True]
            )
            top_5 = df_codes.head(5)
            tables["top_5_resolution_codes"] = [
                {"code": row.code, "count": int(row.count)}
                for row in top_5.itertuples()
            ]

        # Table: Queue Origin
        if "u_original_assignment_group" in resolved_df.columns:
            # Create a temporary column for categorization
            resolved_df["origin"] = resolved_df["u_original_assignment_group"].apply(
                lambda x: (
                    "DVN-Global-Zscaler-Operations"
                    if pd.notna(x) and x.lower() == "dvn-global-zscaler-operations"
                    else "From Service Desk"
                )
            )

            origin_counts = resolved_df["origin"].value_counts().reset_index()
            origin_counts.columns = ["origin", "count"]
            # Sort by count (desc), then origin (asc)
            origin_counts = origin_counts.sort_values(
                by=["count", "origin"], ascending=[False, True]
            )
            tables["queue_origin"] = [
                {"origin": row.origin, "count": int(row.count)}
                for row in origin_counts.itertuples()
            ]

    return {
        "version": 3,
        "metadata": metadata,
        "kpis": kpis,
        "series": series,
        "tables": tables,
    }
