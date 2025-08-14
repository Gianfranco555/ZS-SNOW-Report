import pandas as pd
import pytest
from datetime import date
from pandas.api.types import DatetimeTZDtype

from zn_report.time_ops import parse_dates, derive_buckets


def test_parse_dates_localize_and_convert():
    df = pd.DataFrame(
        {
            "opened_at": [
                "2025-03-08 01:30:00",  # naive → localize to America/Chicago
                "2025-07-03T17:05:00-05:00",  # tz-aware → convert to America/Chicago
                "bad-date",  # invalid → NaT
            ],
            "resolved_at": ["2025-03-08 03:30:00", "2025-07-03T17:45:00-05:00", ""],
            "sys_tags": ["a", "b", "c"],
        }
    )

    out = parse_dates(df, tz="America/Chicago")

    assert isinstance(out["opened_at"].dtype, DatetimeTZDtype)
    assert isinstance(out["resolved_at"].dtype, DatetimeTZDtype)

    # Row 0: naive localized to target tz (date component should match 2025-03-08)
    assert out.loc[0, "opened_at"].date().isoformat() == "2025-03-08"

    # Row 1: tz-aware converted (date remains 2025-07-03 in target tz)
    assert out.loc[1, "opened_at"].date().isoformat() == "2025-07-03"

    # Row 2: invalid → NaT
    assert pd.isna(out.loc[2, "opened_at"])

    # Non-date column untouched
    assert list(out["sys_tags"]) == ["a", "b", "c"]


def test_derive_buckets_inclusive_and_types():
    # Accepts strings
    buckets = derive_buckets("2024-02-28", "2024-03-01", tz="UTC")
    assert buckets == [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1)]

    # Accepts date objects
    b2 = derive_buckets(date(2025, 7, 1), date(2025, 7, 3), tz="America/Chicago")
    assert b2 == [date(2025, 7, 1), date(2025, 7, 2), date(2025, 7, 3)]


def test_derive_buckets_rejects_inverted_range():
    with pytest.raises(ValueError):
        derive_buckets("2025-08-10", "2025-08-09", tz="UTC")


def test_parse_dates_handles_dst_boundaries():
    # DST in America/Chicago for 2025:
    # - Spring forward: Mar 9, 2:00 AM -> 3:00 AM (2:00-2:59 does not exist)
    # - Fall back: Nov 2, 2:00 AM -> 1:00 AM (1:00-1:59 is ambiguous)
    df = pd.DataFrame(
        {
            "opened_at": [
                "2025-03-09 02:30:00",  # nonexistent time
                "2025-11-02 01:30:00",  # ambiguous time
            ],
        }
    )

    out = parse_dates(df, tz="America/Chicago")

    # Non-existent and ambiguous times should be coerced to NaT
    assert pd.isna(out.loc[0, "opened_at"])
    assert pd.isna(out.loc[1, "opened_at"])
    assert isinstance(out["opened_at"].dtype, DatetimeTZDtype)
