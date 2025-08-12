import os
import shutil
import unittest
import pandas as pd
import pytest

from zn_report.io_loader import (
    read_csv_headers,
    validate_headers,
    ensure_headers_ok,
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

        pd.DataFrame(columns=self.valid_headers).to_csv(
            self.valid_csv_path, index=False
        )
        pd.DataFrame(columns=self.missing_headers).to_csv(
            self.invalid_csv_path, index=False
        )
        with open(self.empty_csv_path, "w") as f:
            f.write("")

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
