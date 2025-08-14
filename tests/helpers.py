"""Shared helper functions for the test suite."""

import hashlib
from pathlib import Path
import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"


def get_file_hash(path: Path) -> str:
    """Computes the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_golden_file_hash(generated_path: Path, test_name: str):
    """
    Checks a generated file's hash against its golden hash file.

    If the golden file does not exist, it's created. The test_name should
    be the name of the artifact, e.g., "report.pdf" or "chart_open_by_state.png".
    The hash file will be named `{test_name}.sha256`.
    """
    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / f"{test_name}.sha256"
    generated_hash = get_file_hash(generated_path)

    if not golden_path.exists():
        golden_path.write_text(generated_hash)
        pytest.skip(
            f"Golden file '{golden_path.name}' created. Please review and commit."
        )

    expected_hash = golden_path.read_text().strip()
    assert generated_hash == expected_hash, f"Hash mismatch for {test_name}"
