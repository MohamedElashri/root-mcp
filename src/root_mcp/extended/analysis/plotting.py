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
    config: Any | None = None,
) -> dict[str, str]:
    """
    Generate a plot from analysis data.

    Args:
        data: Analysis result (histogram data)
        plot_type: Type of plot (histogram, etc.)
        fit_data: Optional fit results to overlay
        options: Plotting options (title, labels, etc.)
        config: Configuration object with plotting settings

    Returns:
        Dictionary with base64 encoded image
    """
    if options is None:
        options = {}

    # Get plotting config or use defaults
    if config and hasattr(config, "analysis") and hasattr(config.analysis, "plotting"):
        plot_cfg = config.analysis.plotting
        figsize = (plot_cfg.figure_width, plot_cfg.figure_height)
    else:
        figsize = (10, 6)

    fig, ax = plt.subplots(figsize=figsize)

    try:
        if plot_type == "histogram":
            plot_metadata = _plot_histogram(ax, data, fit_data, options, config)

            # Customize 1D histogram plot
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

            # Get grid alpha from config
            if config and hasattr(config, "analysis") and hasattr(config.analysis, "plotting"):
                plot_cfg = config.analysis.plotting
                grid_alpha = plot_cfg.grid_alpha
                grid_enabled = plot_cfg.grid_enabled
            else:
                grid_alpha = 0.3
                grid_enabled = True

            grid_style = options.get("grid", grid_enabled)
            if grid_style:
                ax.grid(True, alpha=grid_alpha, which="both" if options.get("log_y") else "major")

            ax.legend()

        elif plot_type == "histogram_2d":
            _plot_histogram_2d(fig, ax, data, options, config)

        else:
            raise ValueError(f"Unsupported plot type: {plot_type}")

        # Get DPI from config
        if config and hasattr(config, "analysis") and hasattr(config.analysis, "plotting"):
            dpi = config.analysis.plotting.dpi
        else:
            dpi = 100

        # Save to buffer
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=dpi)
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
    config: Any | None = None,
) -> dict[str, Any]:
    """Helper to plot 1D histogram."""
    # Handle both formats:
    # 1. Full histogram result: {"data": {...}, "metadata": {...}}
    # 2. Just the data dict: {"bin_edges": [...], "bin_counts": [...]}
    if "data" in data and "bin_edges" not in data:
        hist_data = data["data"]
    else:
        hist_data = data

    edges = np.array(hist_data["bin_edges"])
    counts = np.array(hist_data["bin_counts"])

    # Handle errors
    if "bin_errors" in hist_data:
        errors = np.array(hist_data["bin_errors"])
    else:
        errors = np.sqrt(counts)

    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]

    # Get plotting config or use defaults
    if config and hasattr(config, "analysis") and hasattr(config.analysis, "plotting"):
        plot_cfg = config.analysis.plotting
        data_color = plot_cfg.data_color
        marker_size = plot_cfg.marker_size
        marker_style = plot_cfg.marker_style
        cap_size = plot_cfg.error_bar_cap_size
        hist_alpha = plot_cfg.hist_fill_alpha
        hist_color = plot_cfg.hist_fill_color
        line_width = plot_cfg.line_width
        fit_color = plot_cfg.fit_line_color
        fit_style = plot_cfg.fit_line_style
    else:
        data_color = "black"
        marker_size = 4.0
        marker_style = "o"
        cap_size = 2.0
        hist_alpha = 0.2
        hist_color = "blue"
        line_width = 2.0
        fit_color = "red"
        fit_style = "-"

    # Plot data points with errors
    color = options.get("color", data_color)
    ax.errorbar(
        centers,
        counts,
        yerr=errors,
        fmt=marker_style,
        color=color,
        label="Data",
        markersize=marker_size,
        capsize=cap_size,
    )

    # Plot histogram step
    ax.stairs(counts, edges, fill=True, alpha=hist_alpha, color=hist_color, label="Hist")

    # Overlay fit if present
    if fit_data:
        fitted_values = fit_data.get("fitted_values")
        if fitted_values:
            # If fit returned values on the same x-coord
            ax.plot(
                centers,
                fitted_values,
                fit_style,
                linewidth=line_width,
                color=fit_color,
                label=f"Fit ({fit_data['model']})",
            )

    return {"bin_width": width}


def _plot_histogram_2d(
    fig: plt.Figure,
    ax: plt.Axes,
    data: dict[str, Any],
    options: dict[str, Any],
    config: Any | None = None,
) -> None:
    """Helper to plot 2D histogram."""
    # Handle both formats
    if "data" in data:
        hist_data = data["data"]
    else:
        hist_data = data

    # Handle different field naming conventions
    # HistogramOperations uses: bin_edges_x, bin_edges_y, bin_counts
    # AnalysisOperations uses: x_edges, y_edges, counts
    edges_x = np.array(hist_data.get("bin_edges_x") or hist_data.get("x_edges"))
    edges_y = np.array(hist_data.get("bin_edges_y") or hist_data.get("y_edges"))
    counts = np.array(hist_data.get("bin_counts") or hist_data.get("counts"))

    # Get options
    colormap = options.get("colormap", "viridis")
    log_z = options.get("log_z", False)
    title = options.get("title", "2D Histogram")
    xlabel = options.get("xlabel", "X")
    ylabel = options.get("ylabel", "Y")

    # Apply log scale to counts if requested
    plot_counts = counts.T  # Transpose for correct orientation
    if log_z:
        plot_counts = np.where(plot_counts > 0, np.log10(plot_counts), 0)

    # Create 2D histogram plot
    im = ax.pcolormesh(edges_x, edges_y, plot_counts, cmap=colormap, shading="auto")

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    if log_z:
        cbar.set_label("log10(Entries)")
    else:
        cbar.set_label("Entries")

    # Set labels and title
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
