"""I/O layer for safe ROOT file access."""

from .file_manager import FileManager
from .readers import TreeReader, HistogramReader
from .validators import PathValidator, SecurityError

__all__ = [
    "FileManager",
    "TreeReader",
    "HistogramReader",
    "PathValidator",
    "SecurityError",
]
