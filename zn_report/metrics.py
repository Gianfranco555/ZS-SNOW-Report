"""
Metrics Engine (UPT v3)
"""
from __future__ import annotations
import re
from datetime import date
from typing import Any

import pandas as pd

from . import time_ops


def compute_metrics(df: pd.DataFrame, start: date | str, end: date | str, tz: str) -> dict[str, Any]:
    """
    Computes UPT v3 metrics from a given DataFrame of Zscaler tickets.

    Args:
        df: DataFrame containing ticket data.
        start: The start of the reporting window (inclusive).
        end: The end of the reporting window (inclusive).
        tz: The timezone for analysis.

    Returns:
        A dictionary containing the UPT v3 metrics envelope.
    """
    # 1. Prepare data and metadata
    export_row_count = len(df)

    # Handle empty or incomplete DataFrame
    if df.empty or time_ops.DATE_OPEN not in df.columns or time_ops.DATE_RESOLVED not in df.columns:
        df = pd.DataFrame(columns=[time_ops.DATE_OPEN, time_ops.DATE_RESOLVED]) # Ensure columns exist

    # Calculate dropped rows based on null values in original data
    opened_na = df[time_ops.DATE_OPEN].isna()
    resolved_na = df[time_ops.DATE_RESOLVED].isna()
    dropped_counts = {
        # A ticket with no open date is unusable
        "opened_at": (opened_na & ~resolved_na).sum(),
        # A ticket with no resolved date is just open, not dropped. This key is for future use.
        "resolved_at": 0,
        "both": (opened_na & resolved_na).sum(),
    }

    # Parse dates, which is the main source of data filtering/validation
    df_parsed = time_ops.parse_dates(df, tz)

    # Derive date buckets for the report window
    buckets = time_ops.derive_buckets(start, end, tz)
    calendar_days = len(buckets)

    # Per spec, add a warning about potential undercounting with this filter method
    warnings = ["updated-window may undercount opened"]

    metadata = {
        "version": 3,
        "source_path": "",  # Per spec, to be populated by CLI layer
        "tz": tz,
        "start": str(buckets[0]) if buckets else str(start),
        "end": str(buckets[-1]) if buckets else str(end),
        "calendar_days": calendar_days,
        "export_row_count": export_row_count,
        "dropped": dropped_counts,
        "warnings": warnings,
    }

    # 2. Filter data for KPI calculations
    # Window must be tz-aware for accurate comparisons
    window_start_dt = pd.Timestamp(buckets[0], tz=tz) if buckets else None
    window_end_dt = (
        pd.Timestamp(buckets[-1], tz=tz) + pd.Timedelta(days=1) if buckets else None
    )

    df_resolved = pd.DataFrame()
    if window_start_dt and window_end_dt:
        resolved_mask = (
            df_parsed[time_ops.DATE_RESOLVED].notna()
            & (df_parsed[time_ops.DATE_RESOLVED] >= window_start_dt)
            & (df_parsed[time_ops.DATE_RESOLVED] < window_end_dt)
        )
        df_resolved = df_parsed[resolved_mask]

    # 3. Calculate KPIs
    resolved_count = len(df_resolved)
    resolved_per_day_avg = (
        round(resolved_count / calendar_days, 2) if calendar_days > 0 else 0.0
    )

    if not df_resolved.empty:
        ttr_hours = (
            df_resolved[time_ops.DATE_RESOLVED] - df_resolved[time_ops.DATE_OPEN]
        ).dt.total_seconds() / 3600
        avg_ttr_hours = ttr_hours.mean()
    else:
        avg_ttr_hours = 0.0

    # Calculate open tickets by state (case-insensitive)
    open_states = ["New", "In Progress", "On Hold"]
    open_mask = pd.Series([False] * len(df_parsed), index=df_parsed.index)
    if window_end_dt:
        open_mask = (df_parsed[time_ops.DATE_OPEN] < window_end_dt) & (
            df_parsed[time_ops.DATE_RESOLVED].isna()
            | (df_parsed[time_ops.DATE_RESOLVED] >= window_end_dt)
        )

    df_open = df_parsed[open_mask]

    open_by_state = {s: 0 for s in open_states}
    if not df_open.empty and "state" in df_open.columns:
        # Normalize state names to title case for consistent grouping
        state_counts = (
            df_open[df_open["state"].str.lower().isin([s.lower() for s in open_states])]["state"]
            .str.title()
            .value_counts()
        )
        open_by_state.update(state_counts.to_dict())


    kpis = {
        "resolved_count": resolved_count,
        "resolved_per_day_avg": resolved_per_day_avg,
        "avg_ttr_hours": avg_ttr_hours,
        "open_by_state": open_by_state,
    }

    # 4. Calculate Series
    if not df_resolved.empty:
        daily_counts = df_resolved[time_ops.DATE_RESOLVED].dt.date.value_counts()
        # Create a series from buckets to ensure all days are present
        bucket_dates = [b for b in buckets]
        daily_counts = daily_counts.reindex(bucket_dates, fill_value=0)
    else:
        # If no resolved tickets, create a series of zeros for all buckets
        daily_counts = pd.Series(0, index=pd.to_datetime(buckets).date)

    # Format for JSON output
    resolved_per_day = [
        {"date": str(idx), "count": int(val)}
        for idx, val in daily_counts.sort_index().items()
    ]

    series = {"resolved_per_day": resolved_per_day}

    # 5. Calculate Tables
    resolved_by_assignee = []
    if not df_resolved.empty and "assigned_to" in df_resolved.columns:
        assignee_counts = df_resolved["assigned_to"].value_counts().reset_index()
        assignee_counts.columns = ["assignee", "count"]
        assignee_counts = assignee_counts.sort_values(
            by=["count", "assignee"], ascending=[False, True]
        )
        resolved_by_assignee = assignee_counts.to_dict("records")

    top_5_resolution_codes = []
    if not df_resolved.empty and "close_code" in df_resolved.columns:
        codes_counts = df_resolved["close_code"].fillna("Unspecified").value_counts().reset_index()
        codes_counts.columns = ["resolution_code", "count"]
        codes_counts = codes_counts.sort_values(
            by=["count", "resolution_code"], ascending=[False, True]
        ).head(5)
        top_5_resolution_codes = codes_counts.to_dict("records")


    top_5_tags = []
    if not df_resolved.empty and "sys_tags" in df_resolved.columns:
        tags_series = df_resolved["sys_tags"].dropna().astype(str)
        # Split by delimiters, then clean, lowercase, and deduplicate in one apply
        cleaned_tags = tags_series.apply(
            lambda raw_tags: list(
                {
                    tag.strip().lower()
                    for tag in re.split(r"[\s,|;]+", raw_tags)
                    if tag.strip()
                }
            )
        )
        all_tags = cleaned_tags.explode().dropna()
        if not all_tags.empty:
            tag_counts = all_tags.value_counts().reset_index()
            tag_counts.columns = ["tag", "count"]
            tag_counts = tag_counts.sort_values(
                by=["count", "tag"], ascending=[False, True]
            ).head(5)
            top_5_tags = tag_counts.to_dict("records")

    tables = {
        "resolved_by_assignee": resolved_by_assignee,
        "top_5_resolution_codes": top_5_resolution_codes,
        "top_5_tags": top_5_tags,
    }

    return {
        "metadata": metadata,
        "kpis": kpis,
        "series": series,
        "tables": tables,
    }
