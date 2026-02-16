"""Common utilities shared between core and extended modes."""

from .cache import LRUCache
from .errors import (
    ROOTMCPError,
    SecurityError,
    ValidationError,
    FileOperationError,
    AnalysisError,
)
from .root_availability import is_root_available, get_root_version, get_root_features
from .utils import format_bytes, ensure_path_exists, sanitize_filename

__all__ = [
    "LRUCache",
    "ROOTMCPError",
    "SecurityError",
    "ValidationError",
    "FileOperationError",
    "AnalysisError",
    "format_bytes",
    "ensure_path_exists",
    "sanitize_filename",
    "is_root_available",
    "get_root_version",
    "get_root_features",
]
