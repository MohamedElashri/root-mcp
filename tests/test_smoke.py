"""Smoke tests for ROOT-MCP."""

from root_mcp.config import load_config
from root_mcp.server import ROOTMCPServer


def test_config_loads():
    """Test that configuration loads successfully."""
    config = load_config()
    assert config is not None
    assert config.server.name == "root-mcp"
    assert config.server.mode in ["core", "extended"]


def test_server_initializes_extended_mode():
    """Test that server initializes in extended mode."""
    config = load_config()
    config.server.mode = "extended"

    server = ROOTMCPServer(config)

    # Server should initialize (may fall back to core if dependencies missing)
    assert server is not None
    assert server.current_mode in ["core", "extended"]

    # Core components should always be loaded
    assert hasattr(server, "file_manager")
    assert hasattr(server, "path_validator")
    assert hasattr(server, "tree_reader")
    assert hasattr(server, "basic_stats")


def test_server_initializes_core_mode():
    """Test that server initializes in core mode."""
    config = load_config()
    config.server.mode = "core"

    server = ROOTMCPServer(config)

    assert server is not None
    assert server.current_mode == "core"
    assert server._extended_components_loaded is False

    # Core components should be loaded
    assert hasattr(server, "file_manager")
    assert hasattr(server, "path_validator")
    assert hasattr(server, "tree_reader")
    assert hasattr(server, "basic_stats")


def test_mode_switching():
    """Test runtime mode switching."""
    config = load_config()
    config.server.mode = "core"

    server = ROOTMCPServer(config)
    assert server.current_mode == "core"

    # Try switching to extended mode
    result = server.switch_mode("extended")
    assert result["status"] in ["success", "error"]

    # If successful, verify extended components loaded
    if result["status"] == "success":
        assert server.current_mode == "extended"
        assert server._extended_components_loaded is True

        # Switch back to core
        result = server.switch_mode("core")
        assert result["status"] == "success"
        assert server.current_mode == "core"
        assert server._extended_components_loaded is False


def test_import_root_mcp() -> None:
    import root_mcp

    assert isinstance(root_mcp.__version__, str)


def test_package_version_matches_distribution_when_installed() -> None:
    from importlib.metadata import PackageNotFoundError, version as dist_version

    import root_mcp

    try:
        assert root_mcp.__version__ == dist_version("root-mcp")
    except PackageNotFoundError:
        assert root_mcp.__version__ == "0.0.0"


def test_server_entrypoint_importable() -> None:
    from root_mcp.server import main

    assert callable(main)
