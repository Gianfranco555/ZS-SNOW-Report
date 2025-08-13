import os
import shutil
import unittest
import pandas as pd
import pytest
import numpy as np

from zn_report.io_loader import (
    _normalize_strings,
    read_csv_headers,
    validate_headers,
    ensure_headers_ok,
    load_csv,
)
from zn_report.exceptions import MissingHeadersError
from zn_report.constants import REQUIRED_HEADERS


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
        self.assertEqual(set(df.columns), set(REQUIRED_HEADERS))

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
