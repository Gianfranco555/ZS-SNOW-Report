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
    tzinfo = ZoneInfo(tz)

    def _coerce_one(x):
        if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and x.strip() == ""):
            return pd.NaT
        try:
            ts = pd.to_datetime(x, errors="raise")
        except Exception:
            return pd.NaT
        # pandas Timestamp: tz-aware → convert; naive → localize
        if getattr(ts, "tzinfo", None) is None:
            try:
                # Handle DST gaps/ambiguous by coercing to NaT rather than raising
                return ts.tz_localize(tzinfo, nonexistent="NaT", ambiguous="NaT")
            except TypeError:
                # Fallback for older pandas without nonexistent/ambiguous kwargs
                try:
                    return ts.tz_localize(tzinfo)
                except Exception:
                    return pd.NaT
        else:
            return ts.tz_convert(tzinfo)

    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = pd.Series((_coerce_one(v) for v in out[col]))
        else:
            # Required by spec elsewhere, but we don't enforce header contract here.
            out[col] = pd.Series([], dtype="datetime64[ns]")

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
