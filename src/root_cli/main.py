#!/usr/bin/env python3
"""
root-cli: Command-line interface for ROOT data analysis

A token-efficient alternative to MCP protocol, using CLI commands + skill files.
"""

import json
import sys
from pathlib import Path

import click

# Import all commands
from root_cli.commands import (
    export,
    fit,
    hist_arithmetic,
    histogram,
    histogram2d,
    inspect,
    invariant_mass,
    ls,
    plot1d,
    plot2d,
    read,
    sample,
    stats,
    validate,
    branches,
    correlation,
)

# Output directory
OUTPUT_DIR = Path("/tmp/root_mcp")
OUTPUT_DIR.mkdir(exist_ok=True)


def get_backend_status():
    """Check if root_mcp backend is available."""
    try:
        from root_mcp.core.io import FileManager  # noqa: F401
        from root_mcp.core.tools.discovery import DiscoveryTools  # noqa: F401

        return True
    except ImportError:
        return False


@click.group()
@click.option(
    "--data-path",
    "-d",
    envvar="ROOT_MCP_DATA_PATH",
    type=click.Path(exists=True),
    help="Base path for ROOT files (or set ROOT_MCP_DATA_PATH env var)",
)
@click.option(
    "--json", "-j", "json_output", is_flag=True, help="Output in JSON format (for programmatic use)"
)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx, data_path, json_output):
    """
    ROOT CLI - Analyze CERN ROOT files from command line

    A token-efficient alternative to MCP server protocol.

    Examples:
      # List available ROOT files
      root-cli ls

      # Inspect a file structure
      root-cli inspect /path/to/file.root

      # Create histogram with fit
      root-cli histogram data.root events muon_pt --bins 100 --fit gaussian

      # Read branches with selection
      root-cli read data.root events met muon_pt --selection "met > 50"

    Set default data path:
      export ROOT_MCP_DATA_PATH=/your/data/dir
    """
    ctx.ensure_object(dict)
    ctx.obj["data_path"] = Path(data_path) if data_path else Path.cwd()
    ctx.obj["json_output"] = json_output

    # Initialize backend components if available
    backend_available = get_backend_status()
    ctx.obj["backend_available"] = backend_available

    if backend_available:
        from root_mcp.config import Config, ResourceConfig
        from root_mcp.core.io import FileManager, TreeReader, PathValidator
        from root_mcp.extended.analysis import AnalysisOperations, HistogramOperations

        # Create a minimal config based on provided data path
        data_path_str = str(data_path) if data_path else str(ctx.obj["data_path"])

        # Create minimal config - no file loading needed
        from root_mcp.config import SecurityConfig

        cfg = Config(
            resources=[
                ResourceConfig(
                    name="local_data",
                    uri=f"file://{data_path_str}",
                    description="Local ROOT files",
                    allowed_patterns=["*.root"],
                )
            ],
            security=SecurityConfig(allowed_roots=[]),  # Permissive mode
        )

        ctx.obj["config"] = cfg
        ctx.obj["file_manager"] = FileManager(cfg)
        ctx.obj["path_validator"] = PathValidator(cfg)
        ctx.obj["tree_reader"] = TreeReader(cfg, ctx.obj["file_manager"])
        ctx.obj["analysis_ops"] = AnalysisOperations(cfg, ctx.obj["file_manager"])
        ctx.obj["histogram_ops"] = HistogramOperations(cfg, ctx.obj["file_manager"])
    else:
        if len(sys.argv) > 1 and sys.argv[1] not in ["--help", "-h", "--version"]:
            click.echo("⚠️  Warning: root_mcp backend not available. Using stub mode.", err=True)


# Register all commands
cli.add_command(ls)
cli.add_command(inspect)
cli.add_command(branches)
cli.add_command(validate)
cli.add_command(read)
cli.add_command(stats)
cli.add_command(export)
cli.add_command(sample)
cli.add_command(histogram)
cli.add_command(histogram2d)
cli.add_command(fit)
cli.add_command(invariant_mass)
cli.add_command(correlation)
cli.add_command(plot1d)
cli.add_command(plot2d)
cli.add_command(hist_arithmetic)


@cli.command()
@click.pass_context
def info(ctx):
    """Show CLI information and available commands."""
    backend_status = (
        "Available" if ctx.obj.get("backend_available") else "Not installed (stub mode)"
    )

    result = {
        "name": "root-cli",
        "version": "0.1.0",
        "backend_available": ctx.obj.get("backend_available", False),
        "backend_status": backend_status,
        "output_directory": str(OUTPUT_DIR),
        "data_path": str(ctx.obj.get("data_path", ".")),
        "commands": [
            "ls",
            "inspect",
            "branches",
            "validate",
            "read",
            "stats",
            "export",
            "sample",
            "histogram",
            "histogram2d",
            "fit",
            "invariant-mass",
            "correlation",
            "plot1d",
            "plot2d",
            "hist-arithmetic",
            "info",
        ],
    }

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("ROOT CLI v0.1.0")
        click.echo(f"Data path: {ctx.obj.get('data_path', '.')}")
        click.echo(f"Output directory: {OUTPUT_DIR}")
        click.echo(f"Backend: {backend_status}")
        click.echo(f"\nAvailable commands ({len(result['commands'])}):")
        for cmd in result["commands"]:
            click.echo(f"  - {cmd}")
        click.echo("\nUse 'root-cli <command> --help' for command-specific help.")
        click.echo("\nDocumentation: docs/skills/root-cli.md")


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
