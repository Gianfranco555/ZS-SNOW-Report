from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Iterable, List
from zoneinfo import ZoneInfo
import pandas as pd
from pandas.api.types import is_datetime64tz_dtype, DatetimeTZDtype


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
    target_tz = ZoneInfo(tz)

    def _process_timestamp(value):
        if pd.isna(value) or value == "":
            return pd.NaT
        try:
            # Per spec, parse with errors="raise"
            ts = pd.to_datetime(value, errors="raise")
        except (ValueError, TypeError):
            return pd.NaT

        # If tz-aware, convert to target_tz.
        if ts.tzinfo is not None:
            return ts.tz_convert(target_tz)
        # If naive, localize to target_tz. Coerce DST boundary issues to NaT.
        else:
            return ts.tz_localize(target_tz, nonexistent="NaT", ambiguous="NaT")

    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = out[col].apply(_process_timestamp)
            # After processing, ensure the column has the correct timezone-aware dtype,
            # especially if it contains all NaT values (which results in object dtype).
            if not isinstance(out[col].dtype, DatetimeTZDtype):
                # This can happen if all inputs were invalid, creating a Series of NaTs
                # with a non-tz-aware dtype (like object or datetime64[ns]).
                # We must explicitly convert it to the target tz-aware dtype.
                # `astype` fails for naive -> aware, so we convert to datetime (if needed),
                # then localize. Since all values are NaT, localizing is safe.
                out[col] = pd.to_datetime(out[col]).dt.tz_localize(target_tz)
        else:
            # If a date column is missing, create an empty one with the target dtype.
            out[col] = pd.Series([], dtype=f"datetime64[ns, {target_tz}]")

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
