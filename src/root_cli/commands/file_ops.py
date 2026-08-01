"""File operations commands for root-cli."""

import json
from pathlib import Path

import click


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@click.command()
@click.argument("pattern", default="*.root")
@click.option("--limit", "-l", default=100, help="Max files to list")
@click.pass_context
def ls(ctx, pattern, limit):
    """List ROOT files in data directory."""
    from root_mcp.core.tools.discovery import DiscoveryTools

    config = ctx.obj["config"]
    discovery = DiscoveryTools(config, ctx.obj["file_manager"], ctx.obj["path_validator"])

    result = discovery.list_files(pattern=pattern, limit=limit)

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    files = result.get("data", {}).get("files", [])

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data_path = config.resources[0].uri.replace("file://", "") if config.resources else "."
        click.echo(f"Found {len(files)} ROOT files in {data_path}:\n")
        if not files:
            click.echo("  (no files found)")
        for f in files:
            size = format_size(f.get("size_bytes", 0))
            click.echo(f"  {Path(f['path']).name:<50} {size:>10}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.option("--no-trees", is_flag=True, help="Skip tree metadata")
@click.option("--no-histograms", is_flag=True, help="Skip histogram metadata")
@click.pass_context
def inspect(ctx, root_file, no_trees, no_histograms):
    """Inspect ROOT file structure."""
    from root_mcp.core.tools.discovery import DiscoveryTools

    config = ctx.obj["config"]
    discovery = DiscoveryTools(config, ctx.obj["file_manager"], ctx.obj["path_validator"])

    result = discovery.inspect_file(
        str(root_file), include_trees=not no_trees, include_histograms=not no_histograms
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"File: {root_file}")
        click.echo(f"Size: {format_size(data.get('size_bytes', 0))}")

        if data.get("trees"):
            click.echo(f"\nTabular Data (TTrees/RNTuples) ({len(data['trees'])}):")
            for tree in data["trees"]:
                click.echo(
                    f"  {tree['name']:<20} {tree.get('entries', 'N/A'):>12,} entries, "
                    f"{tree.get('branches', 0)} branches"
                )

        if data.get("histograms"):
            click.echo(f"\nHistograms ({len(data['histograms'])}):")
            for hist in data["histograms"]:
                click.echo(f"  {hist.get('name', 'unknown')}")

        if data.get("directories"):
            click.echo(f"\nDirectories: {len(data['directories'])}")

        # Save JSON for downstream use
        output_file = Path("/tmp/root_mcp") / f"{Path(root_file).stem}_info.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.option("--pattern", "-p", default="*", help="Glob pattern for branch names")
@click.option("--limit", "-l", default=100, help="Max branches to list")
@click.option("--stats", "-s", is_flag=True, help="Compute statistics (slower)")
@click.pass_context
def branches(ctx, root_file, tree_name, pattern, limit, stats):
    """List branches in a TTree or RNTuple."""
    from root_mcp.core.tools.discovery import DiscoveryTools

    config = ctx.obj["config"]
    discovery = DiscoveryTools(config, ctx.obj["file_manager"], ctx.obj["path_validator"])

    result = discovery.list_branches(
        str(root_file), tree_name, pattern=pattern, limit=limit, include_stats=stats
    )

    if "error" in result:
        click.echo(f"Error: {result.get('message', 'Unknown error')}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"Tree: {tree_name} in {root_file}")
        click.echo(f"Total entries: {data.get('total_entries', 'N/A'):,}")
        click.echo(f"\nBranches ({data.get('matched', 0)}):\n")

        for branch in data.get("branches", [])[:limit]:
            name = branch.get("name", "unknown")
            btype = branch.get("type", "unknown")
            stats_info = ""
            if stats and "stats" in branch:
                s = branch["stats"]
                stats_info = f"  mean={s.get('mean', 'N/A'):.2f}, std={s.get('std', 'N/A'):.2f}"
            click.echo(f"  {name:<30} {btype:<10} {stats_info}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{tree_name}_branches.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx, root_file):
    """Validate ROOT file integrity."""
    from root_mcp.core.io.file_manager import FileManager

    config = ctx.obj["config"]
    file_manager = FileManager(config)

    try:
        file_info = file_manager.get_file_info(Path(root_file))
        trees = file_manager.list_trees(Path(root_file))

        result = {
            "data": {
                "valid": True,
                "readable": True,
                "warnings": [],
                "metadata": {
                    "num_objects": len(trees) + 1,
                    "num_trees": len(trees),
                    "trees": [t["name"] for t in trees],
                    "compression_ratio": file_info.get("compression", 1.0),
                },
            }
        }

        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"File: {root_file}")
            click.echo("Status: ✓ Valid")
            click.echo("Readable: ✓ Yes")
            click.echo(f"Compression: {file_info.get('compression', 'N/A')}")
            click.echo(f"Trees: {len(trees)}")
            for t in trees:
                click.echo(f"  - {t['name']}")
    except Exception as e:  # noqa: BLE001
        result = {"error": "validation_failed", "message": str(e)}
        if ctx.obj.get("json_output"):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Validation failed: {e}", err=True)
            ctx.exit(1)
