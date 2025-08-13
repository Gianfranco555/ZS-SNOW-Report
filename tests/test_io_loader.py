import os
import shutil
import unittest
import pandas as pd
import pytest
import numpy as np
import io

from zn_report.io_loader import (
    _normalize_strings,
    read_csv_headers,
    validate_headers,
    ensure_headers_ok,
    load_csv,
    STRING_COLS,
)
from zn_report.exceptions import MissingHeadersError
from zn_report.constants import REQUIRED_HEADERS


@pytest.fixture
def csv_content() -> str:
    """Provides a 5-row CSV string with headers and varied data."""
    # Use a structured approach to create the CSV content to avoid column mismatch errors.
    headers = sorted(list(REQUIRED_HEADERS))
    data = [
        {
            "sys_tags": "  tag1 ", "comments": " c1 ", "work_notes": " w1 ", "assigned_to": " ",
            "state": " new ", "u_original_assignment_group": " g1 ", "close_code": " cc1 ",
            "opened_at": "2023-01-01", "resolved_at": "2023-01-01"
        },
        {
            "sys_tags": "tag2", "comments": "c2", "work_notes": "w2", "assigned_to": "user1",
            "state": "closed", "u_original_assignment_group": "g2", "close_code": "cc2",
            "opened_at": "2023-01-02", "resolved_at": "2023-01-02"
        },
        {
            "sys_tags": " tag3", "comments": "c3 ", "work_notes": " w3 ", "assigned_to": "  user2  ",
            "state": "  pending  ", "u_original_assignment_group": " g3 ", "close_code": " cc3 ",
            "opened_at": "2023-01-03", "resolved_at": "2023-01-03"
        },
        {
            "sys_tags": "tag4", "comments": "c4", "work_notes": "w4", "assigned_to": "",
            "state": "closed", "u_original_assignment_group": "g4", "close_code": "cc4",
            "opened_at": "2023-01-04", "resolved_at": "2023-01-04"
        },
        {
            "sys_tags": "tag5", "comments": "c5", "work_notes": "w5", "assigned_to": "user3",
            "state": "new", "u_original_assignment_group": "g5", "close_code": "cc5",
            "opened_at": "2023-01-05", "resolved_at": "2023-01-05"
        },
    ]
    # Create a DataFrame to easily convert to a CSV string with the correct header order.
    df = pd.DataFrame(data, columns=headers)
    return df.to_csv(index=False)


class TestIoLoaderHermetic:
    def test_missing_headers_raises(self):
        """Test that loading a CSV with missing headers raises MissingHeadersError."""
        # Create a CSV with one required header missing.
        headers = sorted(list(REQUIRED_HEADERS - {"sys_tags"}))
        csv_file = io.StringIO(",".join(headers) + "\n" + ",".join(["data"] * len(headers)))

        with pytest.raises(MissingHeadersError) as excinfo:
            load_csv(csv_file)

        # The error should report the exact missing header.
        assert excinfo.value.missing == ["sys_tags"]

    def test_load_csv_single_frame_ok(self, csv_content: str):
        """Test that loading a CSV in a single frame works correctly."""
        csv_file = io.StringIO(csv_content)
        df = load_csv(csv_file)

        assert isinstance(df, pd.DataFrame)

        # Columns should be sorted as per default behavior.
        expected_cols = sorted(list(REQUIRED_HEADERS))
        assert list(df.columns) == expected_cols

        # All string-like columns should be of StringDtype.
        for col in STRING_COLS:
            assert isinstance(df[col].dtype, pd.StringDtype)

        # Check whitespace stripping and special 'Unassigned' replacement.
        expected_assigned_to = pd.Series(
            ["Unassigned", "user1", "user2", "Unassigned", "user3"],
            name="assigned_to",
            dtype="string"
        )
        pd.testing.assert_series_equal(df["assigned_to"], expected_assigned_to)

        expected_sys_tags = pd.Series(
            ["tag1", "tag2", "tag3", "tag4", "tag5"],
            name="sys_tags",
            dtype="string"
        )
        pd.testing.assert_series_equal(df["sys_tags"], expected_sys_tags)

    def test_load_csv_chunked_iterator(self, csv_content: str):
        """Test that loading a CSV with chunking works correctly."""
        # Full load for comparison.
        full_df = load_csv(io.StringIO(csv_content))

        # Chunked load.
        csv_file = io.StringIO(csv_content)
        chunks = load_csv(csv_file, chunksize=2)

        assert hasattr(chunks, "__iter__")
        chunk_list = list(chunks)

        assert len(chunk_list) == 3
        assert all(isinstance(chunk, pd.DataFrame) for chunk in chunk_list)
        assert [len(chunk) for chunk in chunk_list] == [2, 2, 1]

        # Compare concatenated chunks to the full-loaded DataFrame.
        concatenated_df = pd.concat(chunk_list).reset_index(drop=True)
        pd.testing.assert_frame_equal(concatenated_df, full_df)

    def test_usecols_override(self, csv_content: str):
        """Test that `usecols` overrides the default column selection."""
        csv_file = io.StringIO(csv_content)
        usecols = ["assigned_to", "state"]
        df = load_csv(csv_file, usecols=usecols)

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == usecols
        assert len(df) == 5


class TestIoLoader(unittest.TestCase):
    def setUp(self):
        """Set up test files."""
        self.test_dir = "test_data"
        os.makedirs(self.test_dir, exist_ok=True)

        self.valid_headers = sorted(list(REQUIRED_HEADERS))
        self.missing_headers = self.valid_headers[:-2]

        self.valid_csv_path = os.path.join(self.test_dir, "valid.csv")
        self.invalid_csv_path = os.path.join(self.test_dir, "invalid.csv")
        self.empty_csv_path = os.path.join(self.test_dir, "empty.csv")
        self.data_csv_path = os.path.join(self.test_dir, "data.csv")

        pd.DataFrame(columns=self.valid_headers).to_csv(
            self.valid_csv_path, index=False
        )
        pd.DataFrame(columns=self.missing_headers).to_csv(
            self.invalid_csv_path, index=False
        )
        with open(self.empty_csv_path, "w") as f:
            f.write("")

        # Create a CSV with data for load_csv tests
        test_data = {
            "opened_at": ["2023-01-01 12:00:00", "2023-01-02 12:00:00"],
            "resolved_at": ["2023-01-01 13:00:00", "2023-01-02 13:00:00"],
            "sys_tags": ["  tag1 ", " tag2  "],
            "comments": [" comment1 ", "comment2 "],
            "work_notes": [" notes1 ", "  notes2"],
            "assigned_to": ["  user1", ""],
            "state": ["  Closed", "New  "],
            "u_original_assignment_group": ["  group1", "group2  "],
            "close_code": ["  code1", "code2  "],
        }
        pd.DataFrame(test_data).to_csv(self.data_csv_path, index=False)

    def tearDown(self):
        """Tear down test files."""
        shutil.rmtree(self.test_dir)

    def test_read_csv_headers_valid(self):
        headers = read_csv_headers(self.valid_csv_path)
        self.assertEqual(headers, self.valid_headers)

    def test_read_csv_headers_invalid(self):
        headers = read_csv_headers(self.invalid_csv_path)
        self.assertEqual(headers, self.missing_headers)

    def test_read_csv_headers_empty(self):
        with pytest.raises(pd.errors.EmptyDataError):
            read_csv_headers(self.empty_csv_path)

    def test_validate_headers_valid(self):
        validate_headers(self.valid_headers)

    def test_validate_headers_invalid(self):
        with pytest.raises(MissingHeadersError) as excinfo:
            validate_headers(self.missing_headers)

        missing = sorted(list(REQUIRED_HEADERS - set(self.missing_headers)))
        self.assertEqual(excinfo.value.missing, missing)

    def test_ensure_headers_ok_valid(self):
        headers = ensure_headers_ok(self.valid_csv_path)
        self.assertEqual(headers, self.valid_headers)

    def test_ensure_headers_ok_invalid(self):
        with pytest.raises(MissingHeadersError):
            ensure_headers_ok(self.invalid_csv_path)

    def test_ensure_headers_ok_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ensure_headers_ok("non_existent_file.csv")

    def test_normalize_strings(self):
        """Test the _normalize_strings function."""
        test_data = {
            "comments": ["  leading", "trailing  ", "  both  ", "no space"],
            "work_notes": [" a ", "b", " c", "d "],
            "assigned_to": ["  test ", "", None, np.nan],
            "state": ["  New", "Closed  ", " In Progress ", ""],
            "non_string_col": [1, 2, 3, 4],  # This column should not be affected
        }
        input_df = pd.DataFrame(test_data)

        normalized_df = _normalize_strings(input_df)

        # Check that a copy is returned
        self.assertIsNot(input_df, normalized_df)

        # Check whitespace stripping
        pd.testing.assert_series_equal(
            normalized_df["comments"],
            pd.Series(["leading", "trailing", "both", "no space"], name="comments", dtype="string"),
        )
        pd.testing.assert_series_equal(
            normalized_df["work_notes"],
            pd.Series(["a", "b", "c", "d"], name="work_notes", dtype="string"),
        )
        pd.testing.assert_series_equal(
            normalized_df["state"],
            pd.Series(["New", "Closed", "In Progress", ""], name="state", dtype="string"),
        )

        # Check 'assigned_to' special handling
        expected_assigned_to = pd.Series(
            ["test", "Unassigned", "Unassigned", "Unassigned"], name="assigned_to", dtype="string"
        )
        pd.testing.assert_series_equal(normalized_df["assigned_to"], expected_assigned_to)

        # Check that columns not in STRING_COLS are untouched
        self.assertTrue("non_string_col" in normalized_df.columns)
        self.assertTrue(pd.api.types.is_integer_dtype(normalized_df["non_string_col"]))

        # Test with a DataFrame that has no columns from STRING_COLS
        no_string_cols_df = pd.DataFrame({"a": [1], "b": [2]})
        processed_df = _normalize_strings(no_string_cols_df.copy())
        pd.testing.assert_frame_equal(processed_df, no_string_cols_df)

        # Test with an empty DataFrame
        empty_df = pd.DataFrame()
        processed_empty_df = _normalize_strings(empty_df)
        pd.testing.assert_frame_equal(processed_empty_df, empty_df)

    def test_load_csv_no_chunking(self):
        """Test loading a CSV without chunking."""
        # All required columns are present in data.csv, so this should work
        df = load_csv(self.data_csv_path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)

        # Check that columns are what we expect
        self.assertEqual(list(df.columns), sorted(list(REQUIRED_HEADERS)))

        # Check normalization and special handling for 'assigned_to'
        self.assertEqual(df["sys_tags"][0], "tag1")
        self.assertEqual(df["assigned_to"][1], "Unassigned")
        self.assertEqual(df["state"][0], "Closed")

    def test_load_csv_with_chunking(self):
        """Test loading a CSV with chunking."""
        chunks = load_csv(self.data_csv_path, chunksize=1)
        self.assertTrue(hasattr(chunks, "__iter__"))

        chunk_list = list(chunks)
        self.assertEqual(len(chunk_list), 2)

        # Check first chunk
        df1 = chunk_list[0]
        self.assertIsInstance(df1, pd.DataFrame)
        self.assertEqual(len(df1), 1)
        self.assertEqual(df1["sys_tags"].iloc[0], "tag1")
        self.assertEqual(df1["assigned_to"].iloc[0], "user1")

        # Check second chunk
        df2 = chunk_list[1]
        self.assertIsInstance(df2, pd.DataFrame)
        self.assertEqual(len(df2), 1)
        self.assertEqual(df2["sys_tags"].iloc[0], "tag2")
        self.assertEqual(df2["assigned_to"].iloc[0], "Unassigned")

    def test_load_csv_usecols(self):
        """Test loading a CSV with usecols."""
        usecols = ["sys_tags", "assigned_to", "state"]
        df = load_csv(self.data_csv_path, usecols=usecols)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), usecols)
        self.assertEqual(len(df), 2)
        self.assertEqual(df["sys_tags"][0], "tag1")
        self.assertEqual(df["state"][1], "New")

    def test_load_csv_chunked_usecols(self):
        """Test loading a chunked CSV with usecols."""
        usecols = ["sys_tags", "assigned_to"]
        chunks = load_csv(self.data_csv_path, usecols=usecols, chunksize=1)
        chunk_list = list(chunks)
        self.assertEqual(len(chunk_list), 2)

        df1 = chunk_list[0]
        self.assertEqual(list(df1.columns), usecols)
        self.assertEqual(df1["sys_tags"].iloc[0], "tag1")

        df2 = chunk_list[1]
        self.assertEqual(list(df2.columns), usecols)
        self.assertEqual(df2["assigned_to"].iloc[0], "Unassigned")

    def test_load_csv_missing_headers_propagates_error(self):
        """Test that load_csv propagates MissingHeadersError."""
        with pytest.raises(MissingHeadersError):
            load_csv(self.invalid_csv_path)

    def test_load_csv_reorders_columns(self):
        """Test that load_csv reorders columns to match usecols order."""
        usecols = ["state", "assigned_to", "sys_tags"]
        df = load_csv(self.data_csv_path, usecols=usecols)
        self.assertEqual(list(df.columns), usecols)

    def test_load_csv_usecols_with_missing_required_headers(self):
        """Test that load_csv with usecols works on a file missing non-requested required headers."""
        # self.invalid_csv_path is missing some REQUIRED_HEADERS.
        # We select columns that are known to be present in the invalid file.
        present_cols = self.missing_headers[:2]
        df = load_csv(self.invalid_csv_path, usecols=present_cols)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), present_cols)
