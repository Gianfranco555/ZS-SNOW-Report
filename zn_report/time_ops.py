from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Iterable, List
from zoneinfo import ZoneInfo
import pandas as pd


DATE_OPEN = "opened_at"
DATE_RESOLVED = "resolved_at"
_DATE_COLS: tuple[str, str] = (DATE_OPEN, DATE_RESOLVED)


def parse_dates(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """
    Convert 'opened_at' and 'resolved_at' to tz-aware pandas datetimes in the
    requested display timezone.

    Rules (spec-aligned):
    - If a value carries an explicit timezone, convert it to the display TZ.
    - If a value is naive, localize it **as-is** to the display TZ (no UTC first).
    - Parse errors → NaT (still compatible with tz-aware dtype).
    - Leaves non-date columns untouched.
    """
    out = df.copy()

    def _process_timestamp(ts):
        if pd.isna(ts):
            return pd.NaT
        if ts.tzinfo is None:
            return ts.tz_localize(tz, nonexistent="NaT", ambiguous="NaT")
        else:
            return ts.tz_convert(tz)

    for col in _DATE_COLS:
        if col in out.columns:
            # Element-wise conversion is needed to correctly handle mixed naive/aware
            # strings as per spec (vectorized pd.to_datetime assumes UTC for naive).
            s = out[col].apply(pd.to_datetime, errors="coerce")
            # Apply timezone logic to each element.
            out[col] = s.apply(_process_timestamp)
        else:
            # If a date column is missing, create an empty one with the target dtype.
            out[col] = pd.Series([], dtype=f"datetime64[ns, {tz}]")

    return out


def derive_buckets(start: date | str, end: date | str, tz: str) -> list[date]:
    """
    Return an inclusive list of calendar dates from start..end (YYYY-MM-DD window).
    'tz' is accepted for interface parity; buckets themselves are date-only.
    """
    def _to_date(d) -> date:
        if isinstance(d, date):
            return d
        return pd.to_datetime(d, errors="raise").date()

    s = _to_date(start)
    e = _to_date(end)
    if s > e:
        raise ValueError("start date must be <= end date")

    days = (e - s).days + 1
    return [s + timedelta(days=i) for i in range(days)]
