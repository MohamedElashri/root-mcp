"""Data access commands for root-cli."""

import json
import click
from pathlib import Path


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("branches", nargs=-1, required=True)
@click.option("--selection", "-s", help="Cut expression (C++ syntax)")
@click.option("--limit", "-l", type=int, help="Max entries to read")
@click.option("--offset", "-o", type=int, default=0, help="Skip first N entries")
@click.option("--flatten", is_flag=True, help="Flatten jagged arrays")
@click.option("--defines", "-d", multiple=True, help="Derived variables (name=expr)")
@click.pass_context
def read(ctx, root_file, tree_name, branches, selection, limit, offset, flatten, defines):
    """Read branch data from TTree."""
    from root_mcp.core.tools.data_access import DataAccessTools

    # Parse defines
    defines_dict = {}
    for item in defines:
        if "=" in item:
            name, expr = item.split("=", 1)
            defines_dict[name.strip()] = expr.strip()

    config = ctx.obj["config"]
    data_access = DataAccessTools(
        config, ctx.obj["file_manager"], ctx.obj["path_validator"], ctx.obj["tree_reader"]
    )

    result = data_access.read_branches(
        str(root_file),
        tree_name,
        list(branches),
        selection=selection,
        limit=limit,
        offset=offset,
        flatten=flatten,
        defines=defines_dict if defines_dict else None,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"Read {data.get('entries', 0)} entries from {tree_name}")
        click.echo(f"Branches: {', '.join(branches)}")
        if selection:
            click.echo(f"Selection: {selection}")

        records = data.get("records", [])
        if records:
            click.echo(f"\nFirst {min(3, len(records))} entries:")
            for i, rec in enumerate(records[:3]):
                click.echo(f"  {i}: {rec}")
            if len(records) > 3:
                click.echo(f"  ... ({len(records) - 3} more)")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{tree_name}_data.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("branches", nargs=-1, required=True)
@click.option("--selection", "-s", help="Cut expression")
@click.pass_context
def stats(ctx, root_file, tree_name, branches, selection):
    """Compute statistics for branches."""
    from root_mcp.core.tools.data_access import DataAccessTools

    config = ctx.obj["config"]
    data_access = DataAccessTools(
        config, ctx.obj["file_manager"], ctx.obj["path_validator"], ctx.obj["tree_reader"]
    )

    result = data_access.get_branch_stats(
        str(root_file), tree_name, list(branches), selection=selection
    )

    if "error" in result:
        click.echo(f"Error: {result.get('message', 'Unknown error')}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        click.echo(f"Statistics for {tree_name} in {root_file}:\n")

        stats_data = result.get("data", {}).get("statistics", {})
        for branch in branches:
            if branch in stats_data:
                s = stats_data[branch]
                click.echo(f"{branch}:")
                click.echo(f"  count:  {s.get('count', 'N/A'):>12,}")
                click.echo(f"  mean:   {s.get('mean', 'N/A'):>12.3f} ± {s.get('std', 0)/2:.3f}")
                click.echo(f"  std:    {s.get('std', 'N/A'):>12.3f}")
                click.echo(f"  range:  [{s.get('min', 'N/A'):.3f}, {s.get('max', 'N/A'):.3f}]")
                click.echo(f"  median: {s.get('median', 'N/A'):>12.3f}")
                if "percentiles" in s:
                    p = s["percentiles"]
                    click.echo(f"  25th:   {p.get('25', 'N/A'):>12.3f}")
                    click.echo(f"  75th:   {p.get('75', 'N/A'):>12.3f}")
                click.echo()

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{tree_name}_stats.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"JSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("branches", nargs=-1, required=True)
@click.option("-o", "--output", required=True, type=click.Path(), help="Output file path")
@click.option(
    "--format",
    "fmt",
    default="csv",
    type=click.Choice(["json", "csv", "parquet"]),
    help="Output format",
)
@click.option("--selection", "-s", help="Cut expression")
@click.option("--limit", "-l", type=int, help="Max entries to export")
@click.pass_context
def export(ctx, root_file, tree_name, branches, output, fmt, selection, limit):
    """Export branch data to file."""
    from root_mcp.core.io.exporters import DataExporter

    config = ctx.obj["config"]
    exporter = DataExporter(config)
    tree_reader = ctx.obj["tree_reader"]

    try:
        # Read data first
        read_result = tree_reader.read_branches(
            path=str(root_file),
            tree_name=tree_name,
            branches=list(branches),
            selection=selection,
            limit=limit,
        )

        # Get the data array
        data = read_result["data"]

        # Export the data
        result = exporter.export(
            data=data,
            output_path=str(output),
            format=fmt,
        )

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
        else:
            data = result.get("data", {})
            click.echo(f"Exported {data.get('entries_exported', 0):,} entries")
            click.echo(f"Format: {fmt}")
            click.echo(f"Output: {output}")
            click.echo(f"File size: {data.get('file_size_bytes', 0):,} bytes")
    except Exception as e:
        click.echo(f"Export failed: {e}", err=True)
        ctx.exit(1)


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.option("--size", default=100, help="Sample size")
@click.option(
    "--method", default="first", type=click.Choice(["first", "random"]), help="Sampling method"
)
@click.option("--branches", "-b", multiple=True, help="Branches to include")
@click.option("--seed", type=int, help="Random seed (for random sampling)")
@click.pass_context
def sample(ctx, root_file, tree_name, size, method, branches, seed):
    """Get a sample from a TTree."""
    from root_mcp.core.tools.data_access import DataAccessTools

    config = ctx.obj["config"]
    data_access = DataAccessTools(
        config, ctx.obj["file_manager"], ctx.obj["path_validator"], ctx.obj["tree_reader"]
    )

    result = data_access.sample_tree(
        str(root_file),
        tree_name,
        size=size,
        method=method,
        branches=list(branches) if branches else None,
        seed=seed,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"Sampled {data.get('entries', 0)} entries from {tree_name}")
        click.echo(f"Method: {method}")

        records = data.get("records", [])
        if records:
            click.echo(f"\nFirst {min(3, len(records))} entries:")
            for i, rec in enumerate(records[:3]):
                click.echo(f"  {i}: {rec}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{tree_name}_sample.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")
