import pandas as pd
from typing import Iterator

from zn_report.constants import REQUIRED_HEADERS
from zn_report.exceptions import MissingHeadersError, FileIOError


import io
import os
import codecs

def _read_csv_with_fallback(path: str, **kwargs) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Reads a CSV file with fallback encoding.

    Handles both file paths and file-like objects, trying UTF-8 first and
    falling back to Latin-1.

    Args:
        path: The path to the CSV file or a file-like object.
        **kwargs: Additional keyword arguments to pass to pandas.read_csv.

    Returns:
        A DataFrame or an iterator of DataFrames.

    Raises:
        FileIOError: If the file cannot be read with either encoding.
        FileNotFoundError: If the file path does not exist.
        pd.errors.EmptyDataError: If the file is empty.
    """
    # Handle file paths (str or PathLike)
    if isinstance(path, (str, os.PathLike)):
        try:
            with open(path, 'rb') as f:
                content = f.read()
        except FileNotFoundError:
            raise  # Propagate for tests that expect this

        if not content:
            return pd.read_csv(io.StringIO(''), **kwargs)

        if content.startswith(codecs.BOM_UTF16_LE) or content.startswith(codecs.BOM_UTF16_BE):
            raise FileIOError(f"The file at {path} could not be read. Please ensure it is saved with either UTF-8 or Latin-1 encoding.")

        try:
            decoded_content = content.decode('utf-8')
            return pd.read_csv(io.StringIO(decoded_content), **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            try:
                decoded_content = content.decode('latin-1')
                return pd.read_csv(io.StringIO(decoded_content), **kwargs)
            except Exception as e:
                raise FileIOError(f"The file at {path} could not be read. Please ensure it is saved with either UTF-8 or Latin-1 encoding.") from e

    # Handle file-like objects (used in tests)
    else:
        if hasattr(path, 'seek'):
            path.seek(0)
        try:
            return pd.read_csv(path, encoding='utf-8', **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            if hasattr(path, 'seek'):
                path.seek(0)
            try:
                return pd.read_csv(path, encoding='latin-1', **kwargs)
            except Exception as e:
                raise FileIOError(f"The file at {path} could not be read. Please ensure it is saved with either UTF-8 or Latin-1 encoding.") from e


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


def read_csv_headers(path: str) -> list[str]:
    """Reads only the headers of a CSV file.

    Args:
        path: The path to the CSV file.

    Returns:
        A list of header strings.
    """
    df = _read_csv_with_fallback(path, nrows=0)
    return list(df.columns)


def validate_headers(headers: list[str]) -> None:
    """Validates that all required headers are present.

    Raises:
        MissingHeadersError: If any required headers are missing.
    """
    missing = REQUIRED_HEADERS - set(headers)
    if missing:
        raise MissingHeadersError(list(missing))


def ensure_headers_ok(path: str) -> list[str]:
    """Convenience guard that reads headers and validates them.

    Args:
        path: The path to the CSV file.

    Returns:
        The list of headers if they are valid.
    """
    headers = read_csv_headers(path)
    validate_headers(headers)
    return headers


def load_csv(
    path: str,
    tz: str = "UTC",
    usecols: list[str] | None = None,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Load a CSV file, with optional chunking and column selection.

    Args:
        path: The path to the CSV file.
        tz: The timezone to use for date columns (currently unused).
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
        csv_headers = read_csv_headers(path)
        missing_cols = set(cols) - set(csv_headers)
        if missing_cols:
            raise MissingHeadersError(list(missing_cols))
    else:
        # Default behavior: ensure all required headers are present.
        ensure_headers_ok(path)

    if hasattr(path, "seek"):
        path.seek(0)

    reader = _read_csv_with_fallback(
        path,
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
