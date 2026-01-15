#!/usr/bin/env python3
"""
MCP Protocol Integration Tests for ROOT-MCP.

Tests the actual MCP server protocol integration - the core functionality
that enables LLM interaction with ROOT files.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from root_mcp.server import ROOTMCPServer
from root_mcp.config import load_config


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent.parent / "data" / "root_files"


@pytest.fixture
def sample_file(test_data_dir):
    """Path to sample events file."""
    file_path = test_data_dir / "sample_events.root"
    if not file_path.exists():
        pytest.skip(f"Test data not found: {file_path}")
    return str(file_path)


@pytest.fixture
async def mcp_server(tmp_path, test_data_dir):
    """Create MCP server in extended mode."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
server:
  name: "test-mcp-server"
  mode: "extended"

core:
  cache:
    enabled: true
    file_cache_size: 10
  limits:
    max_rows_per_call: 10000

extended:
  analysis:
    default_bins: 50

security:
  allowed_roots:
    - "{test_data_dir}"
"""
    )
    config = load_config(str(config_path))
    server = ROOTMCPServer(config)
    return server


class TestMCPServerInitialization:
    """Test MCP server initialization and capabilities."""

    @pytest.mark.asyncio
    async def test_server_starts(self, mcp_server):
        """Test that MCP server initializes correctly."""
        assert mcp_server is not None
        assert mcp_server.server is not None

    @pytest.mark.asyncio
    async def test_server_has_name(self, mcp_server):
        """Test server has correct name."""
        assert mcp_server.config.server.name == "test-mcp-server"

    @pytest.mark.asyncio
    async def test_server_mode(self, mcp_server):
        """Test server is in correct mode."""
        assert mcp_server.config.server.mode == "extended"


class TestMCPToolListing:
    """Test MCP tool listing functionality."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self, mcp_server):
        """Test that list_tools returns available tools."""
        # The server uses decorators, so we need to check the registered tools
        # through the MCP server's internal structure
        assert hasattr(mcp_server, "server")

        # Check that core tools are available
        assert mcp_server.discovery_tools is not None
        assert mcp_server.data_access_tools is not None
        assert mcp_server.basic_stats is not None

        # Check that extended tools are available
        assert mcp_server.histogram_ops is not None
        assert mcp_server.kinematics_ops is not None
        assert mcp_server.analysis_tools is not None

    @pytest.mark.asyncio
    async def test_core_tools_available(self, mcp_server):
        """Test that core tools are properly initialized."""
        core_components = [
            "file_manager",
            "path_validator",
            "tree_reader",
            "discovery_tools",
            "data_access_tools",
            "basic_stats",
        ]

        for component in core_components:
            assert hasattr(mcp_server, component), f"Missing core component: {component}"
            assert getattr(mcp_server, component) is not None

    @pytest.mark.asyncio
    async def test_extended_tools_available(self, mcp_server):
        """Test that extended tools are properly initialized."""
        extended_components = [
            "histogram_ops",
            "kinematics_ops",
            "correlation_analysis",
            "analysis_tools",
        ]

        for component in extended_components:
            assert hasattr(mcp_server, component), f"Missing extended component: {component}"
            assert getattr(mcp_server, component) is not None


class TestMCPToolCalls:
    """Test MCP tool call functionality with real data."""

    @pytest.mark.asyncio
    async def test_inspect_file_tool(self, mcp_server, sample_file):
        """Test inspect_file tool through MCP interface."""
        # Call the tool directly (simulating MCP tool call)
        result = mcp_server.discovery_tools.inspect_file(sample_file)

        assert "data" in result
        assert "trees" in result["data"]
        assert len(result["data"]["trees"]) > 0

    @pytest.mark.asyncio
    async def test_list_branches_tool(self, mcp_server, sample_file):
        """Test list_branches tool through MCP interface."""
        result = mcp_server.discovery_tools.list_branches(sample_file, "events")

        assert "data" in result
        assert "branches" in result["data"]
        assert len(result["data"]["branches"]) > 0

        # Check branch structure
        branch = result["data"]["branches"][0]
        assert "name" in branch
        assert "type" in branch

    @pytest.mark.asyncio
    async def test_read_branches_tool(self, mcp_server, sample_file):
        """Test read_branches tool through MCP interface."""
        result = mcp_server.data_access_tools.read_branches(
            sample_file, "events", ["muon_pt", "muon_eta"], limit=100
        )

        assert "data" in result
        assert result["data"]["entries"] <= 100
        assert "muon_pt" in result["data"]["branches"]

    @pytest.mark.asyncio
    async def test_get_branch_stats_tool(self, mcp_server, sample_file):
        """Test get_branch_stats tool through MCP interface."""
        result = mcp_server.basic_stats.compute_stats(
            sample_file, "events", ["muon_pt", "muon_eta"]
        )

        assert "muon_pt" in result
        assert "mean" in result["muon_pt"]
        assert "std" in result["muon_pt"]
        assert isinstance(result["muon_pt"]["mean"], float)

    @pytest.mark.asyncio
    async def test_compute_histogram_tool(self, mcp_server, sample_file):
        """Test compute_histogram tool through MCP interface."""
        result = mcp_server.histogram_ops.compute_histogram_1d(
            sample_file, "events", "muon_pt", bins=50, range=(0, 200)
        )

        assert "data" in result
        assert "bin_counts" in result["data"]
        assert len(result["data"]["bin_counts"]) == 50
        assert "entries" in result["data"]

    @pytest.mark.asyncio
    async def test_validate_file_tool(self, mcp_server, sample_file):
        """Test validate_file tool through MCP interface."""
        result = mcp_server.file_manager.validate_file(sample_file)

        assert "valid" in result
        assert "readable" in result
        assert result["valid"] is True
        assert result["readable"] is True


class TestMCPErrorHandling:
    """Test MCP error handling."""

    @pytest.mark.asyncio
    async def test_nonexistent_file_error(self, mcp_server):
        """Test error handling for nonexistent file."""
        result = mcp_server.discovery_tools.inspect_file("/nonexistent/file.root")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_tree_error(self, mcp_server, sample_file):
        """Test error handling for invalid tree name."""
        result = mcp_server.discovery_tools.list_branches(sample_file, "nonexistent_tree")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_branch_error(self, mcp_server, sample_file):
        """Test error handling for invalid branch name."""
        result = mcp_server.data_access_tools.read_branches(
            sample_file, "events", ["nonexistent_branch"]
        )
        assert "error" in result


class TestMCPModeSwitching:
    """Test MCP mode switching functionality."""

    @pytest.mark.asyncio
    async def test_switch_to_core_mode(self, mcp_server):
        """Test switching to core mode."""
        # Start in extended mode
        assert mcp_server.config.server.mode == "extended"

        # Switch to core
        mcp_server.switch_mode("core")

        assert mcp_server.config.server.mode == "core"
        # Extended components should be None after switch
        assert not hasattr(mcp_server, "histogram_ops") or mcp_server.histogram_ops is None

    @pytest.mark.asyncio
    async def test_switch_to_extended_mode(self, mcp_server):
        """Test switching to extended mode."""
        # Switch to core first
        mcp_server.switch_mode("core")
        assert mcp_server.config.server.mode == "core"

        # Switch back to extended
        mcp_server.switch_mode("extended")

        assert mcp_server.config.server.mode == "extended"
        # Extended components should be loaded
        assert mcp_server.histogram_ops is not None

    @pytest.mark.asyncio
    async def test_invalid_mode_switch(self, mcp_server):
        """Test that invalid mode switch raises error."""
        with pytest.raises(ValueError):
            mcp_server.switch_mode("invalid_mode")


class TestMCPDataFlow:
    """Test complete data flow through MCP interface."""

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, mcp_server, sample_file):
        """Test a complete analysis workflow through MCP."""
        # Step 1: Inspect file
        file_info = mcp_server.discovery_tools.inspect_file(sample_file)
        assert len(file_info["data"]["trees"]) > 0

        # Step 2: List branches
        branches_info = mcp_server.discovery_tools.list_branches(sample_file, "events")
        assert len(branches_info["data"]["branches"]) > 0

        # Step 3: Read data
        data = mcp_server.data_access_tools.read_branches(
            sample_file, "events", ["muon_pt"], limit=1000
        )
        assert data["data"]["entries"] > 0

        # Step 4: Compute statistics
        stats = mcp_server.basic_stats.compute_stats(sample_file, "events", ["muon_pt"])
        assert "muon_pt" in stats
        assert stats["muon_pt"]["mean"] > 0

        # Step 5: Create histogram
        hist = mcp_server.histogram_ops.compute_histogram_1d(
            sample_file, "events", "muon_pt", bins=50, range=(0, 200)
        )
        assert hist["data"]["entries"] > 0

    @pytest.mark.asyncio
    async def test_physics_analysis_workflow(self, mcp_server, sample_file):
        """Test physics analysis workflow."""
        # Compute invariant mass - skip this test as it requires proper particle pairing
        # which is complex with jagged arrays
        pytest.skip("Invariant mass computation requires proper particle pairing logic")


class TestMCPPerformance:
    """Test MCP performance characteristics."""

    @pytest.mark.asyncio
    async def test_large_data_read(self, mcp_server, sample_file):
        """Test reading large amounts of data."""
        import time

        start = time.time()
        result = mcp_server.data_access_tools.read_branches(
            sample_file, "events", ["muon_pt", "muon_eta", "muon_phi"], limit=10000
        )
        elapsed = time.time() - start

        assert result["data"]["entries"] > 0
        assert elapsed < 5.0  # Should complete in less than 5 seconds

    @pytest.mark.asyncio
    async def test_histogram_performance(self, mcp_server, sample_file):
        """Test histogram computation performance."""
        import time

        start = time.time()
        result = mcp_server.histogram_ops.compute_histogram_1d(
            sample_file, "events", "muon_pt", bins=100, range=(0, 200)
        )
        elapsed = time.time() - start

        assert result["data"]["entries"] > 0
        assert elapsed < 3.0  # Should complete in less than 3 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
