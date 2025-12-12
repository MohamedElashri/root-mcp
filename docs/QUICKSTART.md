# ROOT-MCP Quick Start Guide

Get up and running with ROOT-MCP in 5 minutes.

## Prerequisites

- Python 3.10 or later
- pip or conda/uv

## Installation

### Option 1: From Source (Recommended for Development)

```bash
# Clone repository
git clone https://github.com/MohamedElashri/root-mcp.git
cd root-mcp

# Install in development mode
pip install -e .

# Or with optional dependencies
pip install -e ".[dev,xrootd]"
```

### Option 2: From PyPI (When Published)

```bash
pip install root-mcp
```

## Create Sample Data

Generate test ROOT files:

```bash
# Create sample data
python examples/create_sample_data.py
```

This creates several ROOT files in `data/root_files/`:
- `sample_events.root` (10k events)
- `large_sample.root` (100k events)
- `histograms.root` (pre-filled histograms)
- `analysis.root` (multiple trees and directories)

## Configure Server

Create `config.yaml` in your project directory:

```yaml
# Minimal configuration
resources:
  - name: "local_data"
    uri: "file:///absolute/path/to/data/root_files"
    description: "Sample ROOT files"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/absolute/path/to/data/root_files"
    - "/tmp/root_mcp_output"
  allowed_protocols: ["file"]

limits:
  max_rows_per_call: 1_000_000
  operation_timeout_sec: 60
```

**Important**: Replace `/absolute/path/to/data/root_files` with the actual absolute path.

## Start Server

```bash
# Start MCP server
root-mcp

# Or specify config file
ROOT_MCP_CONFIG=/path/to/config.yaml root-mcp
```

The server will run in stdio mode, communicating over stdin/stdout using the MCP protocol.

## Test with MCP Client

### Using Claude Desktop (or other MCP client)

Configure your MCP client to connect to the ROOT-MCP server:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "args": [],
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

### Using Python MCP Client

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_root_mcp():
    server_params = StdioServerParameters(
        command="root-mcp",
        env={"ROOT_MCP_CONFIG": "/path/to/config.yaml"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")

            # Call a tool
            result = await session.call_tool("list_files", {})
            print(f"Files: {result}")

asyncio.run(test_root_mcp())
```

## First Analysis

Try these commands with your MCP client:

### 1. List Files

```json
{
  "name": "list_files",
  "arguments": {}
}
```

### 2. Inspect a File

```json
{
  "name": "inspect_file",
  "arguments": {
    "path": "/path/to/data/root_files/sample_events.root"
  }
}
```

### 3. List Branches

```json
{
  "name": "list_branches",
  "arguments": {
    "path": "/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "pattern": "muon_*"
  }
}
```

### 4. Read Sample Data

```json
{
  "name": "sample_tree",
  "arguments": {
    "path": "/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "size": 5,
    "branches": ["muon_pt", "muon_eta"]
  }
}
```

### 5. Compute Histogram

```json
{
  "name": "compute_histogram",
  "arguments": {
    "path": "/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "branch": "muon_pt",
    "bins": 50,
    "range": [0, 200],
    "selection": "muon_pt > 20"
  }
}
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for design details
- See [TOOL_SPECIFICATIONS.md](TOOL_SPECIFICATIONS.md) for complete API
- Check [examples/demo_interactions.md](examples/demo_interactions.md) for realistic usage patterns
- Explore advanced configuration options in [config.yaml](config.yaml)

## Troubleshooting

### "File not found" errors

- Verify paths in `config.yaml` are absolute
- Check `allowed_roots` includes the directory
- Ensure ROOT files exist: `ls /path/to/data/root_files/*.root`

### "Permission denied" or "Path not allowed"

- Paths must be under `security.allowed_roots`
- Use absolute paths, not relative
- Check file permissions: `ls -la /path/to/file.root`

### "Module not found: uproot"

```bash
pip install uproot awkward numpy
```

All required packages can be installed using `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### "Branch not found"

- Use `list_branches` to see available branches
- Check for typos in branch names
- ROOT branch names are case-sensitive

### Server won't start

```bash
# Check Python version
python --version  # Should be 3.10+

# Verify installation
pip show root-mcp

# Check config file syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Enable debug logging
ROOT_MCP_LOG_LEVEL=DEBUG root-mcp
```

## Performance Tips

1. **Start small**: Test with `sample_tree` before large reads
2. **Use selections**: Filter data at read time with `selection` parameter
3. **Check efficiency**: Use `apply_selection` before expensive operations
4. **Paginate**: Use `limit` and `offset` for large datasets
5. **Request only needed branches**: Don't read all branches if you only need a few

## Example Workflow

Here's a complete analysis workflow:

```python
# 1. Discover what's available
list_files() → ["sample_events.root"]

# 2. Understand the file
inspect_file("sample_events.root") → trees: ["events"], 10k entries

# 3. See what variables exist
list_branches("events") → muon_pt, muon_eta, electron_pt, jets, ...

# 4. Get a feel for the data
sample_tree(size=10) → See structure of events

# 5. Check if selection is reasonable
apply_selection("muon_pt > 25") → 4,523 / 10,000 pass (45%)

# 6. Analyze
compute_histogram("muon_pt", selection="muon_pt > 25") → Distribution

# 7. Export if needed
export_branches(format="parquet") → Save for ML/plotting
```

## Learning Resources

- **MCP Protocol**: https://modelcontextprotocol.io/
- **ROOT Documentation**: https://root.cern/doc/master/
- **uproot Tutorial**: https://masonproffitt.github.io/uproot-tutorial/
- **Awkward Array**: https://awkward-array.org/

## Getting Help

- **Issues**: https://github.com/MohamedElashri/root-mcp/issues
- **Discussions**: https://github.com/MohamedElashri/root-mcp/discussions
