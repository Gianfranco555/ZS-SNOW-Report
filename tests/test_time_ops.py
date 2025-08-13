import pandas as pd
import pytest
from datetime import date
from pandas.api.types import is_datetime64tz_dtype

from zn_report.time_ops import parse_dates, derive_buckets


def test_parse_dates_localize_and_convert():
    df = pd.DataFrame({
        "opened_at": [
            "2025-03-08 01:30:00",            # naive → localize to America/Chicago
            "2025-07-03T17:05:00-05:00",      # tz-aware → convert to America/Chicago
            "bad-date",                        # invalid → NaT
        ],
        "resolved_at": [
            "2025-03-08 03:30:00",
            "2025-07-03T17:45:00-05:00",
            ""
        ],
        "sys_tags": ["a", "b", "c"]
    })

    out = parse_dates(df, tz="America/Chicago")

    assert is_datetime64tz_dtype(out["opened_at"])
    assert is_datetime64tz_dtype(out["resolved_at"])

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
    assert buckets == [date(2024,2,28), date(2024,2,29), date(2024,3,1)]

    # Accepts date objects
    b2 = derive_buckets(date(2025, 7, 1), date(2025, 7, 3), tz="America/Chicago")
    assert b2 == [date(2025,7,1), date(2025,7,2), date(2025,7,3)]


def test_derive_buckets_rejects_inverted_range():
    with pytest.raises(ValueError):
        derive_buckets("2025-08-10", "2025-08-09", tz="UTC")
