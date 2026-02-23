# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [0.1.5] - 2026-02-23

### Added
- **Optional Native ROOT/PyROOT Support**: When a native ROOT installation is available, three new tools become accessible:
  - `run_root_code`: Execute arbitrary PyROOT/Python code in a sandboxed subprocess with structured result capture (stdout, stderr, output files, execution time)
  - `run_rdataframe`: Convenience wrapper to compute RDataFrame histograms without writing boilerplate
  - `run_root_macro`: Execute C++ ROOT macros via `gROOT.ProcessLine`
- **ROOT Detection**: Subprocess-based probe that safely detects ROOT availability, version, and optional features (RDataFrame, RooFit, TMVA, Minuit2) without polluting the server process
- **Code Validation**: AST-based security sandbox that blocks dangerous imports (`os`, `subprocess`, `shutil`, `socket`, etc.), blocked built-ins (`exec`, `eval`, `compile`), and dangerous attribute accesses (`.system`, `.popen`, `.kill`, `.rmtree`, etc.)
- **Code Templates**: Pre-built templates for common ROOT operations — `rdataframe_histogram`, `rdataframe_snapshot`, `tcanvas_plot`, `roofit_fit`, `root_file_write`, `root_macro`
- **Configuration**: New `enable_root` feature flag and `root_native` config section for execution timeout, output size limits, and working directory
- **Server Info**: `get_server_info` now reports `root_native_available`, `root_native_enabled`, `root_version`, and `root_features`
- **Zero-config / Permissive-default Onboarding**: ROOT-MCP now works without any config file
  - `--data-path` CLI flag sets the data directory inline
  - `ROOT_MCP_DATA_PATH` environment variable as an alternative
  - `root-mcp init --permissive` generates a starter `config.yaml` pre-filled with the current directory
- **Full Environment-Variable Configuration**: Every `config.yaml` field now has a matching `ROOT_MCP_*` env var (25 variables across 8 phases):
  - *Server*: `ROOT_MCP_MODE`, `ROOT_MCP_SERVER_NAME`
  - *Security*: `ROOT_MCP_ALLOWED_ROOTS`, `ROOT_MCP_ALLOW_REMOTE`, `ROOT_MCP_ALLOWED_PROTOCOLS`, `ROOT_MCP_MAX_PATH_DEPTH`
  - *Output*: `ROOT_MCP_EXPORT_PATH`, `ROOT_MCP_EXPORT_FORMATS`, `ROOT_MCP_ENABLE_EXPORT`
  - *Limits*: `ROOT_MCP_MAX_ROWS`, `ROOT_MCP_MAX_EXPORT_ROWS`
  - *Cache*: `ROOT_MCP_CACHE`, `ROOT_MCP_CACHE_SIZE`
  - *Analysis*: `ROOT_MCP_MAX_BINS_1D`, `ROOT_MCP_MAX_BINS_2D`, `ROOT_MCP_FITTING_ITERATIONS`
  - *Plotting*: `ROOT_MCP_PLOT_DPI`, `ROOT_MCP_PLOT_FORMAT`, `ROOT_MCP_PLOT_WIDTH`, `ROOT_MCP_PLOT_HEIGHT`
  - *ROOT exec*: `ROOT_MCP_ROOT_TIMEOUT`, `ROOT_MCP_ROOT_WORKDIR`, `ROOT_MCP_ROOT_MAX_OUTPUT`, `ROOT_MCP_ROOT_MAX_CODE`
  - *Resources*: `ROOT_MCP_RESOURCES` (semicolon-separated `NAME=URI|description` specs)
  - *Logging*: `ROOT_MCP_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **Full CLI-Flag Configuration**: Every env var above has an equivalent `root-mcp` flag (e.g. `--mode`, `--allowed-root`, `--max-rows`, `--root-timeout`, `--resource`, `--log-level`). Merge priority: defaults → config.yaml → env vars → CLI flags
- **`apply_env_overrides()` / `apply_cli_overrides()`**: New pure functions in `config.py` that apply the env-var and CLI layers onto a loaded `Config` object
- **`apply_log_level()`**: Standalone function; applied before `load_config()` so early startup messages respect the configured level

### Changed
- ROOT native tools are gated behind dual condition: `enable_root: true` in config AND ROOT importable in environment
- Extended tools `__init__.py` now exports `RootNativeTools`
- `main()` in `server.py` now calls `apply_env_overrides` then `apply_cli_overrides` after loading config, completing the four-source merge chain

## [0.1.4] - 2026-01-15

### Fixed
- **Histogram Broadcasting Error**: Fixed "operands could not be broadcast together" error in `compute_histogram` by adding `bin_centers` to the return structure (previously only returned `bin_edges`)
- **Critical Bug Fix**: Fixed parameter handling issues in multiple tools when called via MCP client:
  - **tree_name parameter**: The following functions had parameter `tree` but the MCP tool schema defined it as `tree_name`:
    - `list_branches` in `DiscoveryTools`
    - `read_branches` in `DataAccessTools`
    - `compute_histogram` in `AnalysisTools`
    - `compute_histogram_2d` in `AnalysisTools`
  - **entry_start/entry_stop parameters**: Added support for `entry_start` and `entry_stop` parameters in `read_branches` to match MCP schema (converts to `offset` and `limit` internally)
  - **defines parameter**: Added automatic JSON parsing when `defines` parameter is passed as a string instead of a dictionary object (MCP client serialization issue)
  - **Server routing**: Fixed `compute_histogram` and `compute_histogram_2d` to route through `AnalysisTools` wrapper instead of calling `HistogramOperations` directly, enabling proper `defines` parameter support
  - **Tool Parameter Compliance**: Updated `fit_histogram` schema to correctly accept composite models (lists) and file-related arguments (`path`, `tree_name`, etc.) for on-the-fly computation.
  - **Plot Output**: Fixed critical issue where `plot_histogram_1d` and `plot_histogram_2d` failed to write image files to disk despite reporting success.
  - **Defines Dependency Resolution**: Fixed a bug in topological sorting that incorrectly flagged valid variable dependencies as circular (inverted dependency graph logic).

### Added
- **Plotting Tools**: Added dedicated plotting tools that create and save plots directly:
  - `plot_histogram_1d`: Create 1D histogram plots with full customization (title, labels, log scale, style)
  - `plot_histogram_2d`: Create 2D histogram plots (e.g., Dalitz plots, correlation plots)
  - Both tools support `defines` parameter for server-side variable computation
  - **Pre-calculated Data**: Supports plotting memory-resident data (e.g. calculated asymmetry maps) via `data` argument, bypassing ROOT file requirements
  - **Polynomial Models**: Added `polynomial_2` (quadratic) and `polynomial_3` (cubic), and enabled dynamic degree detection for `polynomial` based on initial guess length.
  - **Smart Custom Models**: `fit_histogram` now automatically parses raw string formulas (e.g. `"a*x + b"`), detecting parameters without needing explicit dictionary syntax.
  - **Multi-file Histograms**: `compute_histogram` and `compute_histogram_2d` now accept a list of file paths (e.g. `["file1.root", "file2.root"]`), automatically aggregating statistics and handling range consistency.
  - **Histogram Arithmetic**: Added `histogram_arithmetic` tool to perform operations like `asymmetry` (CP Map), `subtract`, `divide`, etc. on calculated histograms server-side.
  - Plots are saved to specified output paths (PNG, PDF, SVG formats supported)
  - Includes publication-ready styling options
- **defines support for get_branch_stats**: Added `defines` parameter to `get_branch_stats` tool, enabling statistics computation on derived variables (e.g., compute stats for invariant mass without reading all momentum components)

### Removed
- **generate_plot tool**: Replaced with proper plotting tools that work directly with ROOT data instead of requiring pre-computed data objects


## [0.1.3] - 2026-01-15

### Added
- **Dual-Mode Architecture**: Introduced core and extended modes for flexible resource usage
  - Core mode: Lightweight file operations and basic statistics (minimal dependencies)
  - Extended mode: Full physics analysis with fitting, kinematics, and correlations
- **Runtime Mode Switching**: Switch between core and extended modes without server restart via `switch_mode` tool
- **New Tool**: `get_server_info` - Get server capabilities and current mode information
- **New Tool**: `validate_file` - Check ROOT file integrity and readability
- **New Tool**: `export_data` - Export branch data to JSON, CSV, or Parquet formats
- **Modular Analysis Components**: Separated analysis operations into dedicated modules
  - `HistogramOperations`: Advanced 1D/2D histogram creation
  - `KinematicsOperations`: Particle physics calculations (invariant mass, transverse mass, delta R)
  - `CorrelationAnalysis`: Statistical correlation analysis (Pearson, Spearman, mutual information)
- **Lazy Loading**: Extended components only loaded when needed for memory efficiency

### Changed
- **Restructured Codebase**: Organized into `core/`, `extended/`, and `common/` directories
- **Configuration System**: Updated to support mode-aware settings with `core` and `extended` sections
- **Server Implementation**: Rewritten with conditional tool registration based on current mode
- **Dependency Management**: All dependencies included by default, mode controlled via configuration
- **Import Paths**: Updated all imports to use new module structure

## [0.1.2] - 2025-12-18

### Added
- **New Tool**: `compute_kinematics` - Compute derived kinematic quantities (invariant mass, transverse mass, delta R, delta phi) from particle four-momenta and angular coordinates. Supports multiple calculations in a single request with physics selections.

### Changed
- Updated documentation with detailed guides and API references for new tools.
- Improved error handling and validation for tool inputs.
- The `read_branches` tool now supports derived branches via defines parameter

### Fixed
- Bug fixes histogram handling in `fit_histogram` tool.
- Bug fixes in `generate_plot` tool that now handle different data stuctures.

## [0.1.1] - 2025-12-13

### Added

- **New Tool**: `fit_histogram` - Fit histograms with built-in (Gaussian, Exponential, Crystal Ball, Polynomial), composite (sum of models), and custom string models. Includes support for parameter constraints (`bounds`, `fixed_parameters`).
- **New Tool**: `generate_plot` - Generate plots from analysis data with support for log scales, grids, and automatic unit labeling.
- **New Capability**: Define new branches/variables using advanced physics math (`sinh`, `arcsin`, etc.) via the `defines` argument.

## [0.1.0] - 2025-12-12

### Added

- Initial public release.
