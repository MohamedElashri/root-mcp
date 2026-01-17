"""Analysis tools for histograms, selections, and exports."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from root_mcp.extended.analysis.fitting import fit_histogram
from root_mcp.extended.analysis.plotting import generate_plot

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager
    from root_mcp.core.io.validators import PathValidator
    from root_mcp.extended.analysis.operations import AnalysisOperations
    from root_mcp.core.io.readers import TreeReader

logger = logging.getLogger(__name__)


class AnalysisTools:
    """Tools for physics analysis operations."""

    def __init__(
        self,
        config: Config,
        file_manager: FileManager,
        path_validator: PathValidator,
        analysis_ops: AnalysisOperations,
        tree_reader: TreeReader,
    ):
        """
        Initialize analysis tools.

        Args:
            config: Server configuration
            file_manager: File manager instance
            path_validator: Path validator instance
            analysis_ops: Analysis operations instance
            tree_reader: Tree reader instance
        """
        self.config = config
        self.file_manager = file_manager
        self.path_validator = path_validator
        self.analysis_ops = analysis_ops
        self.tree_reader = tree_reader

    def compute_histogram(
        self,
        path: str,
        tree_name: str,
        branch: str,
        bins: int,
        range: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
        defines: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Compute a 1D histogram.

        Args:
            path: File path
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram
            selection: Optional cut expression
            weights: Optional weight branch
            defines: Optional variable definitions

        Returns:
            Histogram data and metadata
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

        # Compute histogram
        try:
            result = self.analysis_ops.compute_histogram(
                path=str(validated_path),
                tree_name=tree_name,
                branch=branch,
                bins=bins,
                range=range,
                selection=selection,
                weights=weights,
                defines=defines,
            )
        except ValueError as e:
            return {
                "error": "invalid_parameter",
                "message": str(e),
            }
        except KeyError as e:
            return {
                "error": "branch_not_found",
                "message": str(e),
                "suggestion": "Use list_branches() to see available branches",
            }
        except Exception as e:
            logger.error(f"Failed to compute histogram: {e}")
            return {
                "error": "computation_error",
                "message": f"Failed to compute histogram: {e}",
            }

        # Add suggestions
        suggestions = []
        if result["data"]["overflow"] > result["data"]["entries"] * 0.05:
            suggestions.append(
                f"{result['data']['overflow']} entries overflow - consider extending range"
            )
        if result["data"]["underflow"] > result["data"]["entries"] * 0.05:
            suggestions.append(
                f"{result['data']['underflow']} entries underflow - consider extending range"
            )

        result["suggestions"] = suggestions

        return result

    def compute_histogram_2d(
        self,
        path: str,
        tree_name: str,
        x_branch: str,
        y_branch: str,
        x_bins: int,
        y_bins: int,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        selection: str | None = None,
        defines: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Compute a 2D histogram.

        Args:
            path: File path
            tree_name: Tree name
            x_branch: X-axis branch
            y_branch: Y-axis branch
            x_bins: Number of bins in x
            y_bins: Number of bins in y
            x_range: (min, max) for x-axis
            y_range: (min, max) for y-axis
            selection: Optional cut expression
            defines: Optional variable definitions

        Returns:
            2D histogram data and metadata
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

        # Compute 2D histogram
        try:
            result = self.analysis_ops.compute_histogram_2d(
                path=str(validated_path),
                tree_name=tree_name,
                x_branch=x_branch,
                y_branch=y_branch,
                x_bins=x_bins,
                y_bins=y_bins,
                x_range=x_range,
                y_range=y_range,
                selection=selection,
                defines=defines,
            )
        except Exception as e:
            return {
                "error": "computation_error",
                "message": f"Failed to compute 2D histogram: {e}",
            }

        result["suggestions"] = [
            "Use for correlation studies or 2D distributions",
            "Visualize as a heatmap or scatter plot",
        ]

        return result

    def fit_histogram(
        self,
        model: str | list[str | dict[str, Any]] | dict[str, Any],
        data: dict[str, Any] | None = None,
        path: str | None = None,
        tree_name: str | None = None,
        branch: str | None = None,
        bins: int | None = None,
        range: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
        defines: dict[str, str] | None = None,
        initial_guess: list[float] | None = None,
        bounds: list[list[float]] | None = None,
        fixed_parameters: dict[str | int, float] | None = None,
    ) -> dict[str, Any]:
        """
        Fit a histogram to a model. Can either take existing histogram data or
        compute it from a file.

        Args:
            model: Model configuration
            data: Optional histogram data (from compute_histogram)
            path: File path (if data not provided)
            tree_name: Tree name (if data not provided)
            branch: Branch to histogram (if data not provided)
            bins: Number of bins (if data not provided)
            range: Histogram range (optional)
            selection: Cut expression (optional)
            weights: Weight branch (optional)
            defines: Variable definitions (optional)
            initial_guess: Initial parameters for fit
            bounds: Parameter bounds
            fixed_parameters: Fixed parameters

        Returns:
            Fit results
        """
        # If data is not provided, compute it
        if data is None:
            if not all([path, tree_name, branch, bins]):
                return {
                    "error": "missing_parameters",
                    "message": "Either 'data' or (path, tree_name, branch, bins) must be provided",
                }

            # Helper to handle potential errors in compute_histogram
            hist_result = self.compute_histogram(
                path=path,  # type: ignore
                tree_name=tree_name,  # type: ignore
                branch=branch,  # type: ignore
                bins=bins,  # type: ignore
                range=range,
                selection=selection,
                weights=weights,
                defines=defines,
            )

            if "error" in hist_result:
                return hist_result

            data = hist_result

        try:
            return fit_histogram(data, model, initial_guess, bounds, fixed_parameters)
        except Exception as e:
            return {
                "error": "fit_error",
                "message": f"Fitting failed: {e}",
            }

    def compute_histogram_arithmetic(
        self,
        operation: str,
        data1: dict[str, Any],
        data2: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Perform histogram arithmetic.

        Args:
            operation: Operation name
            data1: First histogram
            data2: Second histogram
        """
        try:
            return self.analysis_ops.compute_histogram_arithmetic(operation, data1, data2)
        except Exception as e:
            logger.error(f"Arithmetic failed: {e}")
            return {"error": "arithmetic_error", "message": str(e)}

    def generate_plot(
        self,
        data: dict[str, Any],
        plot_type: str = "histogram",
        fit_data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a plot.

        Args:
            data: Analysis data
            plot_type: Plot type
            fit_data: Optional fit to overlay
            options: Plot settings

        Returns:
            Plot image data
        """
        try:
            return generate_plot(data, plot_type, fit_data, options, self.config)
        except Exception as e:
            return {
                "error": "plot_error",
                "message": f"Plotting failed: {e}",
            }

    def apply_selection(
        self,
        path: str,
        tree: str,
        selection: str,
        defines: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Count entries passing a selection.

        Args:
            path: File path
            tree: Tree name
            selection: Cut expression
            defines: Optional variable definitions

        Returns:
            Selection statistics
        """
        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Apply selection
        try:
            result = self.analysis_ops.apply_selection(
                path=str(validated_path),
                tree_name=tree,
                selection=selection,
                defines=defines,
            )
        except Exception as e:
            return {
                "error": "computation_error",
                "message": f"Failed to apply selection: {e}",
            }

        # Add suggestions
        efficiency = result["data"]["efficiency"]
        suggestions = []

        if efficiency < 0.01:
            suggestions.append(
                f"Very tight selection ({efficiency * 100:.3f}%) - "
                "consider loosening cuts or checking syntax"
            )
        elif efficiency > 0.95:
            suggestions.append(
                f"Selection passes most events ({efficiency * 100:.1f}%) - consider tightening cuts"
            )
        else:
            suggestions.append(
                f"{efficiency * 100:.1f}% of events pass selection - "
                "proceed with compute_histogram() or read_branches()"
            )

        result["suggestions"] = suggestions

        return result

    def export_branches(
        self,
        path: str,
        tree: str,
        branches: list[str],
        output_path: str,
        output_format: str,
        selection: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Export branch data to a file.

        Args:
            path: File path
            tree: Tree name
            branches: Branches to export
            output_path: Destination file path
            output_format: Output format (json, csv, parquet)
            selection: Optional cut expression
            limit: Maximum entries to export

        Returns:
            Export metadata
        """
        # Check if export is enabled
        if not self.config.features.enable_export:
            return {
                "error": "feature_disabled",
                "message": "Export feature is disabled",
            }

        # Validate paths
        try:
            validated_input = self.path_validator.validate_path(path)
            validated_output = self.path_validator.validate_output_path(output_path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Check format
        if output_format not in self.config.output.allowed_formats:
            return {
                "error": "invalid_format",
                "message": f"Format '{output_format}' not allowed",
                "details": {"allowed_formats": self.config.output.allowed_formats},
            }

        # Validate limit
        max_export = self.config.limits.max_export_rows
        if limit is None:
            limit = max_export  # Use configured max for export
        if limit > max_export:
            return {
                "error": "limit_exceeded",
                "message": f"Export limit cannot exceed {max_export:,} entries",
            }

        # Read data
        try:
            tree_obj = self.file_manager.get_tree(validated_input, tree)
            arrays = tree_obj.arrays(
                filter_name=branches,
                cut=selection,
                entry_stop=limit,
                library="ak",
            )
        except Exception as e:
            return {
                "error": "read_error",
                "message": f"Failed to read data for export: {e}",
            }

        # Export
        try:
            export_result = self.analysis_ops.export_to_formats(
                data=arrays,
                output_path=str(validated_output),
                format=output_format,
            )
        except Exception as e:
            return {
                "error": "export_error",
                "message": f"Failed to export data: {e}",
            }

        return {
            "data": export_result,
            "metadata": {
                "operation": "export_branches",
            },
            "suggestions": [
                f"Exported {export_result['entries_written']:,} entries to {output_format}",
                f"File size: {export_result['size_bytes'] / 1024 / 1024:.2f} MB",
            ],
        }

    def compute_kinematics(
        self,
        path: str,
        tree: str,
        computations: list[dict[str, Any]],
        selection: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Compute kinematic quantities from four-momenta.

        Args:
            path: File path
            tree: Tree name
            computations: List of kinematic calculations, each dict should have:
                - name: Output variable name
                - type: Calculation type (invariant_mass, invariant_mass_squared,
                        transverse_mass, delta_r, delta_phi)
                - particles: List of particle prefixes (e.g., ['K', 'pi1'])
                - components: Component suffixes (optional, defaults based on type)
            selection: Optional cut expression
            limit: Maximum entries to process

        Returns:
            Dictionary with computed kinematic quantities
        """
        # Validate path
        try:
            validated_path = self.path_validator.validate_path(path)
        except Exception as e:
            return {
                "error": "invalid_path",
                "message": str(e),
            }

        # Validate computations
        if not computations or not isinstance(computations, list):
            return {
                "error": "invalid_parameter",
                "message": "computations must be a non-empty list",
            }

        # Validate each computation
        for comp in computations:
            if not isinstance(comp, dict):
                return {
                    "error": "invalid_parameter",
                    "message": "Each computation must be a dictionary",
                }
            if "name" not in comp:
                return {
                    "error": "invalid_parameter",
                    "message": "Each computation must have a 'name' field",
                }
            if "type" not in comp:
                return {
                    "error": "invalid_parameter",
                    "message": f"Computation '{comp.get('name')}' must have a 'type' field",
                }
            if "particles" not in comp:
                return {
                    "error": "invalid_parameter",
                    "message": f"Computation '{comp.get('name')}' must have a 'particles' field",
                }

        # Apply limit from config if necessary
        if limit is not None and limit > self.config.limits.max_rows_per_call:
            return {
                "error": "limit_exceeded",
                "message": f"Limit cannot exceed {self.config.limits.max_rows_per_call:,} entries",
            }

        # Compute kinematics
        try:
            result = self.analysis_ops.compute_kinematics(
                path=str(validated_path),
                tree_name=tree,
                computations=computations,
                selection=selection,
                limit=limit,
            )
        except ValueError as e:
            return {
                "error": "invalid_parameter",
                "message": str(e),
            }
        except KeyError as e:
            return {
                "error": "branch_not_found",
                "message": f"Required branch not found: {e}",
                "suggestion": "Use list_branches() to see available branches",
            }
        except Exception as e:
            logger.error(f"Failed to compute kinematics: {e}")
            return {
                "error": "computation_error",
                "message": f"Failed to compute kinematics: {e}",
            }

        # Add suggestions
        comp_names = [c["name"] for c in computations]
        suggestions = [
            f"Computed {len(comp_names)} kinematic quantities: {', '.join(comp_names)}",
            f"Processed {result['metadata']['entries_processed']:,} entries",
        ]

        if selection:
            suggestions.append("Selection was applied during computation")

        # Suggest next steps based on computation type
        has_mass = any("mass" in c["type"] for c in computations)
        if has_mass:
            suggestions.append(
                "Use compute_histogram() to visualize mass distributions or "
                "compute_histogram_2d() for Dalitz plots"
            )

        result["suggestions"] = suggestions

        return result
