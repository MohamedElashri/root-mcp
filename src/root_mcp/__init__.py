"""
ROOT-MCP: Production-grade MCP server for CERN ROOT file analysis.

Provides AI models with safe, high-level access to ROOT files through the
Model Context Protocol.
"""

from ._version import get_version
from .config import Config, load_config

__version__ = get_version()
__author__ = "Mohamed Elashri"


__all__ = ["Config", "__version__", "load_config"]
