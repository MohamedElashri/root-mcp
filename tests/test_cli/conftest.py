"""Pytest configuration and shared fixtures for root-cli tests."""

from pathlib import Path

import pytest
from click.testing import CliRunner

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "root_files"


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "requires_root_files: mark test as requiring ROOT data files"
    )


def pytest_collection_modifyitems(config, items):
    """Skip CLI tests if ROOT data files are not available (e.g., in CI)."""
    if not TEST_DATA_DIR.exists() or not list(TEST_DATA_DIR.glob("*.root")):
        skip_root_files = pytest.mark.skip(
            reason="ROOT test data files not available (gitignored in CI)"
        )
        for item in items:
            if "test_cli" in str(item.fspath):
                item.add_marker(skip_root_files)


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
    output_dir = tmp_path / "root_mcp_test"
    output_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    return output_dir
