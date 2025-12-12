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
