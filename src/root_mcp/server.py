"""ROOT-MCP Server - Mode-aware implementation with lazy loading."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any, cast
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from mcp.server.stdio import stdio_server

from root_mcp.config import Config, load_config
from root_mcp.core.io import FileManager, PathValidator, TreeReader, HistogramReader, DataExporter
from root_mcp.core.operations import BasicStatistics
from root_mcp.core.tools import DiscoveryTools, DataAccessTools

# Setup logging - must use stderr to avoid interfering with stdio MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class ROOTMCPServer:
    """Mode-aware ROOT-MCP server with lazy loading."""

    def __init__(self, config: Config):
        """
        Initialize ROOT-MCP server in specified mode.

        Args:
            config: Server configuration
        """
        self.config = config
        self.server = Server(config.server.name)
        self.current_mode = config.server.mode

        # Initialize core components (always available)
        logger.info(f"Initializing ROOT-MCP server in {self.current_mode} mode...")
        self._initialize_core_components()

        # Initialize extended components if in extended mode
        self._extended_components_loaded = False
        if self.current_mode == "extended":
            self._initialize_extended_components()

        # Register handlers
        self._register_resources()
        self._register_tools()

        logger.info(f"ROOT-MCP server initialized successfully in {self.current_mode} mode")

    def _initialize_core_components(self) -> None:
        """Initialize core components (always available)."""
        self.file_manager = FileManager(self.config)
        self.path_validator = PathValidator(self.config)
        self.tree_reader = TreeReader(self.config, self.file_manager)
        self.histogram_reader = HistogramReader(self.config, self.file_manager)
        self.data_exporter = DataExporter(self.config)
        self.basic_stats = BasicStatistics(self.config, self.file_manager)

        # Core tool handlers
        self.discovery_tools = DiscoveryTools(self.config, self.file_manager, self.path_validator)
        self.data_access_tools = DataAccessTools(
            config=self.config,
            file_manager=self.file_manager,
            path_validator=self.path_validator,
            tree_reader=self.tree_reader,
        )

        logger.info("Core components initialized")

    def _initialize_extended_components(self) -> None:
        """Initialize extended analysis components (lazy loaded)."""
        if self._extended_components_loaded:
            return

        try:
            # Import extended modules
            from root_mcp.extended.analysis import (
                AnalysisOperations,
                HistogramOperations,
                KinematicsOperations,
                CorrelationAnalysis,
            )
            from root_mcp.extended.tools import AnalysisTools, PlottingTools

            # Initialize extended components
            self.analysis_ops = AnalysisOperations(self.config, self.file_manager)
            self.histogram_ops = HistogramOperations(self.config, self.file_manager)
            self.kinematics_ops = KinematicsOperations(self.config, self.file_manager)
            self.correlation_analysis = CorrelationAnalysis(self.config, self.file_manager)

            # Extended tool handlers
            self.analysis_tools = AnalysisTools(
                config=self.config,
                file_manager=self.file_manager,
                path_validator=self.path_validator,
                analysis_ops=self.analysis_ops,
                tree_reader=self.tree_reader,
            )

            self.plotting_tools = PlottingTools(
                config=self.config,
                file_manager=self.file_manager,
                path_validator=self.path_validator,
                histogram_ops=self.histogram_ops,
            )

            self._extended_components_loaded = True
            logger.info("Extended components initialized")

        except ImportError as e:
            logger.error(f"Failed to load extended components: {e}")
            logger.warning(
                "Extended mode requires scipy and matplotlib. Falling back to core mode."
            )
            self.current_mode = "core"
            self._extended_components_loaded = False

    def _unload_extended_components(self) -> None:
        """Unload extended components to free memory."""
        if not self._extended_components_loaded:
            return

        # Remove references to extended components
        if hasattr(self, "analysis_ops"):
            del self.analysis_ops
        if hasattr(self, "histogram_ops"):
            del self.histogram_ops
        if hasattr(self, "kinematics_ops"):
            del self.kinematics_ops
        if hasattr(self, "correlation_analysis"):
            del self.correlation_analysis
        if hasattr(self, "analysis_tools"):
            del self.analysis_tools

        self._extended_components_loaded = False
        logger.info("Extended components unloaded")

    def switch_mode(self, new_mode: str) -> dict[str, Any]:
        """
        Switch between core and extended modes at runtime.

        Args:
            new_mode: Target mode ('core' or 'extended')

        Returns:
            Status dictionary
        """
        if new_mode not in ["core", "extended"]:
            raise ValueError(f"Invalid mode: {new_mode}. Must be 'core' or 'extended'")

        if new_mode == self.current_mode:
            return {
                "status": "no_change",
                "current_mode": self.current_mode,
                "message": f"Already in {new_mode} mode",
            }

        old_mode = self.current_mode

        if new_mode == "extended":
            # Switch to extended mode
            try:
                self._initialize_extended_components()
                self.current_mode = "extended"
                self.config.server.mode = "extended"

                return {
                    "status": "success",
                    "previous_mode": old_mode,
                    "current_mode": self.current_mode,
                    "message": f"Switched from {old_mode} to {new_mode} mode",
                    "extended_features_available": True,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "current_mode": self.current_mode,
                    "message": f"Failed to switch to extended mode: {e}",
                }

        else:  # new_mode == "core"
            # Switch to core mode
            self._unload_extended_components()
            self.current_mode = "core"
            self.config.server.mode = "core"

            return {
                "status": "success",
                "previous_mode": old_mode,
                "current_mode": self.current_mode,
                "message": f"Switched from {old_mode} to {new_mode} mode",
                "extended_features_available": False,
            }

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

    def _get_core_tools(self) -> list[Tool]:
        """Get core mode tools."""
        return [
            # Discovery tools
            Tool(
                name="list_files",
                description="List ROOT files in a resource",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource": {"type": "string", "description": "Resource name"},
                        "pattern": {"type": "string", "description": "Optional glob pattern"},
                    },
                    "required": ["resource"],
                },
            ),
            Tool(
                name="inspect_file",
                description="Inspect ROOT file structure and contents",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="list_branches",
                description="List branches in a TTree",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "tree_name": {"type": "string", "description": "Tree name"},
                        "pattern": {"type": "string", "description": "Optional glob pattern"},
                    },
                    "required": ["path", "tree_name"],
                },
            ),
            Tool(
                name="validate_file",
                description="Validate ROOT file integrity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            ),
            # Data access tools
            Tool(
                name="read_branches",
                description="Read branch data from a TTree",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "tree_name": {"type": "string", "description": "Tree name"},
                        "branches": {"type": "array", "items": {"type": "string"}},
                        "entry_start": {"type": "integer", "description": "Start entry"},
                        "entry_stop": {"type": "integer", "description": "Stop entry"},
                        "selection": {"type": "string", "description": "Optional cut expression"},
                    },
                    "required": ["path", "tree_name", "branches"],
                },
            ),
            Tool(
                name="get_branch_stats",
                description="Get statistics for branches (supports derived variables via defines)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "tree_name": {"type": "string", "description": "Tree name"},
                        "branches": {"type": "array", "items": {"type": "string"}},
                        "selection": {"type": "string", "description": "Optional cut expression"},
                        "defines": {
                            "type": "object",
                            "description": "Derived variable definitions (dict of name: expression)",
                        },
                    },
                    "required": ["path", "tree_name", "branches"],
                },
            ),
            Tool(
                name="export_data",
                description="Export branch data to JSON, CSV, or Parquet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "tree_name": {"type": "string", "description": "Tree name"},
                        "branches": {"type": "array", "items": {"type": "string"}},
                        "output_path": {"type": "string", "description": "Output file path"},
                        "format": {"type": "string", "enum": ["json", "csv", "parquet"]},
                        "selection": {"type": "string", "description": "Optional cut expression"},
                        "compress": {"type": "boolean", "description": "Compress output"},
                    },
                    "required": ["path", "tree_name", "branches", "output_path", "format"],
                },
            ),
            # Mode switching
            Tool(
                name="switch_mode",
                description="Switch between core and extended modes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["core", "extended"]},
                    },
                    "required": ["mode"],
                },
            ),
            Tool(
                name="get_server_info",
                description="Get server mode and capabilities",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    def _get_extended_tools(self) -> list[Tool]:
        """Get extended mode tools (in addition to core tools)."""
        return [
            Tool(
                name="compute_histogram",
                description="Compute 1D histogram with fitting support",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "anyOf": [
                                {"type": "string", "description": "File path"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of file paths",
                                },
                            ]
                        },
                        "tree_name": {"type": "string"},
                        "branch": {"type": "string"},
                        "bins": {"type": "integer"},
                        "range": {"type": "array", "items": {"type": "number"}},
                        "selection": {"type": "string"},
                        "weights": {"type": "string"},
                    },
                    "required": ["path", "tree_name", "branch", "bins"],
                },
            ),
            Tool(
                name="compute_histogram_2d",
                description="Compute 2D histogram (supports derived variables via defines)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "anyOf": [
                                {"type": "string", "description": "File path"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of file paths",
                                },
                            ]
                        },
                        "tree_name": {"type": "string", "description": "Tree name"},
                        "x_branch": {"type": "string", "description": "X-axis branch"},
                        "y_branch": {"type": "string", "description": "Y-axis branch"},
                        "x_bins": {"type": "integer", "description": "Number of bins in X"},
                        "y_bins": {"type": "integer", "description": "Number of bins in Y"},
                        "x_range": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "X-axis range [min, max]",
                        },
                        "y_range": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "Y-axis range [min, max]",
                        },
                        "selection": {"type": "string", "description": "Optional cut expression"},
                        "defines": {
                            "type": "object",
                            "description": "Derived variable definitions (dict of name: expression)",
                        },
                    },
                    "required": ["path", "tree_name", "x_branch", "y_branch", "x_bins", "y_bins"],
                },
            ),
            Tool(
                name="fit_histogram",
                description="Fit histogram with model function",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "tree_name": {"type": "string"},
                        "branch": {"type": "string"},
                        "bins": {"type": "integer"},
                        "model": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}},
                                {"type": "array", "items": {"type": "object"}},
                                {"type": "object"},
                            ]
                        },
                        "range": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "selection": {"type": "string"},
                        "weights": {"type": "string"},
                        "defines": {
                            "type": "object",
                            "description": "Derived variable definitions",
                        },
                        "initial_guess": {"type": "array", "items": {"type": "number"}},
                        "bounds": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                        "fixed_parameters": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "required": ["path", "tree_name", "branch", "bins", "model"],
                },
            ),
            Tool(
                name="compute_invariant_mass",
                description="Compute invariant mass from 4-vectors",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "tree_name": {"type": "string"},
                        "pt_branches": {"type": "array", "items": {"type": "string"}},
                        "eta_branches": {"type": "array", "items": {"type": "string"}},
                        "phi_branches": {"type": "array", "items": {"type": "string"}},
                        "mass_branches": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "path",
                        "tree_name",
                        "pt_branches",
                        "eta_branches",
                        "phi_branches",
                    ],
                },
            ),
            Tool(
                name="compute_correlation",
                description="Compute correlation between branches",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "tree_name": {"type": "string"},
                        "branch_x": {"type": "string"},
                        "branch_y": {"type": "string"},
                        "method": {"type": "string", "enum": ["pearson", "spearman"]},
                    },
                    "required": ["path", "tree_name", "branch_x", "branch_y"],
                },
            ),
            Tool(
                name="plot_histogram_1d",
                description="Create and save a 1D histogram plot. Provide EITHER 'data' (pre-calculated) OR 'path', 'tree_name', 'branch', 'bins' (compute from file).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Pre-calculated histogram data (bin_counts, bin_edges, etc.)",
                        },
                        "path": {
                            "type": "string",
                            "description": "File path (required if data not provided)",
                        },
                        "tree_name": {
                            "type": "string",
                            "description": "Tree name (required if data not provided)",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to histogram (required if data not provided)",
                        },
                        "bins": {
                            "type": "integer",
                            "description": "Number of bins (required if data not provided)",
                        },
                        "range": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Histogram range [min, max]",
                        },
                        "selection": {"type": "string", "description": "Optional cut expression"},
                        "weights": {"type": "string", "description": "Optional weight branch"},
                        "defines": {
                            "type": "object",
                            "description": "Derived variable definitions (dict of name: expression)",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path (e.g., /tmp/plot.png)",
                        },
                        "title": {"type": "string", "description": "Plot title"},
                        "xlabel": {"type": "string", "description": "X-axis label"},
                        "ylabel": {"type": "string", "description": "Y-axis label"},
                        "log_y": {"type": "boolean", "description": "Use log scale for y-axis"},
                        "style": {
                            "type": "string",
                            "enum": ["default", "publication", "presentation"],
                            "description": "Plot style",
                        },
                    },
                    "required": ["output_path"],
                },
            ),
            Tool(
                name="plot_histogram_2d",
                description="Create and save a 2D histogram plot. Provide EITHER 'data' (pre-calculated) OR 'path', 'tree_name', 'branch_x'...' (compute from file).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Pre-calculated histogram data (bin_counts, x_edges, y_edges, etc.)",
                        },
                        "path": {
                            "type": "string",
                            "description": "File path (required if data not provided)",
                        },
                        "tree_name": {
                            "type": "string",
                            "description": "Tree name (required if data not provided)",
                        },
                        "branch_x": {
                            "type": "string",
                            "description": "X-axis branch (required if data not provided)",
                        },
                        "branch_y": {
                            "type": "string",
                            "description": "Y-axis branch (required if data not provided)",
                        },
                        "bins_x": {
                            "type": "integer",
                            "description": "Number of bins in X (required if data not provided)",
                        },
                        "bins_y": {
                            "type": "integer",
                            "description": "Number of bins in Y (required if data not provided)",
                        },
                        "range_x": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "X-axis range [min, max]",
                        },
                        "range_y": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Y-axis range [min, max]",
                        },
                        "selection": {"type": "string", "description": "Optional cut expression"},
                        "weights": {"type": "string", "description": "Optional weight branch"},
                        "defines": {
                            "type": "object",
                            "description": "Derived variable definitions (dict of name: expression)",
                        },
                        "output_path": {"type": "string", "description": "Output file path"},
                        "title": {"type": "string", "description": "Plot title"},
                        "xlabel": {"type": "string", "description": "X-axis label"},
                        "ylabel": {"type": "string", "description": "Y-axis label"},
                        "colormap": {"type": "string", "description": "Matplotlib colormap name"},
                        "log_z": {"type": "boolean", "description": "Use log scale for color"},
                        "style": {
                            "type": "string",
                            "enum": ["default", "publication", "presentation"],
                        },
                    },
                    "required": ["output_path"],
                },
            ),
            Tool(
                name="histogram_arithmetic",
                description="Perform bin-by-bin arithmetic on two histograms (e.g. asymmetry, difference, ratio)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide", "asymmetry"],
                            "description": "Operation to perform: data1 [op] data2. Asymmetry is (d1-d2)/(d1+d2).",
                        },
                        "data1": {
                            "type": "object",
                            "description": "First histogram data (result from compute_histogram)",
                        },
                        "data2": {
                            "type": "object",
                            "description": "Second histogram data",
                        },
                    },
                    "required": ["operation", "data1", "data2"],
                },
            ),
        ]

    def _register_tools(self) -> None:
        """Register all MCP tools based on current mode."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools based on current mode."""
            tools = self._get_core_tools()

            if self.current_mode == "extended" and self._extended_components_loaded:
                tools.extend(self._get_extended_tools())

            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with mode awareness."""
            import json

            try:
                # Mode management tools
                if name == "switch_mode":
                    result = self.switch_mode(arguments["mode"])
                elif name == "get_server_info":
                    result = {
                        "server_name": self.config.server.name,
                        "version": self.config.server.version,
                        "current_mode": self.current_mode,
                        "extended_components_loaded": self._extended_components_loaded,
                        "available_modes": ["core", "extended"],
                    }

                # Core tools (always available)
                elif name == "list_files":
                    result = self.discovery_tools.list_files(**arguments)
                elif name == "inspect_file":
                    result = self.discovery_tools.inspect_file(**arguments)
                elif name == "list_branches":
                    result = self.discovery_tools.list_branches(**arguments)
                elif name == "validate_file":
                    result = self.file_manager.validate_file(arguments["path"])
                elif name == "read_branches":
                    result = self.data_access_tools.read_branches(**arguments)
                elif name == "get_branch_stats":
                    # Handle defines parameter if passed as JSON string
                    defines = arguments.get("defines")
                    if defines is not None and isinstance(defines, str):
                        import json

                        try:
                            defines = json.loads(defines)
                        except json.JSONDecodeError:
                            result = {
                                "error": "invalid_parameter",
                                "message": "Invalid JSON in defines parameter",
                            }
                            return [TextContent(type="text", text=json.dumps(result, indent=2))]

                    result = self.basic_stats.compute_stats(
                        arguments["path"],
                        arguments["tree_name"],
                        arguments["branches"],
                        arguments.get("selection"),
                        defines,
                    )
                elif name == "export_data":
                    # Read data directly for export
                    tree = self.file_manager.get_tree(arguments["path"], arguments["tree_name"])
                    arrays = tree.arrays(
                        filter_name=arguments["branches"],
                        cut=arguments.get("selection"),
                        library="ak",
                    )
                    # Export
                    result = self.data_exporter.export(
                        arrays,
                        arguments["output_path"],
                        arguments["format"],
                        compress=arguments.get("compress", False),
                    )

                # Extended tools (only in extended mode)
                elif name in [
                    "compute_histogram",
                    "compute_histogram_2d",
                    "fit_histogram",
                    "compute_invariant_mass",
                    "compute_correlation",
                    "plot_histogram_1d",
                    "plot_histogram_2d",
                    "histogram_arithmetic",
                ]:
                    if self.current_mode != "extended" or not self._extended_components_loaded:
                        result = {
                            "error": "mode_error",
                            "message": f"Tool '{name}' requires extended mode. Current mode: {self.current_mode}",
                            "hint": "Use switch_mode tool to enable extended mode",
                        }
                    else:
                        # Delegate to appropriate handler
                        if name == "compute_histogram":
                            result = self.analysis_tools.compute_histogram(**arguments)
                        elif name == "compute_histogram_2d":
                            result = self.analysis_tools.compute_histogram_2d(**arguments)
                        elif name == "fit_histogram":
                            result = self.analysis_tools.fit_histogram(**arguments)
                        elif name == "compute_invariant_mass":
                            result = self.kinematics_ops.compute_invariant_mass(**arguments)
                        elif name == "compute_correlation":
                            result = self.correlation_analysis.compute_correlation(**arguments)
                        elif name == "plot_histogram_1d":
                            result = self.plotting_tools.plot_histogram_1d(**arguments)
                        elif name == "plot_histogram_2d":
                            result = self.plotting_tools.plot_histogram_2d(**arguments)
                        elif name == "histogram_arithmetic":
                            result = self.analysis_tools.compute_histogram_arithmetic(**arguments)

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

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info(f"Starting {self.config.server.name} v{self.config.server.version}")
        logger.info(f"Mode: {self.current_mode}")
        logger.info(f"Resources configured: {len(self.config.resources)}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ROOT-MCP Server")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (overrides ROOT_MCP_CONFIG env var)",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

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
