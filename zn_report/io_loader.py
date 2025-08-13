import pandas as pd
from typing import Iterator

from zn_report.constants import REQUIRED_HEADERS
from zn_report.exceptions import MissingHeadersError


STRING_COLS = (
    "sys_tags",
    "comments",
    "work_notes",
    "assigned_to",
    "state",
    "u_original_assignment_group",
    "close_code",
)


def _normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize string columns."""
    df = df.copy()
    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype(pd.StringDtype()).str.strip()
            if col == "assigned_to":
                df[col] = df[col].replace("", "Unassigned").fillna("Unassigned")

    return df


def read_csv_headers(path: str, encoding: str = "utf-8") -> list[str]:
    """Reads only the headers of a CSV file.

    Args:
        path: The path to the CSV file.
        encoding: The encoding of the file.

    Returns:
        A list of header strings.
    """
    df = pd.read_csv(path, nrows=0, encoding=encoding)
    return list(df.columns)


def validate_headers(headers: list[str]) -> None:
    """Validates that all required headers are present.

    Raises:
        MissingHeadersError: If any required headers are missing.
    """
    missing = REQUIRED_HEADERS - set(headers)
    if missing:
        raise MissingHeadersError(list(missing))


def ensure_headers_ok(path: str, encoding: str = "utf-8") -> list[str]:
    """Convenience guard that reads headers and validates them.

    Args:
        path: The path to the CSV file.
        encoding: The encoding of the file.

    Returns:
        The list of headers if they are valid.
    """
    headers = read_csv_headers(path, encoding)
    validate_headers(headers)
    return headers


def load_csv(
    path: str,
    tz: str = "UTC",
    encoding: str = "utf-8",
    usecols: list[str] | None = None,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Load a CSV file, with optional chunking and column selection.

    Args:
        path: The path to the CSV file.
        tz: The timezone to use for date columns (currently unused).
        encoding: The encoding of the file.
        usecols: A list of columns to load. If None, all required headers are used.
        chunksize: The number of rows to read per chunk.

    Returns:
        A DataFrame or an iterator of DataFrames.
    """
    # tz is accepted for signature parity but unused
    del tz

    cols = usecols or sorted(list(REQUIRED_HEADERS))
    if usecols:
        # When usecols is specified, we should only validate that those columns exist.
        csv_headers = read_csv_headers(path, encoding)
        missing_cols = set(cols) - set(csv_headers)
        if missing_cols:
            raise MissingHeadersError(list(missing_cols))
    else:
        # Default behavior: ensure all required headers are present.
        ensure_headers_ok(path, encoding)

    reader = pd.read_csv(
        path,
        encoding=encoding,
        usecols=cols,
        dtype="string",
        chunksize=chunksize,
        keep_default_na=True,
    )

    if chunksize is None:
        # reader is a DataFrame
        df = _normalize_strings(reader)
        return df[cols]
    else:
        # reader is an iterator
        def _process_chunks():
            for chunk in reader:
                yield _normalize_strings(chunk)[cols]

        return _process_chunks()
