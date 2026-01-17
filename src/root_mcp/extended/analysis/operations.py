"""High-level analysis operations."""

from __future__ import annotations

import logging
import re
import ast
from typing import TYPE_CHECKING, Any, cast

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.core.io.file_manager import FileManager

from root_mcp.extended.analysis.expression import (
    SafeExprEvaluator,
    translate_leaf_expr,
    strip_outer_parens,
)

logger = logging.getLogger(__name__)


class AnalysisOperations:
    """
    High-level physics analysis operations.

    Provides histogramming, selection, projections, and derived quantities.
    """

    def __init__(self, config: Config, file_manager: FileManager):
        """
        Initialize analysis operations.

        Args:
            config: Server configuration
            file_manager: File manager instance
        """
        self.config = config
        self.file_manager = file_manager

    def _process_defines(self, arrays: ak.Array, defines: dict[str, str] | None) -> ak.Array:
        """
        Process derived variable definitions with dependency resolution.

        Args:
            arrays: Input ak.Array
            defines: Dictionary of {name: expression}

        Returns:
            ak.Array with new fields attached
        """
        if not defines:
            return arrays

        # Create a mutable dict for evaluation
        names = {field: arrays[field] for field in arrays.fields}

        # Topologically sort defines to respect dependencies
        sorted_defines = self._topological_sort_defines(defines, set(arrays.fields))

        for name, expr in sorted_defines:
            try:
                # Evaluate expression
                translated_expr = translate_leaf_expr(expr)
                tree = ast.parse(translated_expr, mode="eval")
                result = SafeExprEvaluator(names).visit(tree)

                # Add to context
                names[name] = result

            except Exception as e:
                logger.error(f"Failed to define {name} = {expr}: {e}")
                raise ValueError(f"Failed to define {name}: {e}")

        # Construct new array with all original + new fields
        return ak.zip(names, depth_limit=1)

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
        dependents_map = {name: [] for name in defines}

        for name, deps in dependencies.items():
            in_degree[name] = len(deps)
            for dep in deps:
                if dep in dependents_map:
                    dependents_map[dep].append(name)

        # Find all nodes with no dependencies (leaves)
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            name = queue.pop(0)
            result.append((name, defines[name]))

            # Notify dependents
            for dependent in dependents_map[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for cycles
        if len(result) != len(defines):
            remaining = set(defines.keys()) - {r[0] for r in result}
            raise ValueError(f"Circular dependency detected in defines: {remaining}")

        return result

    def compute_histogram(
        self,
        path: str | list[str],
        tree_name: str,
        branch: str,
        bins: int,
        range: tuple[float, float] | None = None,
        selection: str | None = None,
        weights: str | None = None,
        defines: dict[str, str] | None = None,
        flatten: bool = True,
    ) -> dict[str, Any]:
        """
        Compute a 1D histogram.

        Args:
            path: File path or list of file paths
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram range (auto if None, based on first file)
            selection: Optional cut expression
            weights: Optional branch for weights
            defines: Optional derived variable definitions
            flatten: Flatten jagged arrays before histogramming

        Returns:
            Histogram data and metadata
        """
        # Validate bins
        if bins > self.config.analysis.histogram.max_bins_1d:
            raise ValueError(
                f"Number of bins ({bins}) exceeds maximum "
                f"({self.config.analysis.histogram.max_bins_1d})"
            )

        paths = [path] if isinstance(path, str) else path
        if not paths:
            raise ValueError("No file paths provided")

        # Accumulators
        total_counts = None
        total_errors_sq = None
        global_edges = None

        # Statistics accumulators
        stat_entries = 0
        stat_sum_w = 0.0
        stat_sum_x = 0.0
        stat_sum_x2 = 0.0
        stat_underflow = 0
        stat_overflow = 0

        # Global range (set on first file if None)
        active_range = range

        for i, p in enumerate(paths):
            tree = self.file_manager.get_tree(p, tree_name)

            # Build list of branches to read
            needed_branches = set()
            if defines:
                for expr in defines.values():
                    needed_branches.update(
                        _extract_branches_from_expression(expr, list(tree.keys()))
                    )

            is_defined_branch = defines and branch in defines
            if not is_defined_branch:
                needed_branches.add(branch)

            if weights:
                is_defined_weight = defines and weights in defines
                if not is_defined_weight:
                    needed_branches.add(weights)

            if selection:
                needed_branches.update(
                    _extract_branches_from_expression(selection, list(tree.keys()))
                )

            available_branches = set(tree.keys())
            branches_to_read = list(needed_branches.intersection(available_branches))

            logger.info(f"Computing histogram for {branch} (file {i + 1}/{len(paths)})")

            # Read data
            arrays = tree.arrays(
                filter_name=branches_to_read,
                library="ak",
            )

            # Process definitions
            if defines:
                arrays = self._process_defines(arrays, defines)

            # Apply selection
            if selection:
                mask = _evaluate_selection_any(arrays, selection)
                arrays = arrays[mask]

            data = arrays[branch]

            # Flatten
            if flatten and _is_list_like(data):
                data = ak.flatten(data)

            data_np = ak.to_numpy(data)

            # Weights
            weights_np = None
            if weights:
                weights_data = arrays[weights]
                if flatten and _is_list_like(weights_data):
                    weights_data = ak.flatten(weights_data)
                weights_np = ak.to_numpy(weights_data)

            # Determine range from first file if needed
            if active_range is None:
                if len(data_np) == 0:
                    active_range = (0.0, 1.0)
                else:
                    active_range = (float(np.min(data_np)), float(np.max(data_np)))
                if len(paths) > 1:
                    logger.warning(
                        f"Range auto-detected from first file: {active_range}. Use this range for consistency."
                    )

            # Compute stats (exact)
            n_entries = len(data_np)
            if n_entries > 0:
                stat_entries += n_entries

                # Careful with weights for mean/std
                if weights_np is not None:
                    w = weights_np
                    stat_sum_w += float(np.sum(w))
                    stat_sum_x += float(np.sum(data_np * w))
                    stat_sum_x2 += float(np.sum((data_np**2) * w))
                else:
                    stat_sum_w += float(n_entries)
                    stat_sum_x += float(np.sum(data_np))
                    stat_sum_x2 += float(np.sum(data_np**2))

            # Compute histogram
            counts, edges = np.histogram(
                data_np,
                bins=bins,
                range=active_range,
                weights=weights_np,
            )

            # Count under/overflow
            stat_underflow += np.sum(data_np < active_range[0], dtype=int)
            stat_overflow += np.sum(data_np > active_range[1], dtype=int)

            # Compute errors squared
            if weights_np is None:
                errors_sq = counts
            else:
                weights_sq = weights_np**2
                errors_sq, _ = np.histogram(
                    data_np, bins=bins, range=active_range, weights=weights_sq
                )

            # Accumulate
            if total_counts is None:
                total_counts = counts
                total_errors_sq = errors_sq
                global_edges = edges
            else:
                total_counts += counts
                total_errors_sq += errors_sq

        # Finalize
        if global_edges is None or total_counts is None or total_errors_sq is None:
            # Should not happen if paths is not empty
            raise RuntimeError("Histogram computation failed: no data produced")

        edges_final = cast(np.ndarray, global_edges)
        counts_final = cast(np.ndarray, total_counts)
        errors_sq_final = cast(np.ndarray, total_errors_sq)

        centers = (edges_final[:-1] + edges_final[1:]) / 2
        final_errors = np.sqrt(errors_sq_final)

        # Compute global mean/std
        mean = 0.0
        std = 0.0
        if stat_sum_w > 0:
            mean = stat_sum_x / stat_sum_w
            # Var = E[x^2] - (E[x])^2
            mean_sq = stat_sum_x2 / stat_sum_w
            var = mean_sq - mean**2
            std = np.sqrt(var) if var > 0 else 0.0

        return {
            "data": {
                "bin_edges": edges_final.tolist(),
                "bin_centers": centers.tolist(),
                "bin_counts": counts_final.tolist(),
                "bin_errors": final_errors.tolist(),
                "underflow": int(stat_underflow),
                "overflow": int(stat_overflow),
                "entries": stat_entries,
                "sum_weights": stat_sum_w,
                "mean": mean,
                "std": std,
            },
            "metadata": {
                "operation": "compute_histogram",
                "branch": branch,
                "bins": bins,
                "range": active_range,
                "selection": selection,
                "weighted": weights is not None,
                "defines": defines,
                "files_processed": len(paths),
            },
        }

    def compute_histogram_2d(
        self,
        path: str | list[str],
        tree_name: str,
        x_branch: str,
        y_branch: str,
        x_bins: int,
        y_bins: int,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        selection: str | None = None,
        defines: dict[str, str] | None = None,
        flatten: bool = True,
    ) -> dict[str, Any]:
        """
        Compute a 2D histogram.

        Args:
            path: File path or list of paths
            tree_name: Tree name
            x_branch: Branch for x-axis
            y_branch: Branch for y-axis
            x_bins: Number of bins in x
            y_bins: Number of bins in y
            x_range: (min, max) for x-axis
            y_range: (min, max) for y-axis
            selection: Optional cut expression
            defines: Optional derived variable definitions
            flatten: Flatten jagged arrays

        Returns:
            2D histogram data and metadata
        """
        # Validate bins
        max_bins = self.config.analysis.histogram.max_bins_2d
        if x_bins > max_bins or y_bins > max_bins:
            raise ValueError(f"Number of bins ({x_bins}, {y_bins}) exceeds maximum ({max_bins})")

        paths = [path] if isinstance(path, str) else path
        if not paths:
            raise ValueError("No file paths provided")

        logger.info(f"Computing 2D histogram: {x_branch} vs {y_branch} ({len(paths)} files)")

        # Accumulators
        total_counts = None
        global_x_edges = None
        global_y_edges = None
        total_entries = 0

        active_x_range = x_range
        active_y_range = y_range

        for i, p in enumerate(paths):
            tree = self.file_manager.get_tree(p, tree_name)

            # Build list of branches to read (reusing logic)
            needed_branches = set()
            if defines:
                for expr in defines.values():
                    needed_branches.update(
                        _extract_branches_from_expression(expr, list(tree.keys()))
                    )

            is_defined_x = defines and x_branch in defines
            if not is_defined_x:
                needed_branches.add(x_branch)

            is_defined_y = defines and y_branch in defines
            if not is_defined_y:
                needed_branches.add(y_branch)

            if selection:
                needed_branches.update(
                    _extract_branches_from_expression(selection, list(tree.keys()))
                )

            available_branches = set(tree.keys())
            branches_to_read = list(needed_branches.intersection(available_branches))

            # Read data
            arrays = tree.arrays(
                filter_name=branches_to_read,
                library="ak",
            )

            # Process defines
            if defines:
                arrays = self._process_defines(arrays, defines)

            # Apply selection
            if selection:
                mask = _evaluate_selection_any(arrays, selection)
                arrays = arrays[mask]

            x_data = arrays[x_branch]
            y_data = arrays[y_branch]

            # Flatten if jagged
            if flatten:
                if _is_list_like(x_data):
                    x_data = ak.flatten(x_data)
                if _is_list_like(y_data):
                    y_data = ak.flatten(y_data)

            # Convert to numpy
            x_np = ak.to_numpy(x_data)
            y_np = ak.to_numpy(y_data)

            total_entries += len(x_np)

            # Determine ranges if not provided (from first file)
            if active_x_range is None:
                if len(x_np) == 0:
                    active_x_range = (0.0, 1.0)
                else:
                    active_x_range = (float(np.min(x_np)), float(np.max(x_np)))

            if active_y_range is None:
                if len(y_np) == 0:
                    active_y_range = (0.0, 1.0)
                else:
                    active_y_range = (float(np.min(y_np)), float(np.max(y_np)))

            if len(paths) > 1 and i == 0 and (x_range is None or y_range is None):
                logger.warning(
                    f"2D Ranges auto-detected from first file. X: {active_x_range}, Y: {active_y_range}"
                )

            # Compute 2D histogram
            counts, x_edges, y_edges = np.histogram2d(
                x_np,
                y_np,
                bins=[x_bins, y_bins],
                range=[active_x_range, active_y_range],
            )

            if total_counts is None:
                total_counts = counts
                global_x_edges = x_edges
                global_y_edges = y_edges
            else:
                total_counts += counts

        if total_counts is None or global_x_edges is None or global_y_edges is None:
            # Should not happen if paths is not empty
            raise RuntimeError("Histogram computation failed: no data produced")

        x_edges_final = cast(np.ndarray, global_x_edges)
        y_edges_final = cast(np.ndarray, global_y_edges)
        counts_final = cast(np.ndarray, total_counts)

        # Compute bin centers
        x_centers = (x_edges_final[:-1] + x_edges_final[1:]) / 2
        y_centers = (y_edges_final[:-1] + y_edges_final[1:]) / 2

        return {
            "data": {
                "x_edges": x_edges_final.tolist(),
                "x_centers": x_centers.tolist(),
                "y_edges": y_edges_final.tolist(),
                "y_centers": y_centers.tolist(),
                "counts": counts_final.tolist(),
                "entries": total_entries,
            },
            "metadata": {
                "operation": "compute_histogram_2d",
                "x_branch": x_branch,
                "y_branch": y_branch,
                "selection": selection,
                "defines": defines,
                "files_processed": len(paths),
            },
        }

    def compute_histogram_arithmetic(
        self,
        operation: str,
        data1: dict[str, Any],
        data2: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Perform arithmetic on two histograms.

        Args:
            operation: One of "add", "subtract", "multiply", "divide", "asymmetry"
            data1: First histogram object
            data2: Second histogram object

        Returns:
            New histogram object with computed values.
        """
        # Normalize input (handle if wrapped in {"data": ...} or direct)
        d1 = data1["data"] if "data" in data1 else data1
        d2 = data2["data"] if "data" in data2 else data2

        # Detect dimensionality
        is_1d = "bin_counts" in d1
        is_2d = "counts" in d1

        if not is_1d and not is_2d:
            raise ValueError("data1 format not recognized (must have 'bin_counts' or 'counts')")

        # Validate compatibility
        if is_1d:
            if "bin_counts" not in d2:
                raise ValueError("Mismatch: data1 is 1D, data2 is not.")
            # Check edges
            edges1 = np.array(d1["bin_edges"])
            edges2 = np.array(d2["bin_edges"])
            if not np.allclose(edges1, edges2):
                raise ValueError("Bin edges do not match.")

            c1 = np.array(d1["bin_counts"])
            c2 = np.array(d2["bin_counts"])
            e1 = np.array(d1["bin_errors"]) if "bin_errors" in d1 else np.sqrt(c1)
            e2 = np.array(d2["bin_errors"]) if "bin_errors" in d2 else np.sqrt(c2)

        elif is_2d:
            if "counts" not in d2:
                raise ValueError("Mismatch: data1 is 2D, data2 is not.")
            x_edges1 = np.array(d1["x_edges"])
            x_edges2 = np.array(d2["x_edges"])
            y_edges1 = np.array(d1["y_edges"])
            y_edges2 = np.array(d2["y_edges"])

            if not np.allclose(x_edges1, x_edges2) or not np.allclose(y_edges1, y_edges2):
                raise ValueError("2D Bin edges do not match.")

            c1 = np.array(d1["counts"])
            c2 = np.array(d2["counts"])
            # 2D usually doesn't have errors in simple output, estimate sqrt(N)
            e1 = np.sqrt(c1)
            e2 = np.sqrt(c2)

        # Perform operation
        with np.errstate(divide="ignore", invalid="ignore"):
            if operation == "add":
                c_out = c1 + c2
                e_out = np.sqrt(e1**2 + e2**2)
            elif operation == "subtract":
                c_out = c1 - c2
                e_out = np.sqrt(e1**2 + e2**2)
            elif operation == "multiply":
                c_out = c1 * c2
                # err(A*B) approx |A*B| * sqrt((eA/A)^2 + (eB/B)^2)
                # Avoid div by zero
                term1 = np.divide(e1, c1, out=np.zeros_like(e1), where=c1 != 0) ** 2
                term2 = np.divide(e2, c2, out=np.zeros_like(e2), where=c2 != 0) ** 2
                e_out = np.abs(c_out) * np.sqrt(term1 + term2)
            elif operation == "divide":
                c_out = np.divide(c1, c2, out=np.zeros_like(c1), where=c2 != 0)
                # err(A/B) approx |A/B| * sqrt((eA/A)^2 + (eB/B)^2)
                term1 = np.divide(e1, c1, out=np.zeros_like(e1), where=c1 != 0) ** 2
                term2 = np.divide(e2, c2, out=np.zeros_like(e2), where=c2 != 0) ** 2
                e_out = np.abs(c_out) * np.sqrt(term1 + term2)
            elif operation == "asymmetry":
                # (A-B)/(A+B)
                num = c1 - c2
                denom = c1 + c2
                c_out = np.divide(num, denom, out=np.zeros_like(num), where=denom != 0)

                # Asymmetry error: 2/(A+B)^2 * sqrt( B^2 eA^2 + A^2 eB^2 )
                denom_sq = denom**2
                prefactor = np.divide(2, denom_sq, out=np.zeros_like(denom), where=denom_sq != 0)
                inner = (c2 * e1) ** 2 + (c1 * e2) ** 2
                e_out = prefactor * np.sqrt(inner)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        # Construct result
        res_data = d1.copy()
        if is_1d:
            res_data["bin_counts"] = c_out.tolist()
            res_data["bin_errors"] = e_out.tolist()
            # Update stats? approximate
            res_data["entries"] = int(np.sum(c_out)) if operation in ["add", "subtract"] else 0
            res_data["sum_weights"] = float(np.sum(c_out))
        else:
            res_data["counts"] = c_out.tolist()
            # 2D output doesn't usually carry errors array in current schema,
            # but plot_histogram_2d accepts "counts".
            # We can add "errors" if we want extended schema support later.
            res_data["entries"] = int(np.sum(c_out)) if operation in ["add", "subtract"] else 0

        return {
            "data": res_data,
            "metadata": {
                "operation": "histogram_arithmetic",
                "mode": operation,
                "input_1": data1.get("metadata", {}).get("branch", "custom"),
                "input_2": data2.get("metadata", {}).get("branch", "custom"),
            },
        }

    def apply_selection(
        self,
        path: str,
        tree_name: str,
        selection: str,
        defines: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Count entries passing a selection.

        Args:
            path: File path
            tree_name: Tree name
            selection: Cut expression
            defines: Optional variable definitions

        Returns:
            Selection statistics
        """
        tree = self.file_manager.get_tree(path, tree_name)
        total_entries = tree.num_entries
        logger.info(f"Applying selection to {tree_name}: {selection}")

        # Need to read in chunks if defines are involved?
        # If defines are involved, we might need all branches they depend on.
        # But apply_selection is often optimized to read only needed branches.

        # Determine needed branches
        needed_branches = set()
        needed_branches.update(_extract_branches_from_expression(selection, list(tree.keys())))
        if defines:
            for expr in defines.values():
                needed_branches.update(_extract_branches_from_expression(expr, list(tree.keys())))

        available_branches = set(tree.keys())
        branches_to_read = list(needed_branches.intersection(available_branches))
        if not branches_to_read:
            branches_to_read = tree.keys()[0:1]  # Fallback in case of no branches

        chunk_size = self.config.analysis.default_chunk_size
        selected_entries = 0
        entry_start = 0

        while entry_start < total_entries:
            entry_stop = min(entry_start + chunk_size, total_entries)
            arrays = tree.arrays(
                filter_name=branches_to_read,
                entry_start=entry_start,
                entry_stop=entry_stop,
                library="ak",
            )
            if len(arrays) == 0:
                entry_start = entry_stop
                continue

            if defines:
                arrays = self._process_defines(arrays, defines)

            mask = _evaluate_selection_any(arrays, selection)
            selected_entries += int(ak.sum(mask))
            entry_start = entry_stop

        efficiency = selected_entries / total_entries if total_entries > 0 else 0.0

        return {
            "data": {
                "entries_total": total_entries,
                "entries_selected": selected_entries,
                "efficiency": efficiency,
                "selection": selection,
            },
            "metadata": {
                "operation": "apply_selection",
                "defines": defines,
            },
        }

    def compute_profile(
        self,
        path: str,
        tree_name: str,
        x_branch: str,
        y_branch: str,
        x_bins: int,
        x_range: tuple[float, float] | None = None,
        selection: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute a profile histogram (mean of y vs binned x).

        Args:
            path: File path
            tree_name: Tree name
            x_branch: Branch to bin
            y_branch: Branch to average
            x_bins: Number of bins in x
            x_range: (min, max) for x-axis
            selection: Optional cut

        Returns:
            Profile data and metadata
        """
        tree = self.file_manager.get_tree(path, tree_name)

        # Read data
        arrays = tree.arrays(
            filter_name=[x_branch, y_branch],
            cut=selection,
            library="ak",
        )

        x_data = ak.to_numpy(ak.flatten(arrays[x_branch]))
        y_data = ak.to_numpy(ak.flatten(arrays[y_branch]))

        # Determine x range
        if x_range is None:
            x_range = (float(np.min(x_data)), float(np.max(x_data)))

        # Digitize x values
        x_edges = np.linspace(x_range[0], x_range[1], x_bins + 1)
        bin_indices = np.digitize(x_data, x_edges) - 1

        # Compute mean and error for each bin
        means = []
        errors = []
        entries = []

        for i in range(x_bins):
            mask = bin_indices == i
            y_in_bin = y_data[mask]

            if len(y_in_bin) > 0:
                means.append(float(np.mean(y_in_bin)))
                errors.append(float(np.std(y_in_bin) / np.sqrt(len(y_in_bin))))
                entries.append(len(y_in_bin))
            else:
                means.append(0.0)
                errors.append(0.0)
                entries.append(0)

        return {
            "data": {
                "bin_edges": x_edges.tolist(),
                "bin_means": means,
                "bin_errors": errors,
                "bin_entries": entries,
            },
            "metadata": {
                "operation": "compute_profile",
                "x_branch": x_branch,
                "y_branch": y_branch,
                "selection": selection,
            },
        }

    def compute_kinematics(
        self,
        path: str,
        tree_name: str,
        computations: list[dict[str, Any]],
        selection: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Compute kinematic quantities from four-momenta.

        Args:
            path: File path
            tree_name: Tree name
            computations: List of kinematic calculations, each dict should have:
                - name: Output variable name
                - type: Calculation type (invariant_mass, invariant_mass_squared,
                        transverse_mass, delta_r, delta_phi)
                - particles: List of particle prefixes
                - components: Component suffixes (default based on type)
            selection: Optional cut expression
            limit: Maximum entries to process

        Returns:
            Dictionary with computed kinematic quantities
        """
        # Collect all branches we need to read
        branches_needed = set()
        for comp in computations:
            comp_type = comp.get("type", "")
            particles = comp.get("particles", [])

            if comp_type in ["invariant_mass", "invariant_mass_squared", "transverse_mass"]:
                components = comp.get("components", ["PX", "PY", "PZ", "PE"])
                for particle in particles:
                    for component in components:
                        branches_needed.add(f"{particle}_{component}")

            elif comp_type in ["delta_r"]:
                eta_suffix = comp.get("eta_suffix", "ETA")
                phi_suffix = comp.get("phi_suffix", "PHI")
                if len(particles) != 2:
                    raise ValueError(f"delta_r requires exactly 2 particles, got {len(particles)}")
                branches_needed.add(f"{particles[0]}_{eta_suffix}")
                branches_needed.add(f"{particles[0]}_{phi_suffix}")
                branches_needed.add(f"{particles[1]}_{eta_suffix}")
                branches_needed.add(f"{particles[1]}_{phi_suffix}")

            elif comp_type == "delta_phi":
                phi_suffix = comp.get("phi_suffix", "PHI")
                if len(particles) != 2:
                    raise ValueError(
                        f"delta_phi requires exactly 2 particles, got {len(particles)}"
                    )
                branches_needed.add(f"{particles[0]}_{phi_suffix}")
                branches_needed.add(f"{particles[1]}_{phi_suffix}")

        # Open file and read branches
        tree = self.file_manager.get_tree(path, tree_name)

        # Apply limit
        entry_stop = limit if limit is not None else None

        # Read arrays
        arrays = tree.arrays(
            filter_name=list(branches_needed),
            cut=selection,
            entry_stop=entry_stop,
            library="ak",
        )

        # Compute each requested quantity
        results = {}
        for comp in computations:
            name = comp.get("name")
            comp_type = comp.get("type")
            particles = comp.get("particles", [])

            if not name:
                raise ValueError("Each computation must have a 'name'")
            if not comp_type:
                raise ValueError(f"Computation '{name}' must have a 'type'")

            try:
                if comp_type == "invariant_mass":
                    components = comp.get("components", ["PX", "PY", "PZ", "PE"])
                    result = _compute_invariant_mass(arrays, particles, components, squared=False)
                    results[name] = ak.to_list(result)

                elif comp_type == "invariant_mass_squared":
                    components = comp.get("components", ["PX", "PY", "PZ", "PE"])
                    result = _compute_invariant_mass(arrays, particles, components, squared=True)
                    results[name] = ak.to_list(result)

                elif comp_type == "transverse_mass":
                    components = comp.get("components", ["PX", "PY", "PZ", "PE"])
                    result = _compute_transverse_mass(arrays, particles, components)
                    results[name] = ak.to_list(result)

                elif comp_type == "delta_r":
                    eta_suffix = comp.get("eta_suffix", "ETA")
                    phi_suffix = comp.get("phi_suffix", "PHI")
                    result = _compute_delta_r(
                        arrays, particles[0], particles[1], eta_suffix, phi_suffix
                    )
                    results[name] = ak.to_list(result)

                elif comp_type == "delta_phi":
                    phi_suffix = comp.get("phi_suffix", "PHI")
                    result = _compute_delta_phi(arrays, particles[0], particles[1], phi_suffix)
                    results[name] = ak.to_list(result)

                else:
                    raise ValueError(f"Unknown computation type: {comp_type}")

            except Exception as e:
                logger.error(f"Failed to compute {name}: {e}")
                raise ValueError(f"Failed to compute {name}: {e}")

        return {
            "data": results,
            "metadata": {
                "operation": "compute_kinematics",
                "tree": tree_name,
                "entries_processed": len(arrays),
                "computations": [{"name": c["name"], "type": c["type"]} for c in computations],
                "selection": selection,
            },
        }

    def export_to_formats(
        self,
        data: ak.Array,
        output_path: str,
        format: str,
    ) -> dict[str, Any]:
        """
        Export data to various formats.

        Args:
            data: Awkward array to export
            output_path: Destination path
            format: Output format (json, csv, parquet)

        Returns:
            Export metadata
        """
        from pathlib import Path
        import json

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            # Convert to list and write JSON
            data_list = ak.to_list(data)
            with open(output_path_obj, "w") as f:
                json.dump(data_list, f, indent=2)

        elif format == "csv":
            # Convert to pandas and write CSV
            import pandas as pd

            df = pd.DataFrame(ak.to_list(data))
            df.to_csv(output_path_obj, index=False)

        elif format == "parquet":
            # Write as Parquet
            import pyarrow.parquet as pq

            table = ak.to_arrow_table(data)
            pq.write_table(table, output_path_obj)

        else:
            raise ValueError(f"Unsupported format: {format}")

        # Get file size
        size_bytes = output_path_obj.stat().st_size

        return {
            "output_path": str(output_path_obj),
            "format": format,
            "entries_written": len(data),
            "size_bytes": size_bytes,
        }


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


def _extract_branches_from_expression(selection: str, available_branches: list[str]) -> list[str]:
    available = set(available_branches)
    tokens = set(re.findall(r"[A-Za-z_]\w*", selection))
    reserved = {
        "and",
        "or",
        "not",
        "true",
        "false",
        "abs",
        "sqrt",
        "log",
        "exp",
        "sin",
        "cos",
        "tan",
        "arcsin",
        "arccos",
        "arctan",
        "min",
        "max",
        "where",
        "sinh",
        "cosh",
        "tanh",
        "arcsin",
        "arccos",
        "arctan",
        "arctan2",
    }
    return sorted([t for t in tokens if t in available and t not in reserved])


def _split_top_level(expr: str, sep: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1

        if depth == 0 and expr.startswith(sep, i):
            parts.append(expr[start:i].strip())
            i += len(sep)
            start = i
            continue

        i += 1

    parts.append(expr[start:].strip())
    return [p for p in parts if p]


def _eval_leaf(arrays: ak.Array, expr: str) -> Any:
    expr = translate_leaf_expr(expr)
    names = {field: arrays[field] for field in arrays.fields}
    tree = ast.parse(expr, mode="eval")
    return SafeExprEvaluator(names).visit(tree)


def _evaluate_selection_any(arrays: ak.Array, selection: str) -> ak.Array:
    expr = strip_outer_parens(selection)

    or_parts = _split_top_level(expr, "||")
    if len(or_parts) > 1:
        mask = _evaluate_selection_any(arrays, or_parts[0])
        for part in or_parts[1:]:
            mask = mask | _evaluate_selection_any(arrays, part)
        return mask

    and_parts = _split_top_level(expr, "&&")
    if len(and_parts) > 1:
        mask = _evaluate_selection_any(arrays, and_parts[0])
        for part in and_parts[1:]:
            mask = mask & _evaluate_selection_any(arrays, part)
        return mask

    term = strip_outer_parens(expr)
    neg = False
    while term.startswith("!") and not term.startswith("!="):
        neg = not neg
        term = term[1:].strip()

    result = _eval_leaf(arrays, term)
    if neg:
        result = ~result

    if _is_list_like(result):
        result = ak.any(result, axis=1)
    elif isinstance(result, (bool, np.bool_)):
        result = ak.Array([bool(result)] * len(arrays))

    return result


def _compute_invariant_mass(
    arrays: ak.Array,
    particles: list[str],
    components: list[str],
    squared: bool = False,
) -> ak.Array:
    """
    Compute invariant mass from four-momenta.

    Args:
        arrays: Input arrays with four-momentum components
        particles: List of particle prefixes (e.g., ['K', 'pi1'])
        components: Component suffixes (e.g., ['PX', 'PY', 'PZ', 'PE'])
        squared: Return m² instead of m

    Returns:
        Array of invariant masses
    """
    if len(components) != 4:
        raise ValueError("Need exactly 4 components for invariant mass (px, py, pz, E)")

    # Sum four-momenta
    px_total = sum(arrays[f"{p}_{components[0]}"] for p in particles)
    py_total = sum(arrays[f"{p}_{components[1]}"] for p in particles)
    pz_total = sum(arrays[f"{p}_{components[2]}"] for p in particles)
    E_total = sum(arrays[f"{p}_{components[3]}"] for p in particles)

    # Compute invariant mass squared: m² = E² - p²
    m_squared = E_total**2 - px_total**2 - py_total**2 - pz_total**2

    if squared:
        return m_squared
    else:
        # Handle negative values (should be rare, but can occur from numerical precision)
        return np.sqrt(np.maximum(m_squared, 0))


def _compute_transverse_mass(
    arrays: ak.Array,
    particles: list[str],
    components: list[str],
) -> ak.Array:
    """
    Compute transverse mass.

    Args:
        arrays: Input arrays
        particles: List of particle prefixes
        components: Component suffixes (px, py, E)

    Returns:
        Array of transverse masses
    """
    if len(components) < 3:
        raise ValueError("Need at least 3 components (px, py, E)")

    px_total = sum(arrays[f"{p}_{components[0]}"] for p in particles)
    py_total = sum(arrays[f"{p}_{components[1]}"] for p in particles)
    E_total = sum(
        arrays[f"{p}_{components[3] if len(components) > 3 else components[2]}"] for p in particles
    )

    mt_squared = E_total**2 - px_total**2 - py_total**2

    return np.sqrt(np.maximum(mt_squared, 0))


def _compute_delta_r(
    arrays: ak.Array,
    particle1: str,
    particle2: str,
    eta_suffix: str = "ETA",
    phi_suffix: str = "PHI",
) -> ak.Array:
    """
    Compute ΔR = sqrt(Δη² + Δφ²) between two particles.

    Args:
        arrays: Input arrays
        particle1: First particle prefix
        particle2: Second particle prefix
        eta_suffix: Pseudorapidity suffix
        phi_suffix: Azimuthal angle suffix

    Returns:
        Array of ΔR values
    """
    eta1 = arrays[f"{particle1}_{eta_suffix}"]
    eta2 = arrays[f"{particle2}_{eta_suffix}"]
    phi1 = arrays[f"{particle1}_{phi_suffix}"]
    phi2 = arrays[f"{particle2}_{phi_suffix}"]

    delta_eta = eta1 - eta2
    delta_phi = phi1 - phi2

    # Wrap delta_phi to [-π, π]
    delta_phi = np.arctan2(np.sin(delta_phi), np.cos(delta_phi))

    return np.sqrt(delta_eta**2 + delta_phi**2)


def _compute_delta_phi(
    arrays: ak.Array,
    particle1: str,
    particle2: str,
    phi_suffix: str = "PHI",
) -> ak.Array:
    """
    Compute Δφ between two particles, wrapped to [-π, π].

    Args:
        arrays: Input arrays
        particle1: First particle prefix
        particle2: Second particle prefix
        phi_suffix: Azimuthal angle suffix

    Returns:
        Array of Δφ values
    """
    phi1 = arrays[f"{particle1}_{phi_suffix}"]
    phi2 = arrays[f"{particle2}_{phi_suffix}"]

    delta_phi = phi1 - phi2

    # Wrap to [-π, π]
    return np.arctan2(np.sin(delta_phi), np.cos(delta_phi))
