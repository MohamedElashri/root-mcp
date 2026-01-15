"""Plotting tools for ROOT data visualization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from root_mcp.config import Config
from root_mcp.core.io.file_manager import FileManager
from root_mcp.core.io.validators import PathValidator
from root_mcp.extended.analysis.histograms import HistogramOperations
from root_mcp.extended.analysis.plotting import generate_plot

logger = logging.getLogger(__name__)


class PlottingTools:
    """Tools for creating plots from ROOT data."""

    def __init__(
        self,
        config: Config,
        file_manager: FileManager,
        path_validator: PathValidator,
        histogram_ops: HistogramOperations,
    ):
        """
        Initialize plotting tools.

        Args:
            config: Server configuration
            file_manager: File manager instance
            path_validator: Path validator instance
            histogram_ops: Histogram operations instance
        """
        self.config = config
        self.file_manager = file_manager
        self.path_validator = path_validator
        self.histogram_ops = histogram_ops

        # Import AnalysisOperations for defines support
        from root_mcp.extended.analysis.operations import AnalysisOperations

        self.analysis_ops = AnalysisOperations(config, file_manager)

    def plot_histogram_1d(
        self,
        path: str,
        tree_name: str,
        branch: str,
        bins: int,
        range: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
        defines: dict[str, str] | str | None = None,
        output_path: str = "/tmp/histogram.png",
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str = "Events",
        log_y: bool = False,
        style: str = "default",
    ) -> dict[str, Any]:
        """
        Create a 1D histogram plot.

        Args:
            path: File path
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram
            selection: Optional cut expression
            weights: Optional weight branch
            defines: Optional variable definitions (dict or JSON string)
            output_path: Where to save the plot
            title: Plot title (default: branch name)
            xlabel: X-axis label (default: branch name)
            ylabel: Y-axis label
            log_y: Use logarithmic y-axis
            style: Plot style ("default", "publication", "presentation")

        Returns:
            Plot metadata including path and statistics
        """
        # Handle defines parameter if passed as JSON string
        if defines is not None and isinstance(defines, str):
            import json

            try:
                defines = json.loads(defines)
            except json.JSONDecodeError as e:
                return {
                    "error": "invalid_parameter",
                    "message": f"Invalid JSON in defines parameter: {e}",
                }

        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Validate output path
        output_path_obj = Path(output_path)
        if not output_path_obj.parent.exists():
            try:
                output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {
                    "error": "invalid_output_path",
                    "message": f"Cannot create output directory: {e}",
                }

        # Compute histogram (use AnalysisOperations if defines are provided)
        try:
            if defines:
                # Use AnalysisOperations which supports defines
                hist_result = self.analysis_ops.compute_histogram(
                    path=str(validated_path),
                    tree_name=tree_name,
                    branch=branch,
                    bins=bins,
                    range=range,
                    selection=selection,
                    weights=weights,
                    defines=defines,
                )
            else:
                # Use HistogramOperations for better performance when no defines
                hist_result = self.histogram_ops.compute_histogram_1d(
                    path=str(validated_path),
                    tree_name=tree_name,
                    branch=branch,
                    bins=bins,
                    range=range,
                    selection=selection,
                    weights=weights,
                )

            if "error" in hist_result:
                return hist_result

        except Exception as e:
            logger.error(f"Failed to compute histogram: {e}")
            return {
                "error": "computation_error",
                "message": f"Failed to compute histogram: {e}",
            }

        # Prepare plot options
        plot_options = {
            "title": title or f"Histogram of {branch}",
            "xlabel": xlabel or branch,
            "ylabel": ylabel,
            "log_y": log_y,
            "style": style,
            "output_path": str(output_path_obj),
        }

        # Generate plot
        try:
            plot_result = generate_plot(
                data=hist_result,
                plot_type="histogram",
                fit_data=None,
                options=plot_options,
                config=self.config,
            )

            if "error" in plot_result:
                return plot_result

            # Return combined result
            return {
                "data": {
                    "plot_path": str(output_path_obj),
                    "format": output_path_obj.suffix[1:],
                    "statistics": hist_result["data"],
                },
                "metadata": {
                    "operation": "plot_histogram_1d",
                    "branch": branch,
                    "bins": bins,
                    "entries": hist_result["data"]["entries"],
                },
                "message": f"Plot saved to {output_path_obj}",
            }

        except Exception as e:
            logger.error(f"Failed to generate plot: {e}")
            return {
                "error": "plot_error",
                "message": f"Failed to generate plot: {e}",
            }

    def plot_histogram_2d(
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
        defines: dict[str, str] | str | None = None,
        output_path: str = "/tmp/histogram_2d.png",
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        colormap: str = "viridis",
        log_z: bool = False,
        style: str = "default",
    ) -> dict[str, Any]:
        """
        Create a 2D histogram plot.

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
            defines: Optional variable definitions (dict or JSON string)
            output_path: Where to save the plot
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            colormap: Matplotlib colormap name
            log_z: Use logarithmic color scale
            style: Plot style

        Returns:
            Plot metadata including path and statistics
        """
        # Handle defines parameter if passed as JSON string
        if defines is not None and isinstance(defines, str):
            import json

            try:
                defines = json.loads(defines)
            except json.JSONDecodeError as e:
                return {
                    "error": "invalid_parameter",
                    "message": f"Invalid JSON in defines parameter: {e}",
                }

        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Validate output path
        output_path_obj = Path(output_path)
        if not output_path_obj.parent.exists():
            try:
                output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {
                    "error": "invalid_output_path",
                    "message": f"Cannot create output directory: {e}",
                }

        # Compute 2D histogram (use AnalysisOperations if defines are provided)
        try:
            if defines:
                # Use AnalysisOperations which supports defines
                hist_result = self.analysis_ops.compute_histogram_2d(
                    path=str(validated_path),
                    tree_name=tree_name,
                    x_branch=branch_x,
                    y_branch=branch_y,
                    x_bins=bins_x,
                    y_bins=bins_y,
                    x_range=range_x,
                    y_range=range_y,
                    selection=selection,
                    defines=defines,
                )
            else:
                # Use HistogramOperations for better performance when no defines
                hist_result = self.histogram_ops.compute_histogram_2d(
                    path=str(validated_path),
                    tree_name=tree_name,
                    branch_x=branch_x,
                    branch_y=branch_y,
                    bins_x=bins_x,
                    bins_y=bins_y,
                    range_x=range_x,
                    range_y=range_y,
                    selection=selection,
                    weights=weights,
                )

            if "error" in hist_result:
                return hist_result

        except Exception as e:
            logger.error(f"Failed to compute 2D histogram: {e}")
            return {
                "error": "computation_error",
                "message": f"Failed to compute 2D histogram: {e}",
            }

        # Prepare plot options
        plot_options = {
            "title": title or f"{branch_y} vs {branch_x}",
            "xlabel": xlabel or branch_x,
            "ylabel": ylabel or branch_y,
            "colormap": colormap,
            "log_z": log_z,
            "style": style,
            "output_path": str(output_path_obj),
        }

        # Generate plot
        try:
            plot_result = generate_plot(
                data=hist_result,
                plot_type="histogram_2d",
                fit_data=None,
                options=plot_options,
                config=self.config,
            )

            if "error" in plot_result:
                return plot_result

            # Return combined result
            return {
                "data": {
                    "plot_path": str(output_path_obj),
                    "format": output_path_obj.suffix[1:],
                    "statistics": {
                        "entries": hist_result["data"]["entries"],
                        "bins_x": bins_x,
                        "bins_y": bins_y,
                    },
                },
                "metadata": {
                    "operation": "plot_histogram_2d",
                    "branch_x": branch_x,
                    "branch_y": branch_y,
                },
                "message": f"Plot saved to {output_path_obj}",
            }

        except Exception as e:
            logger.error(f"Failed to generate plot: {e}")
            return {
                "error": "plot_error",
                "message": f"Failed to generate plot: {e}",
            }
