"""Read the package version generated from pyproject.toml at installation."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed distribution version, or a fallback for an uninstalled source tree."""
    try:
        return version("root-mcp")
    except PackageNotFoundError:
        return "0.0.0"
