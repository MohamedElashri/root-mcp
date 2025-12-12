"""
ROOT-MCP: Production-grade MCP server for CERN ROOT file analysis.

Provides AI models with safe, high-level access to ROOT files through the
Model Context Protocol.
"""

__version__ = "1.0.0"
__author__ = "ROOT-MCP Team"

from .config import Config, load_config

__all__ = ["Config", "load_config", "__version__"]
