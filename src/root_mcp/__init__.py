"""
ROOT-MCP: Production-grade MCP server for CERN ROOT file analysis.

Provides AI models with safe, high-level access to ROOT files through the
Model Context Protocol.
"""

from importlib.metadata import PackageNotFoundError, version as _dist_version
from .config import Config, load_config


def _get_version() -> str:
    try:
        return _dist_version("root-mcp")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
__author__ = "Mohamed Elashri"


__all__ = ["Config", "load_config", "__version__"]
