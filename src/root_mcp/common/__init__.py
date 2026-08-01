"""Common utilities shared between core and extended modes."""

from .cache import LRUCache
from .errors import (
    AnalysisError,
    FileOperationError,
    ROOTMCPError,
    SecurityError,
    ValidationError,
)
from .root_availability import get_root_features, get_root_version, is_root_available
from .utils import ensure_path_exists, format_bytes, sanitize_filename

__all__ = [
    "AnalysisError",
    "FileOperationError",
    "LRUCache",
    "ROOTMCPError",
    "SecurityError",
    "ValidationError",
    "ensure_path_exists",
    "format_bytes",
    "get_root_features",
    "get_root_version",
    "is_root_available",
    "sanitize_filename",
]
