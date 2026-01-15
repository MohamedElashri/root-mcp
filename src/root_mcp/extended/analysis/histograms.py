"""Advanced histogram operations for extended mode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

logger = logging.getLogger(__name__)


class HistogramOperations:
    """
    Advanced histogram operations with scipy-based fitting.

    Extends core histogram capabilities with:
    - 2D and 3D histograms
    - Profile histograms
    - Weighted histograms with proper error propagation
    - Histogram arithmetic
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize histogram operations.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def compute_histogram_1d(
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
        Compute a 1D histogram with advanced features.

        Args:
            path: File path
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram
            selection: Optional cut expression
            weights: Optional weight branch

        Returns:
            Histogram data with metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Validate bins
        max_bins = self.config.extended.histogram.max_bins_1d
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
            data = ak.flatten(data, axis=None)
        data_np = np.asarray(data)

        # Get weights if specified
        weights_np = None
        if weights:
            weights_data = arrays[weights]
            if self._is_jagged(weights_data):
                weights_data = ak.flatten(weights_data, axis=None)
            weights_np = np.asarray(weights_data)

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

        # Compute errors
        if weights_np is None:
            errors = np.sqrt(counts)
        else:
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
                "operation": "compute_histogram_1d",
                "branch": branch,
                "bins": bins,
                "weighted": weights is not None,
                "selection": selection,
            },
        }

    def compute_histogram_2d(
        self,
        path: str,
        tree_name: str,
        branch_x: str,
        branch_y: str,
        bins_x: int,
        bins_y: int,
        range_x: tuple[float, float] | None = None,
        range_y: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute a 2D histogram.

        Args:
            path: File path
            tree_name: Tree name
            branch_x: X-axis branch
            branch_y: Y-axis branch
            bins_x: Number of bins in X
            bins_y: Number of bins in Y
            range_x: (min, max) for X axis
            range_y: (min, max) for Y axis
            selection: Optional cut expression
            weights: Optional weight branch

        Returns:
            2D histogram data
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Validate bins
        max_bins = self.config.extended.histogram.max_bins_2d
        if bins_x > max_bins or bins_y > max_bins:
            raise ValueError(
                f"Number of bins ({bins_x}x{bins_y}) exceeds maximum ({max_bins}x{max_bins})"
            )

        # Read data
        branches_to_read = [branch_x, branch_y]
        if weights:
            branches_to_read.append(weights)

        arrays = tree.arrays(
            filter_name=branches_to_read,
            cut=selection,
            library="ak",
        )

        # Get data
        data_x = arrays[branch_x]
        data_y = arrays[branch_y]

        if self._is_jagged(data_x):
            data_x = ak.flatten(data_x, axis=None)
        if self._is_jagged(data_y):
            data_y = ak.flatten(data_y, axis=None)

        data_x_np = np.asarray(data_x)
        data_y_np = np.asarray(data_y)

        # Get weights if specified
        weights_np = None
        if weights:
            weights_data = arrays[weights]
            if self._is_jagged(weights_data):
                weights_data = ak.flatten(weights_data, axis=None)
            weights_np = np.asarray(weights_data)

        # Determine ranges
        if range_x is None:
            data_finite = data_x_np[np.isfinite(data_x_np)]
            if len(data_finite) == 0:
                raise ValueError(f"No finite values in branch {branch_x}")
            range_x = (float(np.min(data_finite)), float(np.max(data_finite)))

        if range_y is None:
            data_finite = data_y_np[np.isfinite(data_y_np)]
            if len(data_finite) == 0:
                raise ValueError(f"No finite values in branch {branch_y}")
            range_y = (float(np.min(data_finite)), float(np.max(data_finite)))

        # Compute 2D histogram
        counts, edges_x, edges_y = np.histogram2d(
            data_x_np,
            data_y_np,
            bins=[bins_x, bins_y],
            range=[range_x, range_y],
            weights=weights_np,
        )

        # Compute bin centers
        centers_x = (edges_x[:-1] + edges_x[1:]) / 2
        centers_y = (edges_y[:-1] + edges_y[1:]) / 2

        # Compute errors
        if weights_np is None:
            errors = np.sqrt(counts)
        else:
            errors_sq, _, _ = np.histogram2d(
                data_x_np,
                data_y_np,
                bins=[bins_x, bins_y],
                range=[range_x, range_y],
                weights=weights_np**2,
            )
            errors = np.sqrt(errors_sq)

        return {
            "data": {
                "bin_edges_x": edges_x.tolist(),
                "bin_edges_y": edges_y.tolist(),
                "bin_centers_x": centers_x.tolist(),
                "bin_centers_y": centers_y.tolist(),
                "bin_counts": counts.tolist(),
                "bin_errors": errors.tolist(),
                "entries": int(np.sum(counts)),
                "range_x": range_x,
                "range_y": range_y,
            },
            "metadata": {
                "operation": "compute_histogram_2d",
                "branch_x": branch_x,
                "branch_y": branch_y,
                "bins_x": bins_x,
                "bins_y": bins_y,
                "weighted": weights is not None,
                "selection": selection,
            },
        }

    def compute_profile(
        self,
        path: str,
        tree_name: str,
        branch_x: str,
        branch_y: str,
        bins: int,
        range_x: tuple[float, float] | None = None,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute a profile histogram (mean of Y vs X).

        Args:
            path: File path
            tree_name: Tree name
            branch_x: X-axis branch
            branch_y: Y-axis branch (to be averaged)
            bins: Number of bins in X
            range_x: (min, max) for X axis
            selection: Optional cut expression

        Returns:
            Profile histogram data
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        arrays = tree.arrays(
            filter_name=[branch_x, branch_y],
            cut=selection,
            library="ak",
        )

        # Get data
        data_x = arrays[branch_x]
        data_y = arrays[branch_y]

        if self._is_jagged(data_x):
            data_x = ak.flatten(data_x)
        if self._is_jagged(data_y):
            data_y = ak.flatten(data_y)

        data_x_np = ak.to_numpy(data_x)
        data_y_np = ak.to_numpy(data_y)

        # Determine range
        if range_x is None:
            data_finite = data_x_np[np.isfinite(data_x_np)]
            if len(data_finite) == 0:
                raise ValueError(f"No finite values in branch {branch_x}")
            range_x = (float(np.min(data_finite)), float(np.max(data_finite)))

        # Compute bin edges
        edges = np.linspace(range_x[0], range_x[1], bins + 1)
        centers = (edges[:-1] + edges[1:]) / 2

        # Compute mean and error in each bin
        means = np.zeros(bins)
        errors = np.zeros(bins)
        entries = np.zeros(bins, dtype=int)

        for i in range(bins):
            mask = (data_x_np >= edges[i]) & (data_x_np < edges[i + 1])
            if i == bins - 1:  # Include right edge in last bin
                mask = (data_x_np >= edges[i]) & (data_x_np <= edges[i + 1])

            y_in_bin = data_y_np[mask]
            if len(y_in_bin) > 0:
                means[i] = np.mean(y_in_bin)
                errors[i] = np.std(y_in_bin) / np.sqrt(len(y_in_bin))  # Standard error
                entries[i] = len(y_in_bin)

        return {
            "data": {
                "bin_edges": edges.tolist(),
                "bin_centers": centers.tolist(),
                "bin_means": means.tolist(),
                "bin_errors": errors.tolist(),
                "bin_entries": entries.tolist(),
                "range": range_x,
            },
            "metadata": {
                "operation": "compute_profile",
                "branch_x": branch_x,
                "branch_y": branch_y,
                "bins": bins,
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
