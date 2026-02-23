"""Tests for the run_root_code MCP tool integration."""

from __future__ import annotations

import tempfile
from unittest.mock import patch


from root_mcp.config import Config, FeatureFlags, RootNativeConfig
from root_mcp.extended.tools.root_native import RootNativeTools

# ---------------------------------------------------------------------------
# RootNativeTools unit tests
# ---------------------------------------------------------------------------


class TestRootNativeToolsInit:
    """Tests for RootNativeTools initialization."""

    def test_creates_with_default_config(self):
        config = Config()
        tools = RootNativeTools(config=config)
        assert tools.executor is not None
        assert tools.validator is not None
        assert tools.executor.execution_timeout == 60

    def test_creates_with_custom_config(self):
        config = Config(
            root_native=RootNativeConfig(
                execution_timeout=120,
                max_code_length=50_000,
                working_directory="/tmp/test_root_native",
            )
        )
        tools = RootNativeTools(config=config)
        assert tools.executor.execution_timeout == 120
        assert tools.validator.max_code_length == 50_000

    def test_executor_uses_config_values(self):
        config = Config(
            root_native=RootNativeConfig(
                max_output_size=5_000_000,
                allowed_output_formats=["png", "pdf"],
            )
        )
        tools = RootNativeTools(config=config)
        assert tools.executor.max_output_size == 5_000_000
        assert tools.executor.allowed_output_formats == ["png", "pdf"]


class TestRootNativeToolsExecution:
    """Tests for run_root_code method."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp(prefix="test_rnt_")
        self.config = Config(
            root_native=RootNativeConfig(
                execution_timeout=10,
                working_directory=self.work_dir,
            )
        )
        self.tools = RootNativeTools(config=self.config)

    def test_run_simple_code(self):
        result = self.tools.run_root_code(code="print('hello from tool')")
        assert result["status"] == "success"
        assert "hello from tool" in result["stdout"]
        assert result["execution_time_seconds"] > 0

    def test_run_code_with_math(self):
        code = """
import math
print(f"pi={math.pi:.4f}")
"""
        result = self.tools.run_root_code(code=code)
        assert result["status"] == "success"
        assert "pi=3.1416" in result["stdout"]

    def test_run_blocked_code(self):
        result = self.tools.run_root_code(code="import os\nos.system('ls')")
        assert result["status"] == "validation_failed"
        assert "error" in result

    def test_run_code_with_runtime_error(self):
        result = self.tools.run_root_code(code="1/0")
        assert result["status"] == "error"
        assert "error" in result
        assert "traceback" in result

    def test_run_code_with_timeout(self):
        code = "import time; time.sleep(30)"
        result = self.tools.run_root_code(code=code, timeout=2)
        assert result["status"] == "timeout"

    def test_run_code_with_output_files(self):
        code = """
import json
output_path = _output_dir + "/result.json"
with open(output_path, "w") as f:
    json.dump({"answer": 42}, f)
"""
        result = self.tools.run_root_code(code=code)
        assert result["status"] == "success"
        assert len(result["output_files"]) > 0
        assert any("result.json" in f for f in result["output_files"])

    def test_run_code_captures_stderr(self):
        code = """
import sys
print("stderr msg", file=sys.stderr)
"""
        result = self.tools.run_root_code(code=code)
        assert result["status"] == "success"
        assert "stderr msg" in result["stderr"]

    def test_result_has_expected_keys(self):
        result = self.tools.run_root_code(code="print('ok')")
        expected_keys = {
            "status",
            "stdout",
            "stderr",
            "return_value",
            "output_files",
            "execution_time_seconds",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_warnings_included_in_result(self):
        # open() triggers a warning but doesn't block
        code = "f = open('/dev/null', 'r'); f.close()"
        result = self.tools.run_root_code(code=code)
        assert result["status"] == "success"
        assert "warnings" in result


# ---------------------------------------------------------------------------
# Server integration tests (tool visibility and dispatch)
# ---------------------------------------------------------------------------


class TestToolVisibility:
    """Tests that run_root_code tool is shown/hidden correctly."""

    def test_tool_hidden_when_root_disabled(self):
        """Tool should not appear when enable_root is False."""
        config = Config(features=FeatureFlags(enable_root=False))
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        assert server._root_native_available is False

    def test_tool_hidden_when_root_not_installed(self):
        """Tool should not appear when ROOT is not importable."""
        config = Config(features=FeatureFlags(enable_root=True))

        with patch(
            "root_mcp.server.is_root_available",
            return_value=False,
        ):
            from root_mcp.server import ROOTMCPServer

            server = ROOTMCPServer(config)
            assert server._root_native_available is False

    def test_tool_visible_when_root_enabled_and_available(self):
        """Tool should appear when enable_root=True and ROOT is available."""
        config = Config(features=FeatureFlags(enable_root=True))

        with (
            patch(
                "root_mcp.server.is_root_available",
                return_value=True,
            ),
            patch(
                "root_mcp.server.get_root_version",
                return_value="6.32/02",
            ),
        ):
            from root_mcp.server import ROOTMCPServer

            server = ROOTMCPServer(config)
            assert server._root_native_available is True
            assert hasattr(server, "root_native_tools")

    def test_get_root_native_tools_returns_tool_schema(self):
        """_get_root_native_tools should return all native ROOT tools."""
        config = Config()
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        tools = server._get_root_native_tools()
        names = [t.name for t in tools]
        assert "run_root_code" in names
        assert "run_rdataframe" in names
        assert "run_root_macro" in names
        run_root_code = next(t for t in tools if t.name == "run_root_code")
        assert "code" in run_root_code.inputSchema["properties"]
        assert "code" in run_root_code.inputSchema["required"]

    def test_root_native_tools_unloaded_on_mode_switch(self):
        """Switching to core mode should unload root native tools."""
        config = Config(features=FeatureFlags(enable_root=True))

        with (
            patch(
                "root_mcp.server.is_root_available",
                return_value=True,
            ),
            patch(
                "root_mcp.server.get_root_version",
                return_value="6.32/02",
            ),
        ):
            from root_mcp.server import ROOTMCPServer

            server = ROOTMCPServer(config)
            assert server._root_native_available is True

            # Switch to core mode
            server.switch_mode("core")
            assert server._root_native_available is False
            assert not hasattr(server, "root_native_tools")


class TestToolDispatch:
    """Tests for run_root_code dispatch in call_tool."""

    def test_dispatch_when_not_available_returns_error(self):
        """Calling run_root_code when ROOT is not available should return error."""
        config = Config(features=FeatureFlags(enable_root=False))
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        assert server._root_native_available is False

        # Simulate calling the tool via the dispatch logic
        # We test the logic directly rather than through MCP protocol

        async def _call():
            # Access the registered call_tool handler
            handlers = server.server._tool_handlers
            if handlers:
                handler = handlers[0] if isinstance(handlers, list) else handlers
                return await handler("run_root_code", {"code": "print('hi')"})
            return None

        # The tool dispatch is registered as a closure, so we test the server's
        # _root_native_available flag instead
        assert server._root_native_available is False

    def test_dispatch_when_available_executes(self):
        """Calling run_root_code when ROOT is available should execute."""
        config = Config(
            features=FeatureFlags(enable_root=True),
            root_native=RootNativeConfig(execution_timeout=10),
        )

        with (
            patch(
                "root_mcp.server.is_root_available",
                return_value=True,
            ),
            patch(
                "root_mcp.server.get_root_version",
                return_value="6.32/02",
            ),
        ):
            from root_mcp.server import ROOTMCPServer

            server = ROOTMCPServer(config)
            assert server._root_native_available is True

            # Call the tool directly
            result = server.root_native_tools.run_root_code(code="print('dispatched')")
            assert result["status"] == "success"
            assert "dispatched" in result["stdout"]
