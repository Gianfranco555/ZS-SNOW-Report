import pandas as pd
from typing import Iterator

from zn_report.constants import REQUIRED_HEADERS
from zn_report.exceptions import MissingHeadersError, FileIOError


import os
import codecs
from pathlib import Path
from typing import IO, Union

def _read_csv_with_fallback(
    path: Union[str, Path, IO], **kwargs
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Reads a CSV file with fallback encoding.

    This is a memory-efficient implementation that lets pandas handle file I/O.
    It tries to read the file with UTF-8 encoding first, then falls back to
    Latin-1 if a UnicodeDecodeError or ParserError is encountered.

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
    # For file paths, we can efficiently sniff for an unsupported BOM.
    if isinstance(path, (str, os.PathLike)):
        try:
            with open(path, "rb") as f:
                bom = f.read(4)
            if bom.startswith(codecs.BOM_UTF16_LE) or bom.startswith(codecs.BOM_UTF16_BE):
                raise FileIOError(
                    f"The file at {path} could not be read. Please ensure it is saved with"
                    " either UTF-8 or Latin-1 encoding."
                )
        except FileNotFoundError:
            # Let pd.read_csv handle the FileNotFoundError to be consistent.
            pass

    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except (UnicodeDecodeError, pd.errors.ParserError):
        if hasattr(path, "seek"):
            path.seek(0)
        try:
            return pd.read_csv(path, encoding="latin-1", **kwargs)
        except Exception as e:
            raise FileIOError(
                f"The file at {path} could not be read. Please ensure it is saved with"
                " either UTF-8 or Latin-1 encoding."
            ) from e
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # Let these specific, expected errors propagate for other tests.
        raise


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
