"""Correlation and covariance analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

logger = logging.getLogger(__name__)


class CorrelationAnalysis:
    """
    Statistical correlation and covariance analysis.

    Provides:
    - Pearson correlation coefficients
    - Spearman rank correlation
    - Covariance matrices
    - Correlation matrices
    - Significance testing
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize correlation analysis.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def compute_correlation_matrix(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        selection: str | None = None,
        method: str = "pearson",
    ) -> dict[str, Any]:
        """
        Compute correlation matrix for multiple branches.

        Args:
            path: File path
            tree_name: Tree name
            branches: List of branches to correlate
            selection: Optional cut expression
            method: Correlation method ('pearson' or 'spearman')

        Returns:
            Correlation matrix and metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        arrays = tree.arrays(
            filter_name=branches,
            cut=selection,
            library="ak",
        )

        # Convert to numpy arrays and flatten if needed
        data_arrays = []
        for branch in branches:
            data = arrays[branch]
            if self._is_jagged(data):
                data = ak.flatten(data)
            data_np = ak.to_numpy(data)

            # Remove NaN and inf
            data_np = data_np[np.isfinite(data_np)]
            data_arrays.append(data_np)

        # Find minimum length (in case of different lengths after filtering)
        min_length = min(len(arr) for arr in data_arrays)
        data_arrays = [arr[:min_length] for arr in data_arrays]

        # Stack into matrix (variables x observations)
        data_matrix = np.vstack(data_arrays)

        # Compute correlation
        if method == "pearson":
            corr_matrix = np.corrcoef(data_matrix)
        elif method == "spearman":
            corr_matrix, _ = stats.spearmanr(data_matrix, axis=1)
        else:
            raise ValueError(f"Unknown correlation method: {method}")

        return {
            "correlation_matrix": corr_matrix.tolist(),
            "branches": branches,
            "n_observations": min_length,
            "method": method,
            "metadata": {
                "operation": "compute_correlation_matrix",
                "selection": selection,
            },
        }

    def compute_covariance_matrix(
        self,
        path: str,
        tree_name: str,
        branches: list[str],
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute covariance matrix for multiple branches.

        Args:
            path: File path
            tree_name: Tree name
            branches: List of branches
            selection: Optional cut expression

        Returns:
            Covariance matrix and metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        arrays = tree.arrays(
            filter_name=branches,
            cut=selection,
            library="ak",
        )

        # Convert to numpy arrays
        data_arrays = []
        for branch in branches:
            data = arrays[branch]
            if self._is_jagged(data):
                data = ak.flatten(data)
            data_np = ak.to_numpy(data)
            data_np = data_np[np.isfinite(data_np)]
            data_arrays.append(data_np)

        # Find minimum length
        min_length = min(len(arr) for arr in data_arrays)
        data_arrays = [arr[:min_length] for arr in data_arrays]

        # Stack into matrix
        data_matrix = np.vstack(data_arrays)

        # Compute covariance
        cov_matrix = np.cov(data_matrix)

        return {
            "covariance_matrix": cov_matrix.tolist(),
            "branches": branches,
            "n_observations": min_length,
            "metadata": {
                "operation": "compute_covariance_matrix",
                "selection": selection,
            },
        }

    def compute_correlation(
        self,
        path: str,
        tree_name: str,
        branch_x: str,
        branch_y: str,
        selection: str | None = None,
        method: str = "pearson",
    ) -> dict[str, Any]:
        """
        Compute correlation coefficient between two branches.

        Args:
            path: File path
            tree_name: Tree name
            branch_x: First branch
            branch_y: Second branch
            selection: Optional cut expression
            method: Correlation method ('pearson' or 'spearman')

        Returns:
            Correlation coefficient, p-value, and metadata
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

        x_np = ak.to_numpy(data_x)
        y_np = ak.to_numpy(data_y)

        # Remove NaN and inf from both arrays
        mask = np.isfinite(x_np) & np.isfinite(y_np)
        x_np = x_np[mask]
        y_np = y_np[mask]

        if len(x_np) < 2:
            raise ValueError("Not enough valid data points for correlation")

        # Compute correlation
        if method == "pearson":
            corr_coef, p_value = stats.pearsonr(x_np, y_np)
        elif method == "spearman":
            corr_coef, p_value = stats.spearmanr(x_np, y_np)
        else:
            raise ValueError(f"Unknown correlation method: {method}")

        return {
            "correlation_coefficient": float(corr_coef),
            "p_value": float(p_value),
            "n_observations": len(x_np),
            "method": method,
            "branch_x": branch_x,
            "branch_y": branch_y,
            "metadata": {
                "operation": "compute_correlation",
                "selection": selection,
            },
        }

    def compute_mutual_information(
        self,
        path: str,
        tree_name: str,
        branch_x: str,
        branch_y: str,
        bins: int = 50,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute mutual information between two branches.

        Args:
            path: File path
            tree_name: Tree name
            branch_x: First branch
            branch_y: Second branch
            bins: Number of bins for discretization
            selection: Optional cut expression

        Returns:
            Mutual information and metadata
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

        x_np = ak.to_numpy(data_x)
        y_np = ak.to_numpy(data_y)

        # Remove NaN and inf
        mask = np.isfinite(x_np) & np.isfinite(y_np)
        x_np = x_np[mask]
        y_np = y_np[mask]

        # Compute 2D histogram
        hist_2d, _, _ = np.histogram2d(x_np, y_np, bins=bins)

        # Normalize to get probabilities
        p_xy = hist_2d / np.sum(hist_2d)

        # Marginal distributions
        p_x = np.sum(p_xy, axis=1)
        p_y = np.sum(p_xy, axis=0)

        # Compute mutual information
        # MI = sum(p(x,y) * log(p(x,y) / (p(x) * p(y))))
        mi = 0.0
        for i in range(bins):
            for j in range(bins):
                if p_xy[i, j] > 0 and p_x[i] > 0 and p_y[j] > 0:
                    mi += p_xy[i, j] * np.log(p_xy[i, j] / (p_x[i] * p_y[j]))

        return {
            "mutual_information": float(mi),
            "n_observations": len(x_np),
            "bins": bins,
            "branch_x": branch_x,
            "branch_y": branch_y,
            "metadata": {
                "operation": "compute_mutual_information",
                "selection": selection,
            },
        }

    @staticmethod
    def _is_jagged(array: ak.Array) -> bool:
        """Check if array is jagged (variable-length)."""
        try:
            layout = ak.to_layout(array)
            while hasattr(layout, "content"):
                layout = layout.content

            name = type(layout).__name__
            if name == "RegularArray":
                return False
            return "ListArray" in name or "ListOffsetArray" in name
        except Exception:
            return False
