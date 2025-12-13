"""ROOT-MCP Server - Main entry point."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, cast
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from mcp.server.stdio import stdio_server

from root_mcp.config import Config, load_config
from root_mcp.io import FileManager, PathValidator
from root_mcp.io.readers import TreeReader, HistogramReader
from root_mcp.analysis import AnalysisOperations
from root_mcp.tools import DiscoveryTools, DataAccessTools, AnalysisTools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ROOTMCPServer:
    """Main ROOT-MCP server class."""

    def __init__(self, config: Config):
        """
        Initialize ROOT-MCP server.

        Args:
            config: Server configuration
        """
        self.config = config
        self.server = Server(config.server.name)

        # Initialize components
        logger.info("Initializing ROOT-MCP server components...")
        self.file_manager = FileManager(config)
        self.path_validator = PathValidator(config)
        self.tree_reader = TreeReader(config, self.file_manager)
        self.histogram_reader = HistogramReader(config, self.file_manager)
        self.analysis_ops = AnalysisOperations(config, self.file_manager)

        # Initialize tool handlers
        self.discovery_tools = DiscoveryTools(config, self.file_manager, self.path_validator)
        self.data_access_tools = DataAccessTools(
            config, self.file_manager, self.path_validator, self.tree_reader
        )
        self.analysis_tools = AnalysisTools(
            config,
            self.file_manager,
            self.path_validator,
            self.analysis_ops,
            self.tree_reader,
        )

        # Register handlers
        self._register_resources()
        self._register_tools()

        logger.info("ROOT-MCP server initialized successfully")

    def _register_resources(self) -> None:
        """Register MCP resources (file roots)."""

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available ROOT file resources."""
            resources = []
            for resource_config in self.config.resources:
                resources.append(
                    Resource(
                        uri=cast(Any, f"root-mcp://{resource_config.name}"),
                        name=resource_config.name,
                        description=resource_config.description,
                        mimeType="application/x-root",
                    )
                )
            return resources

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        # Discovery tools
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            tools = [
                Tool(
                    name="list_files",
                    description="List ROOT files in a resource. Returns file paths, sizes, and metadata.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "resource": {
                                "type": "string",
                                "description": "Resource ID (optional, uses default if omitted)",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to filter files (e.g., 'run_*.root')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of files to return (default 100)",
                                "default": 100,
                            },
                        },
                    },
                ),
                Tool(
                    name="inspect_file",
                    description="Inspect a ROOT file's structure. Returns trees, histograms, and directories.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path or resource URI",
                            },
                            "include_histograms": {
                                "type": "boolean",
                                "description": "Include histogram metadata",
                                "default": True,
                            },
                            "include_trees": {
                                "type": "boolean",
                                "description": "Include TTree metadata",
                                "default": True,
                            },
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="list_branches",
                    description="List branches in a TTree with type information and optional statistics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "tree": {"type": "string", "description": "Tree name"},
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to filter branches (e.g., 'muon_*')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum branches to return",
                                "default": 100,
                            },
                            "include_stats": {
                                "type": "boolean",
                                "description": "Compute min/max/mean (slower)",
                                "default": False,
                            },
                        },
                        "required": ["path", "tree"],
                    },
                ),
                Tool(
                    name="read_branches",
                    description="Read branch data from a TTree with optional filtering and pagination.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "branches": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of branch names to read",
                            },
                            "selection": {
                                "type": "string",
                                "description": "ROOT-style cut expression (e.g., 'pt > 20 && abs(eta) < 2.4')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum entries to return",
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Number of entries to skip",
                                "default": 0,
                            },
                            "flatten": {
                                "type": "boolean",
                                "description": "Flatten jagged arrays",
                                "default": False,
                            },
                        },
                        "required": ["path", "tree", "branches"],
                    },
                ),
                Tool(
                    name="sample_tree",
                    description="Get a quick sample from a TTree (first N or random N entries).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "size": {
                                "type": "integer",
                                "description": "Sample size",
                                "default": 100,
                            },
                            "method": {
                                "type": "string",
                                "enum": ["first", "random"],
                                "description": "Sampling method",
                                "default": "first",
                            },
                            "branches": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Branches to include (all if omitted)",
                            },
                            "seed": {
                                "type": "integer",
                                "description": "Random seed for reproducibility",
                            },
                        },
                        "required": ["path", "tree"],
                    },
                ),
                Tool(
                    name="get_branch_stats",
                    description="Compute summary statistics (min, max, mean, std) for branches.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "branches": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "selection": {
                                "type": "string",
                                "description": "Optional cut expression",
                            },
                        },
                        "required": ["path", "tree", "branches"],
                    },
                ),
                Tool(
                    name="compute_histogram",
                    description="Compute a 1D histogram with optional selection and weights.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "branch": {"type": "string"},
                            "bins": {"type": "integer"},
                            "range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                                "description": "[min, max] (auto-detected if omitted)",
                            },
                            "selection": {
                                "type": "string",
                                "description": "Cut expression",
                            },
                            "weights": {
                                "type": "string",
                                "description": "Branch name for weights",
                            },
                            "defines": {
                                "type": "object",
                                "description": "Dictionary of derived variable definitions {name: expression}",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                        "required": ["path", "tree", "branch", "bins"],
                    },
                ),
                Tool(
                    name="compute_histogram_2d",
                    description="Compute a 2D histogram for correlation studies.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "x_branch": {"type": "string"},
                            "y_branch": {"type": "string"},
                            "x_bins": {"type": "integer"},
                            "y_bins": {"type": "integer"},
                            "x_range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "y_range": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "selection": {"type": "string"},
                            "defines": {
                                "type": "object",
                                "description": "Dictionary of derived variable definitions {name: expression}",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                        "required": ["path", "tree", "x_branch", "y_branch", "x_bins", "y_bins"],
                    },
                ),
                Tool(
                    name="apply_selection",
                    description="Count how many entries pass a selection without reading data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "selection": {
                                "type": "string",
                                "description": "Cut expression",
                            },
                            "defines": {
                                "type": "object",
                                "description": "Dictionary of derived variable definitions {name: expression}",
                                "additionalProperties": {"type": "string"},
                            },
                        },
                        "required": ["path", "tree", "selection"],
                    },
                ),
                Tool(
                    name="fit_histogram",
                    description="Fit a histogram to a model (gaussian, exponential, polynomial, crystal_ball) or a composite of them.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Histogram data from compute_histogram",
                            },
                            "model": {
                                "description": "Model to fit. Can be a string (single model) or list of models (composite).",
                                "anyOf": [
                                    {
                                        "type": "string",
                                        "enum": [
                                            "gaussian",
                                            "exponential",
                                            "polynomial",
                                            "crystal_ball",
                                        ],
                                        "description": "Single model name",
                                    },
                                    {
                                        "type": "array",
                                        "items": {
                                            "anyOf": [
                                                {"type": "string"},
                                                {
                                                    "type": "object",
                                                    "properties": {
                                                        "model": {"type": "string"},
                                                        "prefix": {"type": "string"},
                                                    },
                                                },
                                            ]
                                        },
                                        "description": "Composite model (list of names or configs)",
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "expr": {"type": "string"},
                                            "params": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                        "required": ["expr", "params"],
                                        "description": "Custom model expression",
                                    },
                                ],
                            },
                            "initial_guess": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Initial guess for parameters",
                            },
                            "bounds": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "minItems": 2,
                                    "maxItems": 2,
                                },
                                "description": "Bounds [min, max] for each parameter",
                            },
                            "fixed_parameters": {
                                "type": "object",
                                "additionalProperties": {"type": "number"},
                                "description": "Map of parameter name or index to fixed value",
                            },
                        },
                        "required": ["data", "model"],
                    },
                ),
                Tool(
                    name="generate_plot",
                    description="Generate a plot (base64 image) from analysis data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "object",
                                "description": "Analysis data (e.g. histogram)",
                            },
                            "plot_type": {
                                "type": "string",
                                "enum": ["histogram"],
                                "default": "histogram",
                            },
                            "fit_data": {
                                "type": "object",
                                "description": "Optional fit results to overlay",
                            },
                            "options": {
                                "type": "object",
                                "description": "Plotting options",
                                "properties": {
                                    "title": {"type": "string"},
                                    "xlabel": {"type": "string"},
                                    "ylabel": {"type": "string"},
                                    "unit": {
                                        "type": "string",
                                        "description": "Unit string for axes (e.g. GeV)",
                                    },
                                    "log_x": {"type": "boolean"},
                                    "log_y": {"type": "boolean"},
                                    "grid": {"type": "boolean"},
                                    "color": {"type": "string"},
                                },
                            },
                        },
                        "required": ["data"],
                    },
                ),
                Tool(
                    name="export_branches",
                    description="Export branch data to JSON, CSV, or Parquet format.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "tree": {"type": "string"},
                            "branches": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "output_path": {"type": "string"},
                            "output_format": {
                                "type": "string",
                                "enum": ["json", "csv", "parquet"],
                            },
                            "selection": {"type": "string"},
                            "limit": {"type": "integer"},
                        },
                        "required": ["path", "tree", "branches", "output_path", "output_format"],
                    },
                ),
            ]
            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            logger.info(f"Tool called: {name} with args: {arguments}")

            # Route to appropriate handler
            result: dict[str, Any] = {}

            try:
                if name == "list_files":
                    result = self.discovery_tools.list_files(**arguments)
                elif name == "inspect_file":
                    result = self.discovery_tools.inspect_file(**arguments)
                elif name == "list_branches":
                    result = self.discovery_tools.list_branches(**arguments)
                elif name == "read_branches":
                    result = self.data_access_tools.read_branches(**arguments)
                elif name == "sample_tree":
                    result = self.data_access_tools.sample_tree(**arguments)
                elif name == "get_branch_stats":
                    result = self.data_access_tools.get_branch_stats(**arguments)
                elif name == "compute_histogram":
                    result = self.analysis_tools.compute_histogram(**arguments)
                elif name == "compute_histogram_2d":
                    result = self.analysis_tools.compute_histogram_2d(**arguments)
                elif name == "apply_selection":
                    result = self.analysis_tools.apply_selection(**arguments)
                elif name == "fit_histogram":
                    result = self.analysis_tools.fit_histogram(**arguments)
                elif name == "generate_plot":
                    result = self.analysis_tools.generate_plot(**arguments)
                elif name == "export_branches":
                    result = self.analysis_tools.export_branches(**arguments)
                else:
                    result = {
                        "error": "unknown_tool",
                        "message": f"Unknown tool: {name}",
                    }
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}", exc_info=True)
                result = {
                    "error": "internal_error",
                    "message": f"Internal error: {e}",
                }

            # Format result as JSON
            import json

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info(f"Starting {self.config.server.name} v{self.config.server.version}")
        logger.info(f"Resources configured: {len(self.config.resources)}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Main entry point."""
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create and run server
    server = ROOTMCPServer(config)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
