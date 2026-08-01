"""ROOT-MCP Server - Mode-aware implementation with lazy loading."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

from root_mcp.common.root_availability import get_root_features, get_root_version, is_root_available
from root_mcp.config import (
    _CONFIG_TEMPLATE,
    Config,
    apply_env_overrides,
    load_config,
    validate_deployment_config,
)
from root_mcp.core.io.retention import cleanup_exports
from root_mcp.observability import MetricsRegistry
from root_mcp.security import (
    AuditLogger,
    PolicyDenied,
    PolicyEngine,
    QuotaExceeded,
    QuotaManager,
    RequestContext,
    ResourceAccessDenied,
    ResourceResolver,
    build_audit_event,
    exported_bytes,
)
from root_mcp.transport import HTTPStartupError, run_http, run_stdio

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
        validate_deployment_config(config)
        self.config = config
        self.server = Server(config.server.name)
        self.current_mode = config.server.mode
        self.policy_engine = PolicyEngine(config)
        self.quota_manager = QuotaManager(config)
        self.metrics = MetricsRegistry()
        self.audit_logger = AuditLogger(config.audit)

        # Initialize core components (always available)
        logger.info(f"Initializing ROOT-MCP server in {self.current_mode} mode...")
        self._initialize_core_components()

        # Initialize extended components if in extended mode
        self._extended_components_loaded = False
        self._root_native_available = False
        if self.current_mode == "extended":
            self._initialize_extended_components()

        # Register handlers
        self._register_resources()
        self._register_tools()

        logger.info(f"ROOT-MCP server initialized successfully in {self.current_mode} mode")

    def _create_request_context(self) -> RequestContext:
        """Create a request context for the current MCP request."""
        try:
            mcp_request = self.server.request_context.request
            http_ctx = getattr(getattr(mcp_request, "state", None), "root_mcp_context", None)
            if isinstance(http_ctx, RequestContext):
                return http_ctx
        except LookupError:
            pass
        except AttributeError:
            pass

        return RequestContext(
            deployment_profile=self.config.deployment.profile,
            transport=self.config.deployment.transport,
            request_id=str(uuid4()),
        )

    def _debug_errors_enabled(self) -> bool:
        """Return whether client errors may include internal details."""
        return logger.isEnabledFor(logging.DEBUG)

    def _initialize_core_components(self) -> None:
        """Initialize core components (always available)."""
        from root_mcp.core.io import (
            DataExporter,
            FileManager,
            HistogramReader,
            PathValidator,
            TreeReader,
        )
        from root_mcp.core.operations import BasicStatistics
        from root_mcp.core.tools import DataAccessTools, DiscoveryTools

        self.file_manager = FileManager(self.config)
        self.path_validator = PathValidator(self.config)
        self.resource_resolver = ResourceResolver(self.config, self.path_validator)
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
                CorrelationAnalysis,
                HistogramOperations,
                KinematicsOperations,
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

            # Initialize native ROOT tools if enabled and available
            self._initialize_root_native()

        except ImportError as e:
            logger.error(f"Failed to load extended components: {e}")
            logger.warning(
                "Extended mode requires scipy and matplotlib. Falling back to core mode."
            )
            self.current_mode = "core"
            self._extended_components_loaded = False

    def _initialize_root_native(self) -> None:
        """Initialize native ROOT tools if enabled and available."""
        if not self.config.features.enable_root:
            logger.info("Native ROOT support disabled (enable_root=false)")
            self._root_native_available = False
            return

        if self.config.root_native.execution_backend == "disabled":
            logger.info("Native ROOT support disabled (execution_backend=disabled)")
            self._root_native_available = False
            return

        if not is_root_available():
            logger.info("Native ROOT support enabled but ROOT not found in environment")
            self._root_native_available = False
            return

        try:
            from root_mcp.extended.tools.root_native import RootNativeTools

            self.root_native_tools = RootNativeTools(config=self.config)
            self._root_native_available = True
            logger.info(
                "Native ROOT tools initialized (ROOT %s)",
                get_root_version() or "unknown version",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to initialize native ROOT tools: %s", e)
            self._root_native_available = False

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
        if hasattr(self, "root_native_tools"):
            del self.root_native_tools

        self._extended_components_loaded = False
        self._root_native_available = False
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
            except Exception as e:  # noqa: BLE001
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
                description="List branches in a TTree or RNTuple",
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
                description="Read branch data from a TTree or RNTuple",
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

    def _get_root_native_tools(self) -> list[Tool]:
        """Get native ROOT tools (only when ROOT is enabled and available)."""
        return [
            Tool(
                name="run_root_code",
                description=(
                    "Execute PyROOT/Python code with native ROOT. "
                    "Use for operations not possible with uproot: RDataFrame, RooFit, "
                    "custom classes, TCanvas plots, C++ interop, etc. "
                    "IMPORTANT: Always start code with 'import ROOT' and "
                    "'ROOT.gROOT.SetBatch(True)' (prevents GUI). "
                    "The variable '_output_dir' is available in code as a writable "
                    "directory for saving files (plots, ROOT files). "
                    "The variable '_input_files' contains the list of input file paths. "
                    "To return structured data, call '_set_result(value)' where value "
                    "is a JSON-serializable object, or print JSON to stdout. "
                    "Prefer run_rdataframe for simple histograms."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": (
                                "Python code to execute. Must import ROOT explicitly. "
                                "Use ROOT.gROOT.SetBatch(True) to prevent GUI. "
                                "Use _output_dir for file output, _set_result() for structured results."
                            ),
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for output files (optional, defaults to temp dir)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": (
                                "Execution timeout in seconds (default: 60). "
                                "Increase for large files or complex fits."
                            ),
                        },
                        "input_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Paths to ROOT files the code needs. "
                                "Available inside code as _input_files list."
                            ),
                        },
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="run_rdataframe",
                description=(
                    "Compute a 1D histogram using ROOT RDataFrame. "
                    "Only supports 1D histograms of a single branch. "
                    "For 2D histograms, profiles, Define() columns, or other RDataFrame "
                    "operations, use run_root_code instead. "
                    "Preferred over run_root_code for simple 1D histograms — no boilerplate needed. "
                    "Returns JSON with entries, mean, std_dev, bin_contents, bin_errors, bin_edges. "
                    "Use inspect_file first to discover tree and branch names. "
                    "Selection uses C++ syntax (e.g. 'pt > 20 && abs(eta) < 2.5'). "
                    "Requires native ROOT."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the ROOT file",
                        },
                        "tree_name": {
                            "type": "string",
                            "description": "Name of the TTree or RNTuple",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to histogram",
                        },
                        "bins": {
                            "type": "integer",
                            "description": "Number of bins",
                        },
                        "range_min": {
                            "type": "number",
                            "description": "Histogram range minimum",
                        },
                        "range_max": {
                            "type": "number",
                            "description": "Histogram range maximum",
                        },
                        "selection": {
                            "type": "string",
                            "description": "Optional cut expression (C++ syntax for RDF Filter)",
                        },
                        "weight": {
                            "type": "string",
                            "description": "Optional weight column name",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Save histogram plot to this path (png, pdf, svg)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                        },
                    },
                    "required": [
                        "file_path",
                        "tree_name",
                        "branch",
                        "bins",
                        "range_min",
                        "range_max",
                    ],
                },
            ),
            Tool(
                name="run_root_macro",
                description=(
                    "Execute a ROOT C++ macro via gROOT.ProcessLine. "
                    'Use for short C++ snippets (e.g. \'TH1F h("h","h",100,-5,5); '
                    'h.FillRandom("gaus",10000);\'). Multi-line code is supported. '
                    "For complex analysis, prefer run_root_code with Python. "
                    "Requires native ROOT."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "macro_code": {
                            "type": "string",
                            "description": "C++ code to execute",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Save any canvas output to this path (optional)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds",
                        },
                    },
                    "required": ["macro_code"],
                },
            ),
        ]

    def _get_unfiltered_tools(self) -> list[Tool]:
        """Build the full tool list for the current analysis tier."""
        tools = self._get_core_tools()

        if self.current_mode == "extended" and self._extended_components_loaded:
            tools.extend(self._get_extended_tools())

        if self._root_native_available:
            tools.extend(self._get_root_native_tools())

        return tools

    def list_available_tools(self, ctx: RequestContext | None = None) -> list[Tool]:
        """List tools visible to the request context after policy filtering."""
        request_ctx = ctx or self._create_request_context()
        return self.policy_engine.filter_tools(request_ctx, self._get_unfiltered_tools())

    async def handle_tool_call(
        self,
        name: str,
        arguments: dict[str, Any] | None,
        ctx: RequestContext | None = None,
    ) -> list[TextContent]:
        """Handle a tool call after applying request policy."""
        import json

        request_ctx = ctx or self._create_request_context()
        arguments = arguments or {}
        started = perf_counter()
        policy_decision = "unknown"
        status = "error"
        result: dict[str, Any] | None = None

        try:
            decision = self.policy_engine.authorize_tool_call(request_ctx, name, arguments)
            policy_decision = decision.code
            export_decision = self.policy_engine.require_export_permission(
                request_ctx,
                name,
                arguments,
            )
            if export_decision.code != "allowed":
                policy_decision = export_decision.code
            logger.info(
                "Policy allowed tool call request_id=%s profile=%s principal=%s tool=%s",
                request_ctx.request_id,
                request_ctx.deployment_profile,
                request_ctx.principal_id,
                name,
            )
            self.metrics.increment("allowed_calls")
            async with self.quota_manager.reserve(request_ctx, name, arguments):
                with self.metrics.running_call():
                    if request_ctx.deployment_profile == "central":
                        result = await self._dispatch_tool_with_timeout(
                            name,
                            arguments,
                            request_ctx,
                        )
                    else:
                        with self.file_manager.request_context(request_ctx):
                            result = self._dispatch_tool(name, arguments, request_ctx)
                exported_size = exported_bytes(result)
                self.metrics.add_exported_bytes(exported_size)
                self.quota_manager.validate_result(result)
            status = "error" if isinstance(result, dict) and "error" in result else "success"
            if status == "error":
                self.metrics.increment("failed_calls")
        except PolicyDenied as e:
            policy_decision = e.decision.code
            status = "denied"
            self.metrics.increment("denied_calls")
            logger.warning(
                "Policy denied tool call request_id=%s profile=%s principal=%s tool=%s reason=%s",
                request_ctx.request_id,
                request_ctx.deployment_profile,
                request_ctx.principal_id,
                name,
                e.decision.code,
            )
            result = e.to_error(request_ctx.request_id, debug=self._debug_errors_enabled())
        except QuotaExceeded as e:
            policy_decision = e.code
            status = "denied"
            self.metrics.increment("denied_calls")
            logger.warning(
                "Quota denied tool call request_id=%s profile=%s principal=%s tool=%s reason=%s",
                request_ctx.request_id,
                request_ctx.deployment_profile,
                request_ctx.principal_id,
                name,
                e.code,
            )
            result = e.to_error(request_ctx.request_id)
        except (asyncio.TimeoutError, TimeoutError):
            policy_decision = "request_timeout"
            status = "timeout"
            self.metrics.increment("timeout_count")
            logger.warning(
                "Tool call timed out request_id=%s profile=%s principal=%s tool=%s",
                request_ctx.request_id,
                request_ctx.deployment_profile,
                request_ctx.principal_id,
                name,
            )
            result = {
                "error": "quota_exceeded",
                "message": "Tool call exceeded configured timeout",
                "request_id": request_ctx.request_id,
                "reason": "request_timeout",
            }
        except Exception as e:
            policy_decision = "allowed"
            status = "error"
            self.metrics.increment("failed_calls")
            logger.exception("Tool %s failed", name)
            if request_ctx.deployment_profile == "central" and not self._debug_errors_enabled():
                result = {
                    "error": "internal_error",
                    "message": "Internal server error",
                    "request_id": request_ctx.request_id,
                }
            else:
                result = {
                    "error": "internal_error",
                    "message": f"Internal error: {e}",
                    "request_id": request_ctx.request_id,
                }

        if request_ctx.deployment_profile == "central":
            self.audit_logger.log_event(
                build_audit_event(
                    ctx=request_ctx,
                    tool_name=name,
                    arguments=arguments,
                    result=result,
                    policy_decision=policy_decision,
                    status=status,
                    duration_ms=(perf_counter() - started) * 1000,
                )
            )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _dispatch_tool_with_timeout(
        self,
        name: str,
        arguments: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Dispatch a tool call with central request timeout enforcement."""
        if ctx.deployment_profile != "central":
            return self._dispatch_tool(name, arguments, ctx)

        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="root-mcp-tool")
        future = loop.run_in_executor(
            executor,
            self._dispatch_tool_in_request_context,
            name,
            arguments,
            ctx,
        )
        try:
            await asyncio.sleep(0.01)
            return await asyncio.wait_for(
                future,
                timeout=self.config.quotas.max_request_seconds,
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _dispatch_tool_in_request_context(
        self,
        name: str,
        arguments: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Dispatch a tool call while applying request-scoped file-cache keys."""
        with self.file_manager.request_context(ctx):
            return self._dispatch_tool(name, arguments, ctx)

    def _dispatch_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Dispatch an already-authorized tool call to its implementation."""
        import json

        # Mode management tools
        if name == "switch_mode":
            return self.switch_mode(arguments["mode"])
        if name == "get_server_info":
            root_available = is_root_available() if self.config.features.enable_root else False
            return {
                "server_name": self.config.server.name,
                "version": self.config.server.version,
                "current_mode": self.current_mode,
                "deployment_profile": self.config.deployment.profile,
                "transport": self.config.deployment.transport,
                "extended_components_loaded": self._extended_components_loaded,
                "available_modes": ["core", "extended"],
                "root_native_available": root_available,
                "root_native_enabled": (
                    self.config.features.enable_root
                    and self.config.root_native.execution_backend != "disabled"
                    and root_available
                ),
                "root_native_backend": self.config.root_native.execution_backend,
                "root_native_central_supported": False,
                "root_version": get_root_version() if root_available else None,
                "root_features": get_root_features() if root_available else {},
                "metrics": self.metrics.snapshot(),
            }

        # Core tools (always available)
        if name == "list_files":
            return self.discovery_tools.list_files(**arguments, ctx=ctx)
        if name == "inspect_file":
            return self.discovery_tools.inspect_file(**arguments, ctx=ctx)
        if name == "list_branches":
            return self.discovery_tools.list_branches(**arguments, ctx=ctx)
        if name == "validate_file":
            try:
                resolved = self.resource_resolver.resolve_path(arguments["path"], ctx, "read")
            except ResourceAccessDenied as e:
                return {"error": e.code, "message": e.message}
            return self.file_manager.validate_file(resolved.path)
        if name == "read_branches":
            return self.data_access_tools.read_branches(**arguments, ctx=ctx)
        if name == "get_branch_stats":
            # Handle defines parameter if passed as JSON string
            defines = arguments.get("defines")
            if defines is not None and isinstance(defines, str):
                try:
                    defines = json.loads(defines)
                except json.JSONDecodeError:
                    return {
                        "error": "invalid_parameter",
                        "message": "Invalid JSON in defines parameter",
                    }

            try:
                resolved = self.resource_resolver.resolve_path(arguments["path"], ctx, "read")
            except ResourceAccessDenied as e:
                return {"error": e.code, "message": e.message}

            return self.basic_stats.compute_stats(
                str(resolved.path),
                arguments["tree_name"],
                arguments["branches"],
                arguments.get("selection"),
                defines,
            )
        if name == "export_data":
            try:
                resolved = self.resource_resolver.resolve_path(arguments["path"], ctx, "export")
                output_path = self.path_validator.resolve_output_path(arguments["output_path"], ctx)
            except ResourceAccessDenied as e:
                return {"error": e.code, "message": e.message}
            except Exception as e:  # noqa: BLE001
                return {"error": "invalid_output_path", "message": str(e)}
            # Read data directly for export
            tree = self.file_manager.get_tree(resolved.path, arguments["tree_name"])
            arrays = tree.arrays(
                filter_name=arguments["branches"],
                cut=arguments.get("selection"),
                library="ak",
            )
            return self.data_exporter.export(
                arrays,
                output_path,
                arguments["format"],
                compress=arguments.get("compress", False),
            )

        # Extended tools (only in extended mode)
        if name in [
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
                return {
                    "error": "mode_error",
                    "message": (
                        f"Tool '{name}' requires extended mode. Current mode: {self.current_mode}"
                    ),
                    "hint": "Use switch_mode tool to enable extended mode",
                }

            # Delegate to appropriate handler
            if name == "compute_histogram":
                return self.analysis_tools.compute_histogram(**arguments, ctx=ctx)
            if name == "compute_histogram_2d":
                return self.analysis_tools.compute_histogram_2d(**arguments, ctx=ctx)
            if name == "fit_histogram":
                return self.analysis_tools.fit_histogram(**arguments, ctx=ctx)
            if name == "compute_invariant_mass":
                try:
                    resolved = self.resource_resolver.resolve_path(arguments["path"], ctx, "read")
                except ResourceAccessDenied as e:
                    return {"error": e.code, "message": e.message}
                arguments = {**arguments, "path": str(resolved.path)}
                return self.kinematics_ops.compute_invariant_mass(**arguments)
            if name == "compute_correlation":
                try:
                    resolved = self.resource_resolver.resolve_path(arguments["path"], ctx, "read")
                except ResourceAccessDenied as e:
                    return {"error": e.code, "message": e.message}
                arguments = {**arguments, "path": str(resolved.path)}
                return self.correlation_analysis.compute_correlation(**arguments)
            if name == "plot_histogram_1d":
                return self.plotting_tools.plot_histogram_1d(**arguments, ctx=ctx)
            if name == "plot_histogram_2d":
                return self.plotting_tools.plot_histogram_2d(**arguments, ctx=ctx)
            if name == "histogram_arithmetic":
                return self.analysis_tools.compute_histogram_arithmetic(**arguments)

        # Native ROOT tools
        if name in ["run_root_code", "run_rdataframe", "run_root_macro"]:
            if not self._root_native_available:
                return {
                    "error": "root_not_available",
                    "message": (
                        "Native ROOT tools are not available. "
                        "Ensure ROOT is installed and enable_root is set to true in config."
                    ),
                    "hint": "Use get_server_info to check ROOT availability",
                }
            if name == "run_root_code":
                return self.root_native_tools.run_root_code(**arguments)
            if name == "run_rdataframe":
                return self.root_native_tools.run_rdataframe(**arguments)
            if name == "run_root_macro":
                return self.root_native_tools.run_root_macro(**arguments)

        return {
            "error": "unknown_tool",
            "message": f"Unknown tool: {name}",
        }

    def _register_tools(self) -> None:
        """Register all MCP tools based on current mode."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools based on current mode."""
            return self.list_available_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls with mode awareness."""
            return await self.handle_tool_call(name, arguments)

    async def run(self) -> None:
        """Run the MCP server."""
        if self.config.deployment.transport != "stdio":
            raise RuntimeError(
                "Transport 'streamable_http' is configured but the HTTP runner is not "
                "available in this stdio path. Use 'root-mcp serve-http' for HTTP."
            )

        logger.info(f"Starting {self.config.server.name} v{self.config.server.version}")
        logger.info(f"Mode: {self.current_mode}")
        logger.info(f"Deployment profile: {self.config.deployment.profile}")
        logger.info(f"Transport: {self.config.deployment.transport}")
        logger.info(f"Resources configured: {len(self.config.resources)}")

        await run_stdio(self.server)


def _run_cleanup_exports(argv: list[str]) -> None:
    """Handle the ``root-mcp cleanup-exports`` operator command."""
    parser = argparse.ArgumentParser(
        prog="root-mcp cleanup-exports",
        description="Apply configured export retention policy.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (overrides ROOT_MCP_CONFIG env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would be removed without deleting them.",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        apply_env_overrides(config)
    except Exception as e:  # noqa: BLE001
        print(f"root-mcp cleanup-exports: failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)

    result = cleanup_exports(config, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))


def _run_init(argv: list[str]) -> None:
    """Handle the ``root-mcp init`` sub-command."""
    parser = argparse.ArgumentParser(
        prog="root-mcp init",
        description="Generate a minimal config.yaml for ROOT-MCP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  root-mcp init                        # placeholder URI, edit before use\n"
            "  root-mcp init --permissive           # URI set to current directory\n"
            "  root-mcp init --permissive --output ~/my-config.yaml\n"
        ),
    )
    parser.add_argument(
        "--permissive",
        action="store_true",
        help=(
            "Set the resource URI to the current working directory so the "
            "generated config works immediately without further editing."
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default="config.yaml",
        metavar="PATH",
        help="Where to write the config file (default: ./config.yaml).",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output).resolve()

    if output_path.exists():
        print(f"Warning: {output_path} already exists — overwriting.", file=sys.stderr)

    if args.permissive:
        uri = f"file://{Path.cwd()}"
    else:
        uri = "file:///REPLACE_WITH_YOUR_DATA_PATH"

    # Detect whether ROOT/PyROOT is available so the flag is pre-set correctly.
    root_detected = is_root_available()
    enable_root = "true" if root_detected else "false"
    if root_detected:
        print("ROOT/PyROOT detected — setting enable_root: true in generated config.")

    content = _CONFIG_TEMPLATE.format(uri=uri, enable_root=enable_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"Created: {output_path}")
    if not args.permissive:
        print(
            f"  → Edit the 'uri' field to point at your ROOT files, then run:\n"
            f"    root-mcp --config {output_path}"
        )
    else:
        print(f"  → Config is ready. Run:\n    root-mcp --config {output_path}")


def _extract_server_command(argv: list[str]) -> tuple[str, list[str]]:
    """Return the server command and remaining argv.

    ``root-mcp`` remains the compatibility stdio entrypoint. The explicit
    transport commands are shallow wrappers over the same parser so existing
    flags keep working in either position after the command name.
    """
    if argv and argv[0] in {"serve-stdio", "serve-http"}:
        return argv[0], argv[1:]
    return "serve-stdio-default", argv


def main() -> None:
    """Main entry point."""
    # Dispatch 'root-mcp init …' before the main parser so the init sub-command
    # gets its own clean argument namespace and the existing server flags are
    # unaffected.
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        _run_init(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup-exports":
        _run_cleanup_exports(sys.argv[2:])
        return

    server_command, parser_argv = _extract_server_command(sys.argv[1:])

    parser = argparse.ArgumentParser(
        prog=(
            "root-mcp" if server_command == "serve-stdio-default" else f"root-mcp {server_command}"
        ),
        description="ROOT-MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Zero-config quick start:\n"
            "  root-mcp --data-path /path/to/root/files\n\n"
            "Explicit stdio transport:\n"
            "  root-mcp serve-stdio --data-path /path/to/root/files\n\n"
            "HTTP central service:\n"
            "  root-mcp serve-http --config central.yaml --profile central --auth-required "
            "--auth-provider external-bearer --origin https://client.example\n\n"
            "With native ROOT support (no config file needed):\n"
            "  root-mcp --data-path /path/to/root/files --enable-root\n\n"
            "Multiple directories:\n"
            "  root-mcp --data-path /data/run3 --data-path /data/mc\n\n"
            "Via environment variable:\n"
            "  ROOT_MCP_DATA_PATH=/data/run3 root-mcp\n\n"
            "Generate a config file:\n"
            "  root-mcp init --permissive"
        ),
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (overrides ROOT_MCP_CONFIG env var)",
    )
    parser.add_argument(
        "--data-path",
        action="append",
        metavar="DIR",
        dest="data_paths",
        help=(
            "Local directory containing ROOT files. "
            "Can be specified multiple times. "
            "Adds a resource and permits access to that directory. "
            "No config.yaml required."
        ),
    )
    parser.add_argument(
        "--enable-root",
        action="store_true",
        default=False,
        dest="enable_root",
        help=(
            "Enable native ROOT/PyROOT tools (run_root_code, run_rdataframe, "
            "run_root_macro). Requires a ROOT installation on PATH. "
            "No config.yaml required."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["core", "extended"],
        default=None,
        dest="mode",
        metavar="MODE",
        help=(
            "Server mode: 'core' (file I/O + basic stats only) or "
            "'extended' (full analysis suite, default). "
            "Overrides config.yaml and ROOT_MCP_MODE."
        ),
    )
    parser.add_argument(
        "--server-name",
        default=None,
        dest="server_name",
        metavar="NAME",
        help=(
            "Override the MCP server name reported to clients. "
            "Overrides config.yaml and ROOT_MCP_SERVER_NAME."
        ),
    )
    # Deployment / Auth
    parser.add_argument(
        "--profile",
        choices=["local", "central"],
        default=None,
        dest="profile",
        metavar="PROFILE",
        help=(
            "Deployment profile: local or central (default: local). "
            "Overrides ROOT_MCP_DEPLOYMENT_PROFILE."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=None,
        dest="transport",
        metavar="TRANSPORT",
        help=(
            "MCP transport: stdio or streamable-http. "
            "streamable-http is used by the serve-http command. "
            "Overrides ROOT_MCP_TRANSPORT."
        ),
    )
    parser.add_argument(
        "--auth-required",
        action="store_true",
        default=None,
        dest="auth_required",
        help=(
            "Require authenticated callers. Central deployments must set this. "
            "Overrides ROOT_MCP_AUTH_REQUIRED."
        ),
    )
    parser.add_argument(
        "--auth-provider",
        choices=["none", "external-bearer", "trusted-headers"],
        default=None,
        dest="auth_provider",
        metavar="PROVIDER",
        help=(
            "Authentication provider: none, external-bearer, or trusted-headers. "
            "Overrides ROOT_MCP_AUTH_PROVIDER."
        ),
    )
    # HTTP startup
    parser.add_argument(
        "--host",
        default=None,
        dest="host",
        metavar="HOST",
        help="HTTP bind host for serve-http (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        dest="port",
        metavar="PORT",
        help="HTTP bind port for serve-http (default: 8000).",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        dest="endpoint",
        metavar="PATH",
        help="HTTP MCP endpoint path for serve-http (default: /mcp).",
    )
    parser.add_argument(
        "--origin",
        action="append",
        default=None,
        dest="origin",
        metavar="ORIGIN",
        help="Allowed HTTP Origin for serve-http. Repeat to allow multiple origins.",
    )
    parser.add_argument(
        "--allow-public-bind",
        action="store_true",
        default=None,
        dest="allow_public_bind",
        help="Allow serve-http to bind to 0.0.0.0, ::, or another non-loopback host.",
    )
    parser.add_argument(
        "--allow-local-http",
        action="store_true",
        default=None,
        dest="allow_local_http",
        help="Allow serve-http with deployment.profile=local for explicit local testing.",
    )
    # Security
    parser.add_argument(
        "--allowed-root",
        action="append",
        dest="allowed_root",
        metavar="DIR",
        help=(
            "Restrict file access to this directory (absolute path). "
            "Repeat to allow multiple directories. "
            "Replaces any allowed_roots set in config.yaml. "
            "Overrides ROOT_MCP_ALLOWED_ROOTS."
        ),
    )
    _allow_remote_group = parser.add_mutually_exclusive_group()
    _allow_remote_group.add_argument(
        "--allow-remote",
        dest="allow_remote",
        action="store_true",
        help="Allow access to remote (non-file://) URIs.",
    )
    _allow_remote_group.add_argument(
        "--no-allow-remote",
        dest="allow_remote",
        action="store_false",
        help="Deny access to remote URIs (default behaviour).",
    )
    parser.set_defaults(allow_remote=None)
    parser.add_argument(
        "--allowed-protocols",
        default=None,
        dest="allowed_protocols",
        metavar="PROTOCOLS",
        help=(
            "Comma-separated list of permitted URI protocols "
            "(e.g. 'file,root,http'). "
            "Replaces config.yaml allowed_protocols. "
            "Overrides ROOT_MCP_ALLOWED_PROTOCOLS."
        ),
    )
    parser.add_argument(
        "--max-path-depth",
        type=int,
        default=None,
        dest="max_path_depth",
        metavar="N",
        help=(
            "Maximum directory depth for path validation (default: 10). "
            "Overrides ROOT_MCP_MAX_PATH_DEPTH."
        ),
    )
    # Output / Export
    parser.add_argument(
        "--export-path",
        default=None,
        dest="export_path",
        metavar="DIR",
        help=(
            "Directory for exported files (default: /tmp/root_mcp_output). "
            "Overrides ROOT_MCP_EXPORT_PATH."
        ),
    )
    parser.add_argument(
        "--export-formats",
        default=None,
        dest="export_formats",
        metavar="FORMATS",
        help=(
            "Comma-separated list of permitted export formats "
            "(e.g. 'json,csv,parquet'). "
            "Overrides ROOT_MCP_EXPORT_FORMATS."
        ),
    )
    parser.add_argument(
        "--no-export",
        dest="enable_export",
        action="store_false",
        help="Disable the file export feature entirely.",
    )
    parser.set_defaults(enable_export=None)
    # Core Limits & Cache
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        dest="max_rows",
        metavar="N",
        help=(
            "Maximum rows returned per read call (default: 1_000_000). Overrides ROOT_MCP_MAX_ROWS."
        ),
    )
    parser.add_argument(
        "--max-export-rows",
        type=int,
        default=None,
        dest="max_export_rows",
        metavar="N",
        help=(
            "Maximum rows written per export (default: 10_000_000). "
            "Overrides ROOT_MCP_MAX_EXPORT_ROWS."
        ),
    )
    parser.add_argument(
        "--no-cache",
        dest="cache_enabled",
        action="store_false",
        help="Disable the in-memory file metadata cache.",
    )
    parser.set_defaults(cache_enabled=None)
    parser.add_argument(
        "--cache-size",
        type=int,
        default=None,
        dest="cache_size",
        metavar="N",
        help=(
            "Number of file entries held in the metadata cache (default: 50). "
            "Overrides ROOT_MCP_CACHE_SIZE."
        ),
    )
    # Extended Analysis
    parser.add_argument(
        "--max-bins-1d",
        type=int,
        default=None,
        dest="max_bins_1d",
        metavar="N",
        help="Maximum bins for 1D histograms (default: 10000). Overrides ROOT_MCP_MAX_BINS_1D.",
    )
    parser.add_argument(
        "--max-bins-2d",
        type=int,
        default=None,
        dest="max_bins_2d",
        metavar="N",
        help="Maximum bins for 2D histograms (default: 1000). Overrides ROOT_MCP_MAX_BINS_2D.",
    )
    parser.add_argument(
        "--fitting-iterations",
        type=int,
        default=None,
        dest="fitting_iterations",
        metavar="N",
        help="Maximum fitting iterations (default: 10000). Overrides ROOT_MCP_FITTING_ITERATIONS.",
    )
    parser.add_argument(
        "--plot-dpi",
        type=int,
        default=None,
        dest="plot_dpi",
        metavar="N",
        help="Plot resolution in DPI (default: 100). Overrides ROOT_MCP_PLOT_DPI.",
    )
    parser.add_argument(
        "--plot-format",
        choices=["png", "pdf", "svg"],
        default=None,
        dest="plot_format",
        metavar="FMT",
        help="Default plot output format: png, pdf, or svg (default: png). Overrides ROOT_MCP_PLOT_FORMAT.",
    )
    parser.add_argument(
        "--plot-width",
        type=float,
        default=None,
        dest="plot_width",
        metavar="N",
        help="Plot figure width in inches (default: 10.0). Overrides ROOT_MCP_PLOT_WIDTH.",
    )
    parser.add_argument(
        "--plot-height",
        type=float,
        default=None,
        dest="plot_height",
        metavar="N",
        help="Plot figure height in inches (default: 6.0). Overrides ROOT_MCP_PLOT_HEIGHT.",
    )
    # Native ROOT Execution
    parser.add_argument(
        "--root-timeout",
        type=int,
        default=None,
        dest="root_timeout",
        metavar="N",
        help="ROOT execution timeout in seconds (default: 60). Overrides ROOT_MCP_ROOT_TIMEOUT.",
    )
    parser.add_argument(
        "--root-backend",
        choices=["local_subprocess", "disabled"],
        default=None,
        dest="root_backend",
        metavar="BACKEND",
        help=(
            "Native ROOT execution backend: local_subprocess or disabled "
            "(default: local_subprocess for local deployments). Overrides ROOT_MCP_ROOT_BACKEND."
        ),
    )
    parser.add_argument(
        "--root-workdir",
        type=str,
        default=None,
        dest="root_workdir",
        metavar="DIR",
        help="Working directory for ROOT execution (default: /tmp/root_mcp_native). Overrides ROOT_MCP_ROOT_WORKDIR.",
    )
    parser.add_argument(
        "--root-max-output",
        type=int,
        default=None,
        dest="root_max_output",
        metavar="N",
        help="Maximum output size from ROOT in bytes (default: 10_000_000). Overrides ROOT_MCP_ROOT_MAX_OUTPUT.",
    )
    parser.add_argument(
        "--root-max-code",
        type=int,
        default=None,
        dest="root_max_code",
        metavar="N",
        help="Maximum ROOT script length in characters (default: 100_000). Overrides ROOT_MCP_ROOT_MAX_CODE.",
    )
    # Remote Resources
    parser.add_argument(
        "--resource",
        action="append",
        default=None,
        dest="resource",
        metavar="NAME=URI[|DESCRIPTION]",
        help=(
            "Declare a named resource. Format: NAME=URI or NAME=URI|DESCRIPTION "
            "(use | to separate the optional description from the URI, since URIs "
            "contain colons). Can be repeated. Overrides ROOT_MCP_RESOURCES."
        ),
    )
    # Log Level
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        dest="log_level",
        metavar="LEVEL",
        help=(
            "Set logging verbosity: DEBUG, INFO, WARNING, or ERROR "
            "(default: INFO). Overrides ROOT_MCP_LOG_LEVEL."
        ),
    )
    args = parser.parse_args(parser_argv)

    if server_command == "serve-http":
        if args.transport == "stdio":
            parser.error("serve-http cannot be combined with --transport stdio")
        args.transport = "streamable-http"
    elif server_command == "serve-stdio":
        if args.transport == "streamable-http":
            parser.error("serve-stdio cannot be combined with --transport streamable-http")
        args.transport = "stdio"

    # Apply log level as early as possible — before load_config so that
    # config-loading log messages are also at the right verbosity.
    import os as _os

    from root_mcp.config import apply_log_level as _apply_log_level

    _env_log_level = _os.environ.get("ROOT_MCP_LOG_LEVEL", "").strip().upper()
    _cli_log_level = getattr(args, "log_level", None)  # CLI wins over env
    _final_log_level = _cli_log_level or _env_log_level or None
    if _final_log_level:
        try:
            _apply_log_level(_final_log_level)
        except ValueError as e:
            # Use print because logger level may not be set correctly yet.
            print(f"root-mcp: invalid log level: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        config = load_config(args.config)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Merge data paths from CLI --data-path flags.
    from root_mcp.config import apply_data_paths

    cli_paths: list[str] = args.data_paths or []
    if cli_paths:
        apply_data_paths(config, cli_paths)
        logger.info(f"Added {len(cli_paths)} data path(s) from --data-path: {cli_paths}")

    # Apply environment variable overrides (priority 3: above YAML, below CLI).
    from root_mcp.config import apply_cli_overrides

    try:
        apply_env_overrides(config)
    except ValueError as e:
        logger.error(f"Invalid environment variable: {e}")
        sys.exit(1)

    # Apply CLI flag overrides (priority 4: highest).
    try:
        apply_cli_overrides(config, args)
    except ValueError as e:
        logger.error(f"Invalid CLI argument: {e}")
        sys.exit(1)

    # Enable native ROOT support via --enable-root flag or ROOT_MCP_ENABLE_ROOT env var.
    # (Shipped before apply_env/cli_overrides; kept inline for backward compat.)
    import os as _os

    if args.enable_root or _os.environ.get("ROOT_MCP_ENABLE_ROOT", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        config.features.enable_root = True
        logger.info("Native ROOT support enabled via --enable-root / ROOT_MCP_ENABLE_ROOT")

    try:
        if server_command == "serve-http":
            server = ROOTMCPServer(config)
            asyncio.run(run_http(server))
            return

        server = ROOTMCPServer(config)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except HTTPStartupError as e:
        logger.error(f"Invalid HTTP configuration: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid deployment configuration: {e}")
        sys.exit(1)
    except NotImplementedError as e:
        logger.error(f"HTTP runner unavailable: {e}")
        sys.exit(1)
    except Exception:
        logger.exception("Server error")
        sys.exit(1)


if __name__ == "__main__":
    main()
