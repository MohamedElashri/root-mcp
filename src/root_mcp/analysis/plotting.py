"""Plotting module for ROOT-MCP."""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

# Use non-interactive backend
plt.switch_backend("Agg")


def generate_plot(
    data: dict[str, Any],
    plot_type: str = "histogram",
    fit_data: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Generate a plot from analysis data.

    Args:
        data: Analysis result (histogram data)
        plot_type: Type of plot (histogram, etc.)
        fit_data: Optional fit results to overlay
        options: Plotting options (title, labels, etc.)

    Returns:
        Dictionary with base64 encoded image
    """
    if options is None:
        options = {}

    fig, ax = plt.subplots(figsize=(10, 6))

    try:
        if plot_type == "histogram":
            plot_metadata = _plot_histogram(ax, data, fit_data, options)
        else:
            raise ValueError(f"Unsupported plot type: {plot_type}")

        # Customize plot
        branch_name = data.get("metadata", {}).get("branch", "Value")
        unit = options.get("unit", "")

        # X Label
        xlabel = options.get("xlabel", branch_name)
        if unit:
            xlabel += f" [{unit}]"
        ax.set_xlabel(xlabel)

        # Y Label
        ylabel = options.get("ylabel")
        if not ylabel:
            # Auto-generate Y label
            bin_width = plot_metadata.get("bin_width")
            if bin_width:
                # Format properly (e.g. 0.5 or 10)
                width_str = f"{bin_width:.3g}"
                if unit:
                    ylabel = f"Entries / {width_str} {unit}"
                else:
                    ylabel = f"Entries / {width_str}"
            else:
                ylabel = "Entries"
        ax.set_ylabel(ylabel)

        ax.set_title(options.get("title", f"{branch_name} Distribution"))

        # Styling
        if options.get("log_y"):
            ax.set_yscale("log")
        if options.get("log_x"):
            ax.set_xscale("log")

        grid_style = options.get("grid", True)
        if grid_style:
            ax.grid(True, alpha=0.3, which="both" if options.get("log_y") else "major")

        ax.legend()

        # Save to buffer
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=100)
        plt.close(fig)

        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode("utf-8")

        return {"image_type": "png", "image_data": img_str}

    except Exception as e:
        plt.close(fig)
        logger.error(f"Plotting failed: {e}")
        raise RuntimeError(f"Plotting failed: {e}")


def _plot_histogram(
    ax: plt.Axes,
    data: dict[str, Any],
    fit_data: dict[str, Any] | None,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Helper to plot 1D histogram."""
    hist_data = data["data"]
    edges = np.array(hist_data["bin_edges"])
    counts = np.array(hist_data["bin_counts"])

    # Handle errors
    if "bin_errors" in hist_data:
        errors = np.array(hist_data["bin_errors"])
    else:
        errors = np.sqrt(counts)

    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]

    # Plot data points with errors
    color = options.get("color", "black")
    ax.errorbar(
        centers, counts, yerr=errors, fmt="o", color=color, label="Data", markersize=4, capsize=2
    )

    # Plot histogram step
    ax.stairs(counts, edges, fill=True, alpha=0.2, color="blue", label="Hist")

    # Overlay fit if present
    if fit_data:
        fitted_values = fit_data.get("fitted_values")
        if fitted_values:
            # If fit returned values on the same x-coord
            ax.plot(centers, fitted_values, "r-", linewidth=2, label=f"Fit ({fit_data['model']})")

    return {"bin_width": width}
