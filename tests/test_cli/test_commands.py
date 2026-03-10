"""Unit tests for root-cli commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import json

from root_cli.main import cli

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "root_files"


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def data_path():
    """Return test data path."""
    return str(TEST_DATA_DIR)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "root_mcp_test"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# ============================================================================
# Test: ls command
# ============================================================================


class TestLsCommand:
    """Test ls command."""

    def test_ls_basic(self, runner, data_path):
        """Test basic ls command."""
        result = runner.invoke(cli, ["-d", data_path, "ls"])
        assert result.exit_code == 0
        assert "ROOT files" in result.output
        assert ".root" in result.output

    def test_ls_with_limit(self, runner, data_path):
        """Test ls with limit option."""
        result = runner.invoke(cli, ["-d", data_path, "ls", "--limit", "3"])
        assert result.exit_code == 0
        assert "Found" in result.output

    def test_ls_with_pattern(self, runner, data_path):
        """Test ls with pattern."""
        result = runner.invoke(cli, ["-d", data_path, "ls", "*.root"])
        assert result.exit_code == 0

    def test_ls_json_output(self, runner, data_path):
        """Test ls with JSON output."""
        result = runner.invoke(cli, ["-d", data_path, "--json", "ls"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "data" in data
        assert "files" in data["data"]
        assert "total_matched" in data["data"]


# ============================================================================
# Test: inspect command
# ============================================================================


class TestInspectCommand:
    """Test inspect command."""

    def test_inspect_basic(self, runner, data_path):
        """Test basic inspect command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "inspect", str(test_file)])
        assert result.exit_code == 0
        assert "File:" in result.output
        assert "TTrees" in result.output

    def test_inspect_json_output(self, runner, data_path):
        """Test inspect with JSON output."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "--json", "inspect", str(test_file)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "data" in data
        assert "trees" in data["data"]

    def test_inspect_nonexistent_file(self, runner, data_path):
        """Test inspect with nonexistent file."""
        result = runner.invoke(cli, ["-d", data_path, "inspect", "/nonexistent.root"])
        assert result.exit_code != 0


# ============================================================================
# Test: branches command
# ============================================================================


class TestBranchesCommand:
    """Test branches command."""

    def test_branches_basic(self, runner, data_path):
        """Test basic branches command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "branches", str(test_file), "events"])
        assert result.exit_code == 0
        assert "Tree:" in result.output
        assert "Branches" in result.output

    def test_branches_with_limit(self, runner, data_path):
        """Test branches with limit."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "branches", str(test_file), "events", "--limit", "5"]
        )
        assert result.exit_code == 0

    def test_branches_with_pattern(self, runner, data_path):
        """Test branches with pattern."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "branches", str(test_file), "events", "--pattern", "muon_*"]
        )
        assert result.exit_code == 0

    def test_branches_json_output(self, runner, data_path):
        """Test branches with JSON output."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "--json", "branches", str(test_file), "events"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "data" in data
        assert "branches" in data["data"]


# ============================================================================
# Test: validate command
# ============================================================================


class TestValidateCommand:
    """Test validate command."""

    def test_validate_valid_file(self, runner, data_path):
        """Test validate with valid file."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "validate", str(test_file)])
        assert result.exit_code == 0
        assert "Valid" in result.output or "Status" in result.output

    def test_validate_json_output(self, runner, data_path):
        """Test validate with JSON output."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "--json", "validate", str(test_file)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "data" in data


# ============================================================================
# Test: read command
# ============================================================================


class TestReadCommand:
    """Test read command."""

    def test_read_basic(self, runner, data_path):
        """Test basic read command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "read", str(test_file), "events", "met"])
        assert result.exit_code == 0
        assert "Read" in result.output

    def test_read_with_limit(self, runner, data_path):
        """Test read with limit."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "read", str(test_file), "events", "met", "--limit", "5"]
        )
        assert result.exit_code == 0

    def test_read_with_selection(self, runner, data_path):
        """Test read with selection."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            ["-d", data_path, "read", str(test_file), "events", "met", "--selection", "met > 50"],
        )
        assert result.exit_code == 0

    def test_read_json_output(self, runner, data_path):
        """Test read with JSON output."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "--json", "read", str(test_file), "events", "met"]
        )
        assert result.exit_code == 0


# ============================================================================
# Test: stats command
# ============================================================================


class TestStatsCommand:
    """Test stats command."""

    def test_stats_basic(self, runner, data_path):
        """Test basic stats command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "stats", str(test_file), "events", "met"])
        assert result.exit_code == 0
        assert "Statistics" in result.output
        assert "mean" in result.output.lower()

    def test_stats_multiple_branches(self, runner, data_path):
        """Test stats with multiple branches."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "stats", str(test_file), "events", "met", "met_phi"]
        )
        assert result.exit_code == 0

    def test_stats_with_selection(self, runner, data_path):
        """Test stats with selection."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            ["-d", data_path, "stats", str(test_file), "events", "met", "--selection", "met > 20"],
        )
        assert result.exit_code == 0


# ============================================================================
# Test: sample command
# ============================================================================


class TestSampleCommand:
    """Test sample command."""

    def test_sample_basic(self, runner, data_path):
        """Test basic sample command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "sample", str(test_file), "events"])
        assert result.exit_code == 0
        assert "Sampled" in result.output

    def test_sample_with_size(self, runner, data_path):
        """Test sample with size."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "sample", str(test_file), "events", "--size", "10"]
        )
        assert result.exit_code == 0

    def test_sample_random(self, runner, data_path):
        """Test sample with random method."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            [
                "-d",
                data_path,
                "sample",
                str(test_file),
                "events",
                "--method",
                "random",
                "--seed",
                "42",
            ],
        )
        assert result.exit_code == 0


# ============================================================================
# Test: histogram command
# ============================================================================


class TestHistogramCommand:
    """Test histogram command."""

    def test_histogram_basic(self, runner, data_path):
        """Test basic histogram command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(cli, ["-d", data_path, "histogram", str(test_file), "events", "met"])
        assert result.exit_code == 0
        assert "Histogram" in result.output
        assert "Statistics" in result.output

    def test_histogram_with_bins(self, runner, data_path):
        """Test histogram with custom bins."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "histogram", str(test_file), "events", "met", "--bins", "50"]
        )
        assert result.exit_code == 0

    def test_histogram_with_range(self, runner, data_path):
        """Test histogram with range."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            ["-d", data_path, "histogram", str(test_file), "events", "met", "--range", "0", "200"],
        )
        assert result.exit_code == 0

    def test_histogram_with_selection(self, runner, data_path):
        """Test histogram with selection."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            [
                "-d",
                data_path,
                "histogram",
                str(test_file),
                "events",
                "met",
                "--selection",
                "met > 20",
            ],
        )
        assert result.exit_code == 0

    def test_histogram_json_output(self, runner, data_path):
        """Test histogram with JSON output."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "--json", "histogram", str(test_file), "events", "met"]
        )
        assert result.exit_code == 0


# ============================================================================
# Test: histogram2d command
# ============================================================================


class TestHistogram2DCommand:
    """Test histogram2d command."""

    def test_histogram2d_basic(self, runner, data_path):
        """Test basic histogram2d command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "histogram2d", str(test_file), "events", "met", "met_phi"]
        )
        assert result.exit_code == 0
        assert "2D Histogram" in result.output

    def test_histogram2d_with_bins(self, runner, data_path):
        """Test histogram2d with custom bins."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            [
                "-d",
                data_path,
                "histogram2d",
                str(test_file),
                "events",
                "met",
                "met_phi",
                "--xbins",
                "30",
                "--ybins",
                "30",
            ],
        )
        assert result.exit_code == 0


# ============================================================================
# Test: correlation command
# ============================================================================


class TestCorrelationCommand:
    """Test correlation command."""

    def test_correlation_basic(self, runner, data_path):
        """Test basic correlation command."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli, ["-d", data_path, "correlation", str(test_file), "events", "met", "met_phi"]
        )
        assert result.exit_code == 0
        assert "correlation" in result.output.lower()

    def test_correlation_spearman(self, runner, data_path):
        """Test correlation with spearman method."""
        test_file = TEST_DATA_DIR / "sample_events.root"
        result = runner.invoke(
            cli,
            [
                "-d",
                data_path,
                "correlation",
                str(test_file),
                "events",
                "met",
                "met_phi",
                "--method",
                "spearman",
            ],
        )
        assert result.exit_code == 0


# ============================================================================
# Test: plot1d command
# ============================================================================


class TestPlot1DCommand:
    """Test plot1d command."""

    def test_plot1d_basic(self, runner, data_path, temp_output_dir):
        """Test basic plot1d command."""
        # First create a histogram
        test_file = TEST_DATA_DIR / "sample_events.root"
        hist_result = runner.invoke(
            cli, ["-d", data_path, "histogram", str(test_file), "events", "met"]
        )
        assert hist_result.exit_code == 0

        # Find the histogram JSON file
        hist_files = list(Path("/tmp/root_mcp").glob("*_hist.json"))
        if hist_files:
            hist_json = str(hist_files[0])
            output_plot = str(temp_output_dir / "test_plot.png")

            result = runner.invoke(cli, ["plot1d", hist_json, "-o", output_plot])
            assert result.exit_code == 0
            assert "Plot created" in result.output


# ============================================================================
# Test: info command
# ============================================================================


class TestInfoCommand:
    """Test info command."""

    def test_info_basic(self, runner):
        """Test basic info command."""
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "ROOT CLI" in result.output
        assert "Available commands" in result.output

    def test_info_json_output(self, runner):
        """Test info with JSON output."""
        result = runner.invoke(cli, ["--json", "info"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "name" in data
        assert "version" in data
        assert "commands" in data


# ============================================================================
# Test: CLI entry point
# ============================================================================


class TestCLIEntryPoint:
    """Test CLI entry point and help."""

    def test_cli_help(self, runner):
        """Test CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ROOT CLI" in result.output
        assert "Options:" in result.output

    def test_cli_version(self, runner):
        """Test CLI version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_command_help(self, runner):
        """Test individual command help."""
        result = runner.invoke(cli, ["ls", "--help"])
        assert result.exit_code == 0
        assert "List ROOT files" in result.output


# ============================================================================
# Test: Error handling
# ============================================================================


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_data_path(self, runner):
        """Test with invalid data path."""
        result = runner.invoke(cli, ["-d", "/nonexistent/path", "ls"])
        # Should handle gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "no files" in result.output.lower()
        )

    def test_invalid_command(self, runner):
        """Test invalid command."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

    def test_missing_required_argument(self, runner, data_path):
        """Test missing required argument."""
        result = runner.invoke(cli, ["-d", data_path, "read", "test.root"])
        assert result.exit_code != 0
