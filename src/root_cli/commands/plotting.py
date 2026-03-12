"""Plotting commands for root-cli."""

import json
import click
from pathlib import Path


@click.command()
@click.argument("histogram_json", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path(), help="Output plot path")
@click.option("--title", "-t", help="Plot title")
@click.option("--xlabel", "-x", help="X-axis label")
@click.option("--ylabel", "-y", default="Events", help="Y-axis label")
@click.option("--log-y", is_flag=True, help="Log scale Y axis")
@click.option(
    "--style",
    default="default",
    type=click.Choice(["default", "publication", "presentation"]),
    help="Plot style",
)
@click.pass_context
def plot1d(ctx, histogram_json, output, title, xlabel, ylabel, log_y, style):
    """Plot 1D histogram from JSON file."""
    from root_mcp.extended.tools.plotting import PlottingTools

    # Load histogram data
    with open(histogram_json, "r") as f:
        hist_data = json.load(f)

    config = ctx.obj["config"]
    plotting = PlottingTools(
        config, ctx.obj["file_manager"], ctx.obj["path_validator"], ctx.obj["histogram_ops"]
    )

    # Extract data for plotting
    data = hist_data.get("data", hist_data)

    result = plotting.plot_histogram_1d(
        data=data,
        output_path=str(output),
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        log_y=log_y,
        style=style,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Plot created: {output}")
        click.echo(f"Source: {histogram_json}")
        if title:
            click.echo(f"Title: {title}")

        # Show statistics
        stats = result.get("data", {}).get("statistics", {})
        if stats:
            click.echo("\nStatistics:")
            for key, value in stats.items():
                click.echo(f"  {key}: {value}")


@click.command()
@click.argument("histogram2d_json", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, type=click.Path(), help="Output plot path")
@click.option("--title", "-t", help="Plot title")
@click.option("--xlabel", "-x", help="X-axis label")
@click.option("--ylabel", "-y", help="Y-axis label")
@click.option("--colormap", default="viridis", help="Matplotlib colormap")
@click.option("--log-z", is_flag=True, help="Log scale color")
@click.option(
    "--style",
    default="default",
    type=click.Choice(["default", "publication", "presentation"]),
    help="Plot style",
)
@click.pass_context
def plot2d(ctx, histogram2d_json, output, title, xlabel, ylabel, colormap, log_z, style):
    """Plot 2D histogram from JSON file."""
    from root_mcp.extended.tools.plotting import PlottingTools

    # Load 2D histogram data
    with open(histogram2d_json, "r") as f:
        hist_data = json.load(f)

    config = ctx.obj["config"]
    plotting = PlottingTools(
        config, ctx.obj["file_manager"], ctx.obj["path_validator"], ctx.obj["histogram_ops"]
    )

    # Extract data for plotting
    data = hist_data.get("data", hist_data)

    result = plotting.plot_histogram_2d(
        data=data,
        output_path=str(output),
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        colormap=colormap,
        log_z=log_z,
        style=style,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"2D Plot created: {output}")
        click.echo(f"Source: {histogram2d_json}")
        if title:
            click.echo(f"Title: {title}")
        click.echo(f"Colormap: {colormap}")


@click.command()
@click.argument(
    "operation", type=click.Choice(["add", "subtract", "multiply", "divide", "asymmetry"])
)
@click.argument("hist1_json", type=click.Path(exists=True))
@click.argument("hist2_json", type=click.Path(exists=True))
@click.option("-o", "--output", help="Save result to JSON file")
@click.pass_context
def hist_arithmetic(ctx, operation, hist1_json, hist2_json, output):
    """Perform bin-by-bin histogram arithmetic."""
    from root_mcp.extended.tools.analysis import AnalysisTools

    # Load histogram data
    with open(hist1_json, "r") as f:
        hist1_data = json.load(f)
    with open(hist2_json, "r") as f:
        hist2_data = json.load(f)

    config = ctx.obj["config"]
    analysis = AnalysisTools(
        config,
        ctx.obj["file_manager"],
        ctx.obj["path_validator"],
        ctx.obj["analysis_ops"],
        ctx.obj["tree_reader"],
    )

    result = analysis.compute_histogram_arithmetic(
        operation=operation,
        data1=hist1_data.get("data", hist1_data),
        data2=hist2_data.get("data", hist2_data),
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"Histogram {operation}:")
        click.echo(f"  Input 1: {hist1_json}")
        click.echo(f"  Input 2: {hist2_json}")
        click.echo(f"  Entries: {data.get('entries', 0):,}")

        bin_counts = data.get("bin_counts", [])
        if bin_counts:
            import numpy as np

            arr = np.array(bin_counts)
            click.echo(f"  Result range: [{np.min(arr):.3f}, {np.max(arr):.3f}]")
            click.echo(f"  Result mean:  {np.mean(arr):.3f}")

        # Save result
        if output:
            output_file = Path(output)
            output_file.parent.mkdir(exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"\nResult saved: {output}")
        else:
            output_file = Path("/tmp/root_mcp") / f"hist_{operation}.json"
            output_file.parent.mkdir(exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"\nJSON: {output_file}")
