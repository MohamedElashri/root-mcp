# ROOT-MCP Documentation

Welcome to the comprehensive documentation for **ROOT-MCP**, the Model Context Protocol server for CERN ROOT files.

## Quick Links

- **[Installation & Quick Start](../README.md)**: Get started in minutes (zero-config path included)
- **[Architecture Overview](ARCHITECTURE.md)**: Understand the three-tier design
- **[Mode Selection Guide](guides/modes.md)**: Choose between core, extended, and native ROOT modes

## User Guides

### Getting Started
- **[Installation & Quick Start](../README.md)**: Installation and basic setup
- **[Configuration Guide](guides/configuration.md)**: Complete configuration reference
- **[Mode Selection Guide](guides/modes.md)**: Core vs Extended mode explained

### Using ROOT-MCP
- **[LLM Integration Guide](guides/llm_integration.md)**: Working with AI assistants like Claude (includes Kinematics examples)

## API Reference

- **[Tool Reference](api/tools.md)**: Complete tool documentation with examples
  - Core tools (always available)
  - Extended tools (extended mode only)
  - JSON payload examples

## Technical Documentation

- **[Architecture](ARCHITECTURE.md)**: System design and component details
  - Dual-mode architecture
  - Component breakdown
  - Security model
  - Performance considerations
- **[Contributing](CONTRIBUTING.md)**: Development guidelines

### Key Concepts

### Zero-Config Start

No YAML file required. Start the server with a single flag:

```bash
root-mcp --data-path /path/to/your/data
```

Or use an environment variable: `export ROOT_MCP_DATA_PATH=/path/to/data`. Generate a starter config with `root-mcp init --permissive`. See the [Configuration Guide](guides/configuration.md) for details.

### Three-Tier Architecture

ROOT-MCP operates in three tiers:

- **Core Mode**: Lightweight file operations and basic statistics
- **Extended Mode**: Full physics analysis with fitting, kinematics, and correlations
- **Native ROOT** (optional): Execute PyROOT code, RDataFrame, and C++ macros — requires a ROOT installation and `enable_root: true`

Mode is controlled via `config.yaml` and can be switched at runtime. See the [Mode Selection Guide](guides/modes.md) for details.

### Tool Categories

**Core Tools** (9 tools — always available):
- File inspection and validation
- Branch reading and statistics
- Data export (JSON/CSV/Parquet)
- Mode management

**Extended Tools** (8 additional tools — extended mode only):
- Histogram fitting
- Kinematics calculations
- Correlation analysis
- Plot generation

**Native ROOT Tools** (3 additional tools — optional, requires ROOT installation + `enable_root: true`):
- `run_root_code` — arbitrary PyROOT/Python code in a sandboxed subprocess
- `run_rdataframe` — RDataFrame histograms without boilerplate
- `run_root_macro` — C++ ROOT macros via `gROOT.ProcessLine`

See the [Tool Reference](api/tools.md) for complete documentation.

### Configuration-Driven

Full behavior is controlled through `config.yaml` — but a config file is not required for basic use. The fastest path is `root-mcp --data-path /your/data`. See the [Configuration Guide](guides/configuration.md) for all options.

## Common Tasks

### Exploring a ROOT File
1. Start in core mode
2. Use `inspect_file` to see structure
3. Use `list_branches` to see available data
4. Use `read_branches` to access data

### Physics Analysis
1. Switch to extended mode
2. Use `compute_invariant_mass` for kinematics
3. Use `compute_histogram` with fitting
4. Use `plot_histogram_1d` for visualization

### Native ROOT Analysis
1. Ensure ROOT is installed and `enable_root: true` is set
2. Use `get_server_info` to confirm `root_native_available: true`
3. Use `run_rdataframe` for RDataFrame event loops
4. Use `run_root_code` for custom PyROOT analysis
5. Use `run_root_macro` for C++ macros

### Data Export
1. Use `read_branches` to get data
2. Use `export_data` to save as JSON/CSV/Parquet
3. Process with external tools

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/MohamedElashri/root-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MohamedElashri/root-mcp/discussions)
- **Examples**: See `examples/` directory in repository

## Version Information

This documentation is for ROOT-MCP v0.1.5+

For older versions, see the [changelog](../CHANGELOG.md).
