import pandas as pd
from typing import Iterator

from zn_report.constants import REQUIRED_HEADERS
from zn_report.exceptions import MissingHeadersError


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
    ...
