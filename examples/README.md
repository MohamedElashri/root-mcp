# ROOT-MCP Examples

This directory contains utilities and examples for ROOT-MCP.

## Available Examples

### Basic Usage Example

**`basic_usage.py`** - Complete working example demonstrating core ROOT-MCP functionality

This example shows:
- Server initialization in different modes
- File inspection and validation
- Branch listing and data reading
- Statistics computation
- Histogram creation (extended mode)

**Usage:**
```bash
# First, create sample data
python examples/create_sample_data.py

# Then run the example
python examples/basic_usage.py
```

### Sample Data Generation

**`create_sample_data.py`** - Generate test ROOT files for development and testing

Creates multiple ROOT files with different structures:
- `sample_events.root` - 10,000 events with particle physics data
- `large_sample.root` - 100,000 events for performance testing
- `histograms.root` - Pre-filled histograms (1D, 2D, profiles)
- `analysis.root` - Multi-tree file with signal/background/systematics

**Usage:**
```bash
python examples/create_sample_data.py
```

Files are created in `data/root_files/` directory.

**Features:**
- Realistic particle physics variables (pT, η, φ, mass)
- Jagged arrays (variable-length per event)
- Multiple trees and directories
- Histograms with various binning schemes

## Using ROOT-MCP

For usage examples, see:

### Documentation
- **[Quick Start Guide](../README.md#quick-start)** - Get started with ROOT-MCP
- **[Mode Selection Guide](../docs/guides/modes.md)** - Choose between core and extended modes
- **[Configuration Guide](../docs/guides/configuration.md)** - Configure the server
- **[Tool Reference](../docs/api/tools.md)** - Complete tool documentation

### Integration Tests
The `tests/` directory contains comprehensive examples:
- **`tests/integration_test.py`** - Direct API usage examples
- **`tests/test_mcp_integration.py`** - MCP protocol usage examples

These tests demonstrate:
- File inspection and validation
- Data reading with selections
- Statistics computation
- Histogram creation and fitting
- Mode switching
- Complete analysis workflows
