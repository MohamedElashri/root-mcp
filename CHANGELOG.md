# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.



## [0.1.2] - 2025-12-18

### Added
- **New Tool**: `compute_kinematics` - Compute derived kinematic quantities (invariant mass, transverse mass, delta R, delta phi) from particle four-momenta and angular coordinates. Supports multiple calculations in a single request with physics selections.
- **New Tool**: `fit_histogram` - Fit histograms with built-in (Gaussian, Exponential, Crystal Ball, Polynomial), composite (sum of models), and custom string models. Includes support for parameter constraints (`bounds`, `fixed_parameters`).
- **New Tool**: `generate_plot` - Generate plots from analysis data with support for log scales, grids, and automatic unit labeling.

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
