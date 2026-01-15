"""Data export functionality for ROOT files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import awkward as ak

if TYPE_CHECKING:
    from root_mcp.config import Config

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Export TTree data to various formats.

    Supports JSON, CSV, and Parquet exports with compression options.
    """

    def __init__(self, config: Config):
        """
        Initialize data exporter.

        Args:
            config: Server configuration
        """
        self.config = config

    def export_to_json(
        self,
        data: ak.Array,
        output_path: str | Path,
        compress: bool = False,
    ) -> dict[str, Any]:
        """
        Export data to JSON format.

        Args:
            data: Awkward array data
            output_path: Output file path
            compress: Whether to compress output

        Returns:
            Export metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to list of records
        records = ak.to_list(data)

        # Determine file mode
        if compress:
            import gzip

            output_path = output_path.with_suffix(output_path.suffix + ".gz")
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)

        size_bytes = output_path.stat().st_size
        entries_written = len(records) if isinstance(records, list) else 1

        logger.info(f"Exported {entries_written} entries to JSON: {output_path}")

        return {
            "output_path": str(output_path),
            "format": "json",
            "entries_written": entries_written,
            "size_bytes": size_bytes,
            "compressed": compress,
        }

    def export_to_csv(
        self,
        data: ak.Array,
        output_path: str | Path,
        compress: bool = False,
    ) -> dict[str, Any]:
        """
        Export data to CSV format.

        Args:
            data: Awkward array data
            output_path: Output file path
            compress: Whether to compress output

        Returns:
            Export metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to pandas DataFrame
        df = ak.to_dataframe(data)

        # Determine compression
        compression = "gzip" if compress else None
        if compress:
            output_path = output_path.with_suffix(output_path.suffix + ".gz")

        # Write to CSV
        df.to_csv(output_path, index=False, compression=compression)

        size_bytes = output_path.stat().st_size
        entries_written = len(df)

        logger.info(f"Exported {entries_written} entries to CSV: {output_path}")

        return {
            "output_path": str(output_path),
            "format": "csv",
            "entries_written": entries_written,
            "size_bytes": size_bytes,
            "compressed": compress,
        }

    def export_to_parquet(
        self,
        data: ak.Array,
        output_path: str | Path,
        compression: str = "snappy",
    ) -> dict[str, Any]:
        """
        Export data to Parquet format.

        Args:
            data: Awkward array data
            output_path: Output file path
            compression: Compression algorithm (snappy, gzip, brotli, none)

        Returns:
            Export metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to pandas DataFrame
        df = ak.to_dataframe(data)

        # Write to Parquet
        df.to_parquet(
            output_path,
            compression=compression if compression != "none" else None,
            index=False,
        )

        size_bytes = output_path.stat().st_size
        entries_written = len(df)

        logger.info(f"Exported {entries_written} entries to Parquet: {output_path}")

        return {
            "output_path": str(output_path),
            "format": "parquet",
            "entries_written": entries_written,
            "size_bytes": size_bytes,
            "compression": compression,
        }

    def export(
        self,
        data: ak.Array,
        output_path: str | Path,
        format: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Export data to specified format.

        Args:
            data: Awkward array data
            output_path: Output file path
            format: Export format (json, csv, parquet)
            **kwargs: Format-specific options

        Returns:
            Export metadata

        Raises:
            ValueError: If format is not supported
        """
        format = format.lower()

        if format == "json":
            return self.export_to_json(data, output_path, **kwargs)
        elif format == "csv":
            return self.export_to_csv(data, output_path, **kwargs)
        elif format == "parquet":
            return self.export_to_parquet(data, output_path, **kwargs)
        else:
            raise ValueError(
                f"Unsupported export format: {format}. "
                f"Supported formats: {self.config.output.allowed_formats}"
            )
