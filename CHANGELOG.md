# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

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
