"""Data access tools for reading TTree data."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.io.file_manager import FileManager
    from root_mcp.io.validators import PathValidator
    from root_mcp.io.readers import TreeReader

logger = logging.getLogger(__name__)


class DataAccessTools:
    """Tools for accessing TTree data."""

    def __init__(
        self,
        config: Config,
        file_manager: FileManager,
        path_validator: PathValidator,
        tree_reader: TreeReader,
    ):
        """
        Initialize data access tools.

        Args:
            config: Server configuration
            file_manager: File manager instance
            path_validator: Path validator instance
            tree_reader: Tree reader instance
        """
        self.config = config
        self.file_manager = file_manager
        self.path_validator = path_validator
        self.tree_reader = tree_reader

    def read_branches(
        self,
        path: str,
        tree: str,
        branches: list[str],
        selection: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        flatten: bool = False,
    ) -> dict[str, Any]:
        """
        Read branch data from a TTree.

        Args:
            path: File path
            tree: Tree name
            branches: List of branch names
            selection: Optional cut expression
            limit: Maximum entries to return
            offset: Number of entries to skip
            flatten: Flatten jagged arrays

        Returns:
            Branch data and metadata
        """
        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Validate limit
        if limit is None:
            limit = self.config.analysis.default_read_limit
        if limit > self.config.limits.max_rows_per_call:
            return {
                "error": "limit_exceeded",
                "message": (
                    f"Requested limit ({limit}) exceeds maximum "
                    f"({self.config.limits.max_rows_per_call})"
                ),
                "suggestion": f"Use limit <= {self.config.limits.max_rows_per_call} or apply selection",
            }

        # Read data
        try:
            result = self.tree_reader.read_branches(
                path=str(validated_path),
                tree_name=tree,
                branches=branches,
                selection=selection,
                limit=limit,
                offset=offset,
                flatten=flatten,
            )
        except KeyError as e:
            return {
                "error": "branch_not_found",
                "message": str(e),
                "suggestion": "Use list_branches() to see available branches",
            }
        except ValueError as e:
            return {
                "error": "invalid_selection",
                "message": str(e),
                "suggestion": "Check ROOT expression syntax (e.g., 'pt > 20 && abs(eta) < 2.4')",
            }
        except Exception as e:
            logger.error(f"Failed to read branches: {e}")
            return {
                "error": "read_error",
                "message": f"Failed to read data: {e}",
            }

        # Add suggestions
        suggestions = []
        if result["metadata"]["truncated"]:
            next_offset = offset + result["data"]["entries"]
            suggestions.append(f"Use offset={next_offset} to get next page")

        if result["data"]["is_jagged"]:
            suggestions.append("Data has variable-length arrays - use flatten=true for flat output")

        entries_selected = result["metadata"]["entries_selected"]
        entries_scanned = result["metadata"]["entries_scanned"]
        if entries_selected < entries_scanned * 0.1:
            suggestions.append(
                f"Only {entries_selected}/{entries_scanned} entries pass selection - "
                "consider compute_histogram() for full dataset analysis"
            )

        result["suggestions"] = suggestions

        return result

    def sample_tree(
        self,
        path: str,
        tree: str,
        size: int = 100,
        method: str = "first",
        branches: list[str] | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Get a sample from a tree.

        Args:
            path: File path
            tree: Tree name
            size: Sample size
            method: "first" or "random"
            branches: Branches to include (None = all)
            seed: Random seed

        Returns:
            Sample data and metadata
        """
        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Validate size
        if size > 10_000:
            return {
                "error": "limit_exceeded",
                "message": f"Sample size ({size}) exceeds maximum (10,000)",
                "suggestion": "Use size <= 10000",
            }

        # Get sample
        try:
            result = self.tree_reader.sample_tree(
                path=str(validated_path),
                tree_name=tree,
                size=size,
                method=method,
                branches=branches,
                seed=seed,
            )
        except ValueError as e:
            return {
                "error": "invalid_parameter",
                "message": str(e),
            }
        except Exception as e:
            return {
                "error": "read_error",
                "message": f"Failed to sample tree: {e}",
            }

        # Add suggestions
        suggestions = [
            "Use this sample to understand data structure before full reads",
            "Use read_branches() with selection to get filtered data",
        ]
        result["suggestions"] = suggestions

        return result

    def get_branch_stats(
        self,
        path: str,
        tree: str,
        branches: list[str],
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute statistics for branches.

        Args:
            path: File path
            tree: Tree name
            branches: Branches to analyze
            selection: Optional cut expression

        Returns:
            Branch statistics
        """
        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Compute stats
        try:
            stats = self.tree_reader.compute_branch_stats(
                path=str(validated_path),
                tree_name=tree,
                branches=branches,
                selection=selection,
            )
        except Exception as e:
            return {
                "error": "computation_error",
                "message": f"Failed to compute statistics: {e}",
            }

        return {
            "data": {
                "statistics": stats,
            },
            "metadata": {
                "operation": "get_branch_stats",
                "branches": branches,
                "selection": selection,
            },
            "suggestions": [
                "Use these statistics to choose histogram ranges",
                "Min/max values help identify outliers",
            ],
        }
