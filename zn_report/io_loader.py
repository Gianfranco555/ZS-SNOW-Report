import pandas as pd
from typing import Iterator

from zn_report.exceptions import MissingHeadersError

REQUIRED_HEADERS: frozenset[str] = frozenset({
    "sys_tags",
    "comments",
    "work_notes",
    "assigned_to",
    "opened_at",
    "state",
    "resolved_at",
    "u_original_assignment_group",
    "close_code",
})


def read_csv_headers(path: str, encoding: str = "utf-8") -> list[str]:
    ...


def validate_headers(headers: list[str]) -> None:
    """Validates that all required headers are present.

    Raises:
        MissingHeadersError: If any required headers are missing.
    """
    ...


def load_csv(
    path: str,
    tz: str = "UTC",
    encoding: str = "utf-8",
    usecols: list[str] | None = None,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    ...
