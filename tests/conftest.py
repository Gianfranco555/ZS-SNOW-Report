import pandas as pd
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def sample_csv_path(data_dir: Path) -> Path:
    """Return the path to the sample incidents CSV file."""
    return data_dir / "sample_incidents.csv"

@pytest.fixture(scope="session")
def shared_df(sample_csv_path: Path) -> pd.DataFrame:
    """
    Provides a shared, session-scoped DataFrame loaded from the sample CSV.
    This ensures that the baseline data is consistent for all tests that use it.
    """
    return pd.read_csv(sample_csv_path)
