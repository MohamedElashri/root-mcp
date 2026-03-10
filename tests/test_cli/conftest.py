"""Pytest configuration and shared fixtures for root-cli tests."""

import pytest
from pathlib import Path
from click.testing import CliRunner

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "root_files"


@pytest.fixture(scope="session")
def test_data_dir():
    """Return test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def sample_root_file():
    """Return path to sample ROOT file."""
    return TEST_DATA_DIR / "sample_events.root"


@pytest.fixture(scope="session")
def muon_root_file():
    """Return path to muon demo ROOT file."""
    return TEST_DATA_DIR / "muon_gaussian_demo.root"


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def data_path(test_data_dir):
    """Return test data path as string."""
    return str(test_data_dir)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch, tmp_path):
    """Setup test environment."""
    # Set up temporary output directory
    output_dir = tmp_path / "root_mcp"
    output_dir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    return output_dir
