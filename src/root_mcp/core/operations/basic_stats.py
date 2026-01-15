"""Basic statistics operations for branches."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

logger = logging.getLogger(__name__)


class BasicStatistics:
    """
    Compute basic statistics for TTree branches.

    Provides min, max, mean, std, median, and percentiles without
    requiring scipy or other analysis dependencies.
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize basic statistics calculator.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def compute_stats(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        selection: str | None = None,
        defines: dict[str, str] | None = None,
    ) -> dict[str, dict[str, float]]:
        """
        Compute basic statistics for branches.

        Args:
            path: File path
            tree_name: Tree name
            branches: List of branch names
            selection: Optional cut expression
            defines: Optional derived variable definitions

        Returns:
            Dictionary mapping branch names to statistics
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Determine which branches to read from the tree
        branches_to_read = set()

        # If we have defines, we need to read branches used in the expressions
        if defines:
            available_branches = set(tree.keys())

            for expr in defines.values():
                branches_to_read.update(self._extract_branches(expr, list(available_branches)))

            # Add branches used in selection expression
            if selection:
                branches_to_read.update(self._extract_branches(selection, list(available_branches)))

            # Add requested branches that exist in the tree (not defined variables)
            for branch in branches:
                if branch not in defines and branch in available_branches:
                    branches_to_read.add(branch)
        else:
            # No defines, just read the requested branches
            branches_to_read = set(branches)

        # Read data (without selection first if we have defines)
        if defines:
            # Read without cut, apply selection after defines
            arrays = tree.arrays(
                filter_name=list(branches_to_read),
                library="ak",
            )

            # Process defines by evaluating expressions
            arrays = self._process_defines(arrays, defines)

            # Apply selection after defines (so we can cut on defined variables)
            if selection:
                mask = self._evaluate_selection(arrays, selection)
                arrays = arrays[mask]
        else:
            # No defines, can apply cut directly
            arrays = tree.arrays(
                filter_name=list(branches_to_read),
                cut=selection,
                library="ak",
            )

        stats = {}
        for branch in branches:
            data = arrays[branch]

            # Flatten jagged arrays completely
            if self._is_jagged(data):
                data = ak.flatten(data, axis=None)

            # Convert to numpy for stats
            # Use np.asarray which handles awkward arrays better
            data_np = np.asarray(data)

            # Filter out NaN and inf values
            data_np = data_np[np.isfinite(data_np)]

            if len(data_np) == 0:
                stats[branch] = {
                    "count": 0,
                    "mean": None,
                    "std": None,
                    "min": None,
                    "max": None,
                    "median": None,
                }
                continue

            # Compute statistics
            stats[branch] = {
                "count": len(data_np),
                "mean": float(np.mean(data_np)),
                "std": float(np.std(data_np)),
                "min": float(np.min(data_np)),
                "max": float(np.max(data_np)),
                "median": float(np.median(data_np)),
            }

            # Add percentiles
            percentiles = [25, 75, 90, 95, 99]
            for p in percentiles:
                stats[branch][f"p{p}"] = float(np.percentile(data_np, p))

        return stats

    def compute_histogram_basic(
        self,
        path: str,
        tree_name: str,
        branch: str,
        bins: int,
        range: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute a basic 1D histogram without fitting capabilities.

        Args:
            path: File path
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram
            selection: Optional cut expression
            weights: Optional weight branch

        Returns:
            Histogram data
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Validate bins
        max_bins = self.config.core.limits.max_rows_per_call
        if bins > max_bins:
            raise ValueError(f"Number of bins ({bins}) exceeds maximum ({max_bins})")

        # Read data
        branches_to_read = [branch]
        if weights:
            branches_to_read.append(weights)

        arrays = tree.arrays(
            filter_name=branches_to_read,
            cut=selection,
            library="ak",
        )

        # Get data
        data = arrays[branch]
        if self._is_jagged(data):
            data = ak.flatten(data)
        data_np = ak.to_numpy(data)

        # Get weights if specified
        weights_np = None
        if weights:
            weights_data = arrays[weights]
            if self._is_jagged(weights_data):
                weights_data = ak.flatten(weights_data)
            weights_np = ak.to_numpy(weights_data)

        # Determine range
        if range is None:
            data_finite = data_np[np.isfinite(data_np)]
            if len(data_finite) == 0:
                raise ValueError(f"No finite values in branch {branch}")
            range = (float(np.min(data_finite)), float(np.max(data_finite)))

        # Compute histogram
        counts, edges = np.histogram(data_np, bins=bins, range=range, weights=weights_np)

        # Compute bin centers
        centers = (edges[:-1] + edges[1:]) / 2

        # Compute errors (Poisson for unweighted, sqrt(sum(w^2)) for weighted)
        if weights_np is None:
            errors = np.sqrt(counts)
        else:
            # For weighted histograms, compute sum of squared weights per bin
            errors_sq, _ = np.histogram(data_np, bins=bins, range=range, weights=weights_np**2)
            errors = np.sqrt(errors_sq)

        # Count overflow/underflow
        underflow = np.sum(data_np < range[0])
        overflow = np.sum(data_np > range[1])

        return {
            "data": {
                "bin_edges": edges.tolist(),
                "bin_centers": centers.tolist(),
                "bin_counts": counts.tolist(),
                "bin_errors": errors.tolist(),
                "entries": int(np.sum(counts)),
                "underflow": int(underflow),
                "overflow": int(overflow),
                "range": range,
            },
            "metadata": {
                "operation": "compute_histogram",
                "branch": branch,
                "bins": bins,
                "weighted": weights is not None,
                "selection": selection,
            },
        }

    def _process_defines(self, arrays: ak.Array, defines: dict[str, str]) -> ak.Array:
        """
        Process derived variable definitions by evaluating expressions with dependency resolution.

        Args:
            arrays: Input awkward array with existing fields
            defines: Dictionary of {name: expression}

        Returns:
            Awkward array with new fields added
        """
        if not defines:
            return arrays

        # Create namespace with existing fields and numpy functions
        namespace = {field: arrays[field] for field in arrays.fields}
        namespace.update(
            {
                "sqrt": np.sqrt,
                "abs": np.abs,
                "log": np.log,
                "exp": np.exp,
                "sin": np.sin,
                "cos": np.cos,
                "tan": np.tan,
                "arcsin": np.arcsin,
                "arccos": np.arccos,
                "arctan": np.arctan,
                "arctan2": np.arctan2,
            }
        )

        # Topologically sort defines to respect dependencies
        sorted_defines = self._topological_sort_defines(defines, set(arrays.fields))

        # Evaluate each define expression in dependency order
        for name, expr in sorted_defines:
            try:
                # Simple eval with restricted namespace
                result = eval(expr, {"__builtins__": {}}, namespace)
                # Add the new field to the array
                arrays = ak.with_field(arrays, result, name)
                # Also add to namespace for subsequent defines
                namespace[name] = result
            except Exception as e:
                logger.error(f"Failed to evaluate define '{name}': {expr} - {e}")
                raise ValueError(f"Failed to evaluate define '{name}': {e}")

        return arrays

    def _topological_sort_defines(
        self, defines: dict[str, str], available_fields: set[str]
    ) -> list[tuple[str, str]]:
        """
        Topologically sort defines to respect dependencies.

        Args:
            defines: Dictionary of {name: expression}
            available_fields: Set of fields already available (from tree)

        Returns:
            List of (name, expression) tuples in dependency order
        """
        import re

        # Build dependency graph
        dependencies = {}
        for name, expr in defines.items():
            # Extract identifiers from expression
            tokens = set(re.findall(r"[A-Za-z_]\w*", expr))
            # Filter to only defined variables (not built-in functions or already available fields)
            reserved = {
                "sqrt",
                "abs",
                "log",
                "exp",
                "sin",
                "cos",
                "tan",
                "arcsin",
                "arccos",
                "arctan",
                "arctan2",
                "sinh",
                "cosh",
                "tanh",
                "min",
                "max",
                "where",
                "sum",
                "any",
                "all",
            }
            deps = [
                t
                for t in tokens
                if t in defines and t not in reserved and t not in available_fields
            ]
            dependencies[name] = deps

        # Topological sort using Kahn's algorithm
        in_degree = {name: 0 for name in defines}
        for deps in dependencies.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Find all nodes with no incoming edges
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            name = queue.pop(0)
            result.append((name, defines[name]))

            # For each dependent of this node
            for other_name, deps in dependencies.items():
                if name in deps and other_name not in [r[0] for r in result]:
                    in_degree[other_name] -= 1
                    if in_degree[other_name] == 0:
                        queue.append(other_name)

        # Check for cycles
        if len(result) != len(defines):
            remaining = set(defines.keys()) - {r[0] for r in result}
            raise ValueError(f"Circular dependency detected in defines: {remaining}")

        return result

    @staticmethod
    def _extract_branches(expr: str, available_branches: list[str]) -> list[str]:
        """Extract branch names from an expression."""
        import re

        available = set(available_branches)
        tokens = set(re.findall(r"[A-Za-z_]\w*", expr))
        # Filter out common function names and keywords
        reserved = {
            "sqrt",
            "abs",
            "log",
            "exp",
            "sin",
            "cos",
            "tan",
            "arcsin",
            "arccos",
            "arctan",
            "arctan2",
        }
        return [t for t in tokens if t in available and t not in reserved]

    @staticmethod
    def _evaluate_selection(arrays: ak.Array, selection: str) -> ak.Array:
        """Evaluate a selection expression and return a boolean mask."""
        # Create namespace with fields
        namespace = {field: arrays[field] for field in arrays.fields}
        namespace.update(
            {
                "sqrt": np.sqrt,
                "abs": np.abs,
            }
        )

        # Replace C++ style operators with Python equivalents
        selection = selection.replace("&&", " and ").replace("||", " or ")

        try:
            mask = eval(selection, {"__builtins__": {}}, namespace)
            # Handle jagged arrays - use ak.any for boolean reductions
            if hasattr(mask, "ndim") and len(ak.to_layout(mask).form.fields) > 0:
                mask = ak.any(mask, axis=-1)
            return mask
        except Exception as e:
            logger.error(f"Failed to evaluate selection: {selection} - {e}")
            raise ValueError(f"Failed to evaluate selection: {e}")

    @staticmethod
    def _is_jagged(array: ak.Array) -> bool:
        """Check if array is jagged (variable-length)."""
        try:
            layout = ak.to_layout(array)
            # Check the top-level layout type
            name = type(layout).__name__
            # ListOffsetArray and ListArray indicate jagged/variable-length arrays
            return "ListArray" in name or "ListOffset" in name
        except Exception:
            return False
