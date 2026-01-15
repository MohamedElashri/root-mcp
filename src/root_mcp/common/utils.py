"""Common utility functions."""

from pathlib import Path


def format_bytes(size_bytes: int) -> str:
    """
    Format bytes as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def ensure_path_exists(path: str | Path) -> Path:
    """
    Ensure a path exists, creating parent directories if needed.

    Args:
        path: Path to ensure exists

    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    sanitized = sanitized.strip(". ")
    return sanitized or "unnamed"
