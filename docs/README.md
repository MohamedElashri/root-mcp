# ROOT-MCP Documentation

Welcome to the comprehensive documentation for **ROOT-MCP**, the Model Context Protocol server for CERN ROOT files.

## Quick Links

- **[Installation & Quick Start](../README.md)**: Get started in minutes
- **[Architecture Overview](ARCHITECTURE.md)**: Understand the dual-mode design
- **[Mode Selection Guide](guides/modes.md)**: Choose between core and extended modes

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

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation hub
├── ARCHITECTURE.md              # System architecture and design
├── CONTRIBUTING.md              # Contribution guidelines
├── guides/
│   ├── modes.md                 # Mode selection guide
│   ├── configuration.md         # Configuration reference
│   ├── llm_integration.md       # AI assistant integration & Advanced examples
└── api/
    └── tools.md                 # Complete tool reference
```

## Key Concepts

### Dual-Mode Architecture

ROOT-MCP operates in two modes:

- **Core Mode**: Lightweight file operations and basic statistics
- **Extended Mode**: Full physics analysis with fitting, kinematics, and correlations

Mode is controlled via `config.yaml` and can be switched at runtime. See the [Mode Selection Guide](guides/modes.md) for details.

### Tool Categories

**Core Tools** (9 tools - always available):
- File inspection and validation
- Branch reading and statistics
- Data export (JSON/CSV/Parquet)
- Mode management

**Extended Tools** (6 additional tools - extended mode only):
- Histogram fitting
- Kinematics calculations
- Correlation analysis
- Plot generation

See the [Tool Reference](api/tools.md) for complete documentation.

### Configuration-Driven

All behavior is controlled through `config.yaml`:
- Mode selection
- Resource limits
- Security constraints
- Analysis parameters

See the [Configuration Guide](guides/configuration.md) for details.

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
4. Use `generate_plot` for visualization

### Data Export
1. Use `read_branches` to get data
2. Use `export_data` to save as JSON/CSV/Parquet
3. Process with external tools

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/MohamedElashri/root-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MohamedElashri/root-mcp/discussions)
- **Examples**: See `examples/` directory in repository

## Version Information

This documentation is for ROOT-MCP v0.1.3+

For older versions, see the [changelog](../CHANGELOG.md).
