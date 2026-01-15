"""Readers for TTree and histogram data."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

logger = logging.getLogger(__name__)


class TreeReader:
    """
    High-level interface for reading TTree data.

    Provides safe, efficient access to TTree branches with chunking,
    filtering, and pagination.
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize TreeReader.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def read_branches(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        selection: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        flatten: bool = False,
        defines: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Read branch data from a TTree.

        Args:
            path: File path
            tree_name: Tree name
            branches: List of branch names to read (can include derived branches from defines)
            selection: Optional ROOT-style cut expression
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            flatten: Flatten jagged arrays
            defines: Optional derived variable definitions {name: expression}

        Returns:
            Dictionary with data and metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Get available branches from tree
        available_branches = set(tree.keys())

        # Determine which branches are physical vs derived
        defined_branches = set(defines.keys()) if defines else set()
        physical_branches_requested = []
        derived_branches_requested = []

        # Validate all requested branches exist (either in tree or in defines)
        for branch in branches:
            if branch in available_branches:
                physical_branches_requested.append(branch)
            elif branch in defined_branches:
                derived_branches_requested.append(branch)
            else:
                similar = self._find_similar_branches(branch, list(available_branches))
                suggestion = f"Did you mean: {similar[:3]}?" if similar else ""
                raise KeyError(
                    f"Branch '{branch}' not found in tree '{tree_name}' or defines. "
                    f"Available: {list(available_branches)[:10]}... {suggestion}"
                )

        # Collect all branches needed for reading (physical branches + dependencies of derived branches)
        branches_to_read = set(physical_branches_requested)

        if defines:
            # Extract dependencies from all define expressions
            from root_mcp.extended.analysis.operations import _extract_branches_from_expression

            for def_name, def_expr in defines.items():
                # Get branches used in this definition
                needed = _extract_branches_from_expression(def_expr, list(available_branches))
                branches_to_read.update(needed)

            # Also extract branches from selection if it exists
            if selection:
                selection_branches = _extract_branches_from_expression(
                    selection, list(available_branches)
                )
                branches_to_read.update(selection_branches)
        elif selection:
            # Just selection, no defines
            from root_mcp.extended.analysis.operations import _extract_branches_from_expression

            selection_branches = _extract_branches_from_expression(
                selection, list(available_branches)
            )
            branches_to_read.update(selection_branches)

        # Apply limit bounds
        if limit is None:
            limit = self.config.analysis.default_read_limit
        limit = min(limit, self.config.limits.max_rows_per_call)

        # Calculate entry range
        total_entries = tree.num_entries
        entry_start = offset
        entry_stop = min(offset + limit, total_entries)

        logger.info(
            f"Reading {len(branches_to_read)} physical branches from {tree_name} "
            f"(entries {entry_start}:{entry_stop}/{total_entries}), "
            f"with {len(derived_branches_requested)} derived branches"
        )

        # Read data from tree
        try:
            arrays = tree.arrays(
                filter_name=list(branches_to_read),
                cut=None,  # We'll apply selection after computing derived branches
                entry_start=entry_start,
                entry_stop=entry_stop,
                library="ak",  # Use awkward arrays
            )
        except Exception as e:
            logger.error(f"Failed to read branches: {e}")
            raise

        # Process derived branches if defines are provided
        if defines:
            from root_mcp.extended.analysis.operations import AnalysisOperations

            analysis_ops = AnalysisOperations(self.config, self.file_manager)
            arrays = analysis_ops._process_defines(arrays, defines)

        # Apply selection after computing derived branches (if applicable)
        if selection:
            try:
                from root_mcp.extended.analysis.operations import _evaluate_selection_any

                mask = _evaluate_selection_any(arrays, selection)
                arrays = arrays[mask]
            except Exception as e:
                logger.error(f"Failed to apply selection: {e}")
                raise ValueError(
                    f"Invalid selection expression: {selection}. "
                    "Use ROOT-style syntax (e.g., 'pt > 20 && abs(eta) < 2.4')"
                ) from e

        # Get actual number of entries (after selection)
        entries_returned = len(arrays)

        # Select only the requested branches (filter out intermediate branches)
        try:
            arrays = arrays[branches]
        except Exception as e:
            logger.error(f"Failed to select requested branches: {e}")
            raise

        # Flatten if requested
        if flatten:
            arrays = ak.flatten(arrays, axis=None)

        # Convert to records (list of dicts)
        records = self._arrays_to_records(arrays)

        # Check if jagged
        is_jagged = self._check_if_jagged(arrays)

        return {
            "data": {
                "branches": branches,
                "entries": entries_returned,
                "is_jagged": is_jagged,
                "records": records,
            },
            "metadata": {
                "operation": "read_branches",
                "entries_scanned": entry_stop - entry_start,
                "entries_selected": entries_returned,
                "entries_returned": entries_returned,
                "truncated": entry_stop < total_entries
                or entries_returned < (entry_stop - entry_start),
                "selection": selection,
                "defines": list(defines.keys()) if defines else None,
            },
        }

    def sample_tree(
        self,
        path: str,
        tree_name: str,
        size: int = 100,
        method: str = "first",
        branches: list[str] | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Get a sample from a tree.

        Args:
            path: File path
            tree_name: Tree name
            size: Sample size
            method: "first" or "random"
            branches: Branches to include (None = all)
            seed: Random seed for reproducibility

        Returns:
            Sample data and metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Get branches
        if branches is None:
            branches = list(tree.keys())

        # Apply size limit
        size = min(size, 10_000)  # Max sample size

        if method == "first":
            # Just read first N entries
            return self.read_branches(
                path=path,
                tree_name=tree_name,
                branches=branches,
                limit=size,
                offset=0,
            )
        elif method == "random":
            # Random sampling
            total_entries = tree.num_entries
            if seed is not None:
                np.random.seed(seed)

            # Generate random indices
            indices = np.random.choice(total_entries, size=min(size, total_entries), replace=False)
            indices = np.sort(indices)  # Sort for better I/O performance

            # Read using entry ranges
            # For simplicity, read in chunks that contain the random indices
            # (Optimal implementation would use uproot's array indexing)
            arrays = tree.arrays(
                filter_name=branches,
                entry_start=0,
                entry_stop=total_entries,
                library="ak",
            )[indices]

            records = self._arrays_to_records(arrays)
            is_jagged = self._check_if_jagged(arrays)

            return {
                "data": {
                    "branches": branches,
                    "entries": len(arrays),
                    "is_jagged": is_jagged,
                    "records": records,
                },
                "metadata": {
                    "operation": "sample_tree",
                    "method": method,
                    "seed": seed,
                },
            }
        else:
            raise ValueError(f"Unknown sampling method: {method}. Use 'first' or 'random'")

    def get_branch_info(
        self, path: str, tree_name: str, pattern: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get information about branches in a tree.

        Args:
            path: File path
            tree_name: Tree name
            pattern: Optional glob pattern to filter branches

        Returns:
            List of branch info dictionaries
        """
        tree = self.file_manager.get_tree(path, tree_name)

        branches = []
        for name in tree.keys():
            # Filter by pattern if provided
            if pattern and not self._matches_glob(name, pattern):
                continue

            branch = tree[name]
            typename = str(branch.typename) if hasattr(branch, "typename") else "unknown"

            # Determine if jagged (variable-length)
            is_jagged = "[]" in typename or "vector" in typename.lower()

            info = {
                "name": name,
                "type": typename,
                "title": str(branch.title) if hasattr(branch, "title") else "",
                "is_jagged": is_jagged,
            }

            branches.append(info)

        return branches

    def compute_branch_stats(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        selection: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """
        Compute statistics for branches.

        Args:
            path: File path
            tree_name: Tree name
            branches: Branches to analyze
            selection: Optional cut expression

        Returns:
            Dictionary mapping branch names to statistics
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data (all entries, but only requested branches)
        arrays = tree.arrays(
            filter_name=branches,
            cut=selection,
            library="ak",
        )

        stats = {}
        for branch in branches:
            data = arrays[branch]

            # Flatten jagged arrays
            if _is_list_like(data):
                data = ak.flatten(data)

            # Convert to numpy for stats
            data_np = ak.to_numpy(data)

            # Compute statistics
            stats[branch] = {
                "count": len(data_np),
                "mean": float(np.mean(data_np)),
                "std": float(np.std(data_np)),
                "min": float(np.min(data_np)),
                "max": float(np.max(data_np)),
                "median": float(np.median(data_np)),
            }

        return stats

    @staticmethod
    def _arrays_to_records(arrays: ak.Array) -> list[dict[str, Any]]:
        """Convert awkward arrays to list of records."""
        # Convert to list of dicts
        records = ak.to_list(arrays)
        return records if isinstance(records, list) else []

    @staticmethod
    def _check_if_jagged(arrays: ak.Array) -> bool:
        """Check if arrays contain jagged (variable-length) data."""
        for field in arrays.fields:
            if _is_variable_length_list(arrays[field]):
                return True
        return False

    @staticmethod
    def _matches_glob(text: str, pattern: str) -> bool:
        """Check if text matches glob pattern."""
        import fnmatch

        return fnmatch.fnmatch(text, pattern)

    def stream_branches(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        chunk_size: int = 10_000,
        selection: str | None = None,
    ):
        """
        Stream branch data in chunks for large files.

        Args:
            path: File path
            tree_name: Tree name
            branches: Branches to read
            chunk_size: Number of entries per chunk
            selection: Optional cut expression

        Yields:
            Chunks of data as awkward arrays
        """
        tree = self.file_manager.get_tree(path, tree_name)
        total_entries = tree.num_entries

        logger.info(
            f"Streaming {len(branches)} branches from {tree_name} "
            f"({total_entries} entries, chunk_size={chunk_size})"
        )

        # Stream in chunks
        for entry_start in range(0, total_entries, chunk_size):
            entry_stop = min(entry_start + chunk_size, total_entries)

            try:
                arrays = tree.arrays(
                    filter_name=branches,
                    cut=selection,
                    entry_start=entry_start,
                    entry_stop=entry_stop,
                    library="ak",
                )
                yield arrays
            except Exception as e:
                logger.error(f"Failed to read chunk {entry_start}:{entry_stop}: {e}")
                raise

    @staticmethod
    def _find_similar_branches(target: str, available: list[str]) -> list[str]:
        """Find branches with similar names using simple heuristics."""
        from difflib import get_close_matches

        return get_close_matches(target, available, n=3, cutoff=0.6)


def _unwrap_awkward_layout(layout: Any) -> Any:
    while True:
        name = type(layout).__name__
        if (
            name
            in {
                "IndexedArray",
                "IndexedOptionArray",
                "ByteMaskedArray",
                "BitMaskedArray",
                "UnmaskedArray",
            }
            or name.endswith("OptionArray")
            or name.endswith("MaskedArray")
        ) and hasattr(layout, "content"):
            layout = layout.content
            continue
        return layout


def _is_list_like(array: ak.Array) -> bool:
    try:
        layout = _unwrap_awkward_layout(ak.to_layout(array))
    except Exception:
        return False

    return type(layout).__name__ in {"RegularArray", "ListArray", "ListOffsetArray"} or (
        "ListOffsetArray" in type(layout).__name__
    )


def _is_variable_length_list(array: ak.Array) -> bool:
    try:
        layout = _unwrap_awkward_layout(ak.to_layout(array))
    except Exception:
        return False

    name = type(layout).__name__
    if name == "RegularArray":
        return False
    return name == "ListArray" or name == "ListOffsetArray" or "ListOffsetArray" in name


class HistogramReader:
    """
    High-level interface for reading histograms.

    Provides access to TH1, TH2, TH3, and TProfile objects.
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize HistogramReader.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def read_histogram(self, path: str, hist_name: str) -> dict[str, Any]:
        """
        Read a histogram from a ROOT file.

        Args:
            path: File path
            hist_name: Histogram name or path

        Returns:
            Histogram data and metadata
        """
        file_obj = self.file_manager.open(path)

        try:
            hist = file_obj[hist_name]
        except KeyError as e:
            available = [h["name"] for h in self.file_manager.list_histograms(path)]
            raise KeyError(f"Histogram '{hist_name}' not found. Available: {available}") from e

        # Get histogram type
        classname = hist.classname

        # Read based on dimensionality
        if "TH1" in classname or "TProfile" in classname:
            return self._read_1d_histogram(hist, classname)
        elif "TH2" in classname:
            return self._read_2d_histogram(hist, classname)
        elif "TH3" in classname:
            return self._read_3d_histogram(hist, classname)
        else:
            raise ValueError(f"Unsupported histogram type: {classname}")

    def _read_1d_histogram(self, hist: Any, classname: str) -> dict[str, Any]:
        """Read 1D histogram."""
        values = hist.values()
        edges = hist.axis().edges()
        errors = hist.errors() if hasattr(hist, "errors") else np.sqrt(values)

        return {
            "type": classname,
            "bin_edges": edges.tolist(),
            "bin_counts": values.tolist(),
            "bin_errors": errors.tolist(),
            "entries": int(values.sum()),
            "underflow": float(hist.values(flow=True)[0]),
            "overflow": float(hist.values(flow=True)[-1]),
        }

    def _read_2d_histogram(self, hist: Any, classname: str) -> dict[str, Any]:
        """Read 2D histogram."""
        values = hist.values()
        x_edges = hist.axis(0).edges()
        y_edges = hist.axis(1).edges()

        return {
            "type": classname,
            "x_edges": x_edges.tolist(),
            "y_edges": y_edges.tolist(),
            "counts": values.tolist(),
            "entries": int(values.sum()),
        }

    def _read_3d_histogram(self, hist: Any, classname: str) -> dict[str, Any]:
        """Read 3D histogram."""
        values = hist.values()
        x_edges = hist.axis(0).edges()
        y_edges = hist.axis(1).edges()
        z_edges = hist.axis(2).edges()

        return {
            "type": classname,
            "x_edges": x_edges.tolist(),
            "y_edges": y_edges.tolist(),
            "z_edges": z_edges.tolist(),
            "counts": values.tolist(),
            "entries": int(values.sum()),
        }
