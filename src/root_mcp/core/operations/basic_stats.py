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
    ) -> dict[str, dict[str, float]]:
        """
        Compute basic statistics for branches.

        Args:
            path: File path
            tree_name: Tree name
            branches: List of branch names
            selection: Optional cut expression

        Returns:
            Dictionary mapping branch names to statistics
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        arrays = tree.arrays(
            filter_name=branches,
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
