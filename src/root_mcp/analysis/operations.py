"""High-level analysis operations."""

from __future__ import annotations

import logging
import re
import ast
from typing import TYPE_CHECKING, Any

import awkward as ak
import numpy as np

if TYPE_CHECKING:
    from root_mcp.config import Config
    from root_mcp.io.file_manager import FileManager

from root_mcp.analysis.expression import SafeExprEvaluator, translate_leaf_expr, strip_outer_parens

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
        Process derived variable definitions.

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

        # We need to respect dependencies, so we ideally sort them topologicaly
        # For now, we assume user defines things in order or independent
        # A robust solution would parse all dependencies first

        for name, expr in defines.items():
            try:
                # Evaluate expression
                # We reuse the safe evaluator logic
                translated_expr = translate_leaf_expr(expr)
                tree = ast.parse(translated_expr, mode="eval")
                result = SafeExprEvaluator(names).visit(tree)

                # Add to context
                names[name] = result

                # Ideally add back to array, but ak.Array is immutable in structure
                # We can simulate it by keeping the 'names' dict as the truth
                # For downstream consumers expecting an array with fields, we can zip it up

            except Exception as e:
                logger.error(f"Failed to define {name} = {expr}: {e}")
                raise ValueError(f"Failed to define {name}: {e}")

        # Construct new array with all original + new fields
        # This is expensive if we duplicate data, so we use zip
        return ak.zip(names, depth_limit=1)

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
        flatten: bool = True,
    ) -> dict[str, Any]:
        """
        Compute a 1D histogram.

        Args:
            path: File path
            tree_name: Tree name
            branch: Branch to histogram
            bins: Number of bins
            range: (min, max) for histogram range (auto if None)
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

        tree = self.file_manager.get_tree(path, tree_name)

        # Build list of branches to read
        # Must include branches used in defines
        needed_branches = set()
        if defines:
            for expr in defines.values():
                needed_branches.update(_extract_branches_from_expression(expr, list(tree.keys())))

        # If branch is a defined variable, we don't need to read it from tree directly
        # checks if branch is in tree, if not, assume it is defined
        is_defined_branch = defines and branch in defines
        if not is_defined_branch:
            needed_branches.add(branch)

        if weights:
            is_defined_weight = defines and weights in defines
            if not is_defined_weight:
                needed_branches.add(weights)

        if selection:
            needed_branches.update(_extract_branches_from_expression(selection, list(tree.keys())))

        # Filter available branches
        available_branches = set(tree.keys())
        branches_to_read = list(needed_branches.intersection(available_branches))

        logger.info(
            f"Computing histogram for {branch} with {bins} bins (defines: {list(defines.keys()) if defines else 'None'})"
        )

        # Read data
        arrays = tree.arrays(
            filter_name=branches_to_read,
            library="ak",
        )

        # Process definitions
        if defines:
            arrays = self._process_defines(arrays, defines)

        # Apply selection AFTER definitions (so we can cut on defined variables)
        if selection:
            mask = _evaluate_selection_any(arrays, selection)
            arrays = arrays[mask]

        data = arrays[branch]

        # Flatten if jagged and requested
        if flatten and _is_list_like(data):
            data = ak.flatten(data)

        # Convert to numpy
        data_np = ak.to_numpy(data)

        # Get weights if specified
        weights_np = None
        if weights:
            weights_data = arrays[weights]
            if flatten and _is_list_like(weights_data):
                weights_data = ak.flatten(weights_data)
            weights_np = ak.to_numpy(weights_data)

        # Determine range if not provided
        if range is None:
            if len(data_np) == 0:
                range = (0.0, 1.0)
            else:
                range = (float(np.min(data_np)), float(np.max(data_np)))

        # Compute histogram
        counts, edges = np.histogram(
            data_np,
            bins=bins,
            range=range,
            weights=weights_np,
        )

        # Compute errors (sqrt(N) for unweighted, proper for weighted)
        if weights_np is None:
            errors = np.sqrt(counts)
        else:
            # For weighted histograms, error is sqrt(sum of weights squared)
            weights_sq = weights_np**2
            errors_sq, _ = np.histogram(data_np, bins=bins, range=range, weights=weights_sq)
            errors = np.sqrt(errors_sq)

        # Count underflow/overflow
        underflow = np.sum(data_np < range[0], dtype=int)
        overflow = np.sum(data_np > range[1], dtype=int)

        # Statistics
        total_entries = len(data_np)
        if total_entries > 0:
            mean = float(np.mean(data_np))
            std = float(np.std(data_np))
        else:
            mean = 0.0
            std = 0.0

        return {
            "data": {
                "bin_edges": edges.tolist(),
                "bin_counts": counts.tolist(),
                "bin_errors": errors.tolist(),
                "underflow": int(underflow),
                "overflow": int(overflow),
                "entries": total_entries,
                "sum_weights": float(np.sum(counts)),
                "mean": mean,
                "std": std,
            },
            "metadata": {
                "operation": "compute_histogram",
                "branch": branch,
                "bins": bins,
                "range": range,
                "selection": selection,
                "weighted": weights is not None,
                "defines": defines,
            },
        }

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
        flatten: bool = True,
    ) -> dict[str, Any]:
        """
        Compute a 2D histogram.

        Args:
            path: File path
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

        tree = self.file_manager.get_tree(path, tree_name)

        logger.info(f"Computing 2D histogram: {x_branch} vs {y_branch}")

        # Build list of branches to read (reusing logic)
        needed_branches = set()
        if defines:
            for expr in defines.values():
                needed_branches.update(_extract_branches_from_expression(expr, list(tree.keys())))

        is_defined_x = defines and x_branch in defines
        if not is_defined_x:
            needed_branches.add(x_branch)

        is_defined_y = defines and y_branch in defines
        if not is_defined_y:
            needed_branches.add(y_branch)

        if selection:
            needed_branches.update(_extract_branches_from_expression(selection, list(tree.keys())))

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

        # Determine ranges if not provided
        if x_range is None:
            x_range = (float(np.min(x_np)), float(np.max(x_np)))
        if y_range is None:
            y_range = (float(np.min(y_np)), float(np.max(y_np)))

        # Compute 2D histogram
        counts, x_edges, y_edges = np.histogram2d(
            x_np,
            y_np,
            bins=[x_bins, y_bins],
            range=[x_range, y_range],
        )

        return {
            "data": {
                "x_edges": x_edges.tolist(),
                "y_edges": y_edges.tolist(),
                "counts": counts.tolist(),
                "entries": len(x_np),
            },
            "metadata": {
                "operation": "compute_histogram_2d",
                "x_branch": x_branch,
                "y_branch": y_branch,
                "selection": selection,
                "defines": defines,
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
