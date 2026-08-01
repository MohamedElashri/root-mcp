"""Core I/O operations for ROOT files."""

__all__ = [
    "DataExporter",
    "FileCache",
    "FileManager",
    "HistogramReader",
    "PathValidator",
    "TreeReader",
]


def __getattr__(name: str):
    """Load I/O helpers lazily so validators stay lightweight to import."""
    if name in {"FileManager", "FileCache"}:
        from .file_manager import FileCache, FileManager

        return {"FileManager": FileManager, "FileCache": FileCache}[name]
    if name in {"TreeReader", "HistogramReader"}:
        from .readers import HistogramReader, TreeReader

        return {"TreeReader": TreeReader, "HistogramReader": HistogramReader}[name]
    if name == "PathValidator":
        from .validators import PathValidator

        return PathValidator
    if name == "DataExporter":
        from .exporters import DataExporter

        return DataExporter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
