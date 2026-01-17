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
        data: dict[str, Any] | None = None,
        path: str | None = None,
        tree_name: str | None = None,
        branch: str | None = None,
        bins: int | None = None,
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
            data: Pre-calculated histogram data (optional)
            path: File path (optional if data provided)
            tree_name: Tree name (optional if data provided)
            branch: Branch to histogram (optional if data provided)
            bins: Number of bins (optional if data provided)
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

        # Validate path if provided
        validated_path = None
        if path:
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

        hist_result = data
        if hist_result is None:
            if not all([validated_path, tree_name, branch, bins]):
                return {
                    "error": "missing_parameters",
                    "message": "Either 'data' or (path, tree_name, branch, bins) must be provided",
                }

            # Compute histogram (use AnalysisOperations if defines are provided)
            try:
                if defines:
                    # Use AnalysisOperations which supports defines
                    hist_result = self.analysis_ops.compute_histogram(
                        path=str(validated_path),
                        tree_name=tree_name,  # type: ignore
                        branch=branch,  # type: ignore
                        bins=bins,  # type: ignore
                        range=range,
                        selection=selection,
                        weights=weights,
                        defines=defines,
                    )
                else:
                    # Use HistogramOperations for better performance when no defines
                    hist_result = self.histogram_ops.compute_histogram_1d(
                        path=str(validated_path),
                        tree_name=tree_name,  # type: ignore
                        branch=branch,  # type: ignore
                        bins=bins,  # type: ignore
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
            "title": title or f"Histogram of {branch or 'Custom Data'}",
            "xlabel": xlabel or branch or "X",
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

            # Save plot to file
            import base64

            try:
                image_data = base64.b64decode(plot_result["image_data"])
                with open(output_path_obj, "wb") as f:
                    f.write(image_data)
            except Exception as e:
                return {
                    "error": "write_error",
                    "message": f"Failed to write plot to file: {e}",
                }

            # Extract statistics safely
            stats = hist_result.get("data", hist_result)
            entries = stats.get("entries", 0)

            # Return combined result
            return {
                "data": {
                    "plot_path": str(output_path_obj),
                    "format": output_path_obj.suffix[1:],
                    "statistics": stats,
                },
                "metadata": {
                    "operation": "plot_histogram_1d",
                    "branch": branch,
                    "bins": bins,
                    "entries": entries,
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
        data: dict[str, Any] | None = None,
        path: str | None = None,
        tree_name: str | None = None,
        branch_x: str | None = None,
        branch_y: str | None = None,
        bins_x: int | None = None,
        bins_y: int | None = None,
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
            data: Pre-calculated histogram data (optional)
            path: File path (optional if data provided)
            tree_name: Tree name (optional if data provided)
            branch_x: X-axis branch (optional if data provided)
            branch_y: Y-axis branch (optional if data provided)
            bins_x: Number of bins in X (optional if data provided)
            bins_y: Number of bins in Y (optional if data provided)
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

        # Validate path if provided
        validated_path = None
        if path:
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

        hist_result = data
        if hist_result is None:
            if not all([validated_path, tree_name, branch_x, branch_y, bins_x, bins_y]):
                return {
                    "error": "missing_parameters",
                    "message": "Either 'data' or (path, tree_name, branch_x, branch_y, bins_x, bins_y) must be provided",
                }

            # Compute 2D histogram (use AnalysisOperations if defines are provided)
            try:
                if defines:
                    # Use AnalysisOperations which supports defines
                    hist_result = self.analysis_ops.compute_histogram_2d(
                        path=str(validated_path),
                        tree_name=tree_name,  # type: ignore
                        x_branch=branch_x,  # type: ignore
                        y_branch=branch_y,  # type: ignore
                        x_bins=bins_x,  # type: ignore
                        y_bins=bins_y,  # type: ignore
                        x_range=range_x,
                        y_range=range_y,
                        selection=selection,
                        defines=defines,
                    )
                else:
                    # Use HistogramOperations for better performance when no defines
                    hist_result = self.histogram_ops.compute_histogram_2d(
                        path=str(validated_path),
                        tree_name=tree_name,  # type: ignore
                        branch_x=branch_x,  # type: ignore
                        branch_y=branch_y,  # type: ignore
                        bins_x=bins_x,  # type: ignore
                        bins_y=bins_y,  # type: ignore
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
            "title": title or f"{branch_y or 'Y'} vs {branch_x or 'X'}",
            "xlabel": xlabel or branch_x or "X",
            "ylabel": ylabel or branch_y or "Y",
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

            # Save plot to file
            import base64

            try:
                image_data = base64.b64decode(plot_result["image_data"])
                with open(output_path_obj, "wb") as f:
                    f.write(image_data)
            except Exception as e:
                return {
                    "error": "write_error",
                    "message": f"Failed to write plot to file: {e}",
                }

            # Extract statistics safely
            stats = hist_result.get("data", hist_result)
            entries = stats.get("entries", 0)
            bx = bins_x or stats.get("bins_x", 0)
            by = bins_y or stats.get("bins_y", 0)

            # Return combined result
            return {
                "data": {
                    "plot_path": str(output_path_obj),
                    "format": output_path_obj.suffix[1:],
                    "statistics": {
                        "entries": entries,
                        "bins_x": bx,
                        "bins_y": by,
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
