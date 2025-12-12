# ROOT-MCP: Production-Grade MCP Server for CERN ROOT Files

A Model Context Protocol (MCP) server that provides AI models with safe, high-level access to CERN ROOT files and their contents (TFile, TDirectory, TTree, TBranch, histograms). Enables declarative, tool-based interaction with ROOT data without requiring users to write low-level C++ or PyROOT code.

## Features

- **Safe ROOT I/O**: Uses uproot (pure Python) to avoid segfaults and C++ crashes
- **LLM-Optimized**: Declarative tools designed for AI model composition
- **Production-Ready**: Resource limits, caching, validation, and comprehensive error handling
- **Physics-Friendly**: Built-in support for common HEP analysis patterns
- **Scalable**: Handles multi-GB files with streaming and pagination
- **Remote Access**: Support for XRootD, HTTP, and S3 (configurable)
- **Export Capabilities**: Convert data to JSON, CSV, or Parquet

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/root-mcp/root-mcp.git
cd root-mcp

# Install with pip
pip install -e .

# Or with optional XRootD support
pip install -e ".[xrootd]"
```

### Configuration

Create a `config.yaml`:

```yaml
resources:
  - name: "local_data"
    uri: "file:///data/root_files"
    description: "Local ROOT files"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/data/root_files"
  allowed_protocols: ["file"]
```

### Run Server

```bash
root-mcp
```

Or programmatically:

```python
from root_mcp import load_config
from root_mcp.server import ROOTMCPServer
import asyncio

config = load_config("config.yaml")
server = ROOTMCPServer(config)
asyncio.run(server.run())
```

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete design documentation.

### Key Components

```
MCP Client (AI Model)
    ↓
MCP Adapter Layer (Tool routing, validation)
    ↓
Logic Layer (Analysis operations, query planning)
    ↓
Core I/O Layer (File management, safe reading)
    ↓
Storage (Local files, XRootD, HTTP, S3)
```

### Safety Features

- **Pure Python I/O**: uproot eliminates C++ crashes
- **Resource Limits**: Configurable memory, row, and timeout limits
- **Path Validation**: Prevents directory traversal and unauthorized access
- **Error Guidance**: LLM-friendly error messages with suggestions

## Available Tools

See [TOOL_SPECIFICATIONS.md](docs/TOOL_SPECIFICATIONS.md) for complete API reference.

### Discovery Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `list_files` | List ROOT files in a resource | Find all files matching `run_*.root` |
| `inspect_file` | Get file structure | List trees, histograms, directories |
| `list_branches` | List TTree branches | Show branch types and stats |

### Data Access Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `read_branches` | Read branch data | Get muon pT and η with cuts |
| `sample_tree` | Quick data sample | Get first 100 entries |
| `get_branch_stats` | Compute statistics | Min/max/mean for branches |

### Analysis Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `compute_histogram` | 1D histogram | pT distribution with selection |
| `compute_histogram_2d` | 2D histogram | η vs φ correlation |
| `apply_selection` | Count entries | How many pass cuts? |
| `export_branches` | Export data | Save to Parquet for ML |

## Usage Examples

### Example 1: Interactive Data Exploration

```python
# AI Model's interaction with MCP server

# Step 1: Find available files
response = call_tool("list_files", {"resource": "local_data", "pattern": "*.root"})
# → Returns: ["run_12345.root", "run_12346.root"]

# Step 2: Inspect a file
response = call_tool("inspect_file", {"path": "/data/root_files/run_12345.root"})
# → Returns: Trees: ["events" (1M entries), "metadata"], Histograms: ["cutflow"]

# Step 3: Understand tree structure
response = call_tool("list_branches", {
    "path": "/data/root_files/run_12345.root",
    "tree": "events",
    "pattern": "muon_*"
})
# → Returns: muon_pt (float32[]), muon_eta (float32[]), muon_phi (float32[])

# Step 4: Sample data
response = call_tool("sample_tree", {
    "path": "/data/root_files/run_12345.root",
    "tree": "events",
    "size": 10,
    "branches": ["muon_pt", "muon_eta"]
})
# → Returns: 10 events with jagged arrays of muon data
```

### Example 2: Physics Analysis

```python
# Count high-pT muons
response = call_tool("apply_selection", {
    "path": "/data/root_files/run_12345.root",
    "tree": "events",
    "selection": "muon_pt > 25 && abs(muon_eta) < 2.4"
})
# → Returns: 45,230 / 1,000,000 entries (4.5% efficiency)

# Compute pT histogram
response = call_tool("compute_histogram", {
    "path": "/data/root_files/run_12345.root",
    "tree": "events",
    "branch": "muon_pt",
    "bins": 50,
    "range": [0, 200],
    "selection": "abs(muon_eta) < 2.4"
})
# → Returns: bin_edges, bin_counts, statistics
```

### Example 3: Data Export

```python
# Export filtered data for ML training
response = call_tool("export_branches", {
    "path": "/data/root_files/run_12345.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta", "muon_phi", "muon_charge"],
    "selection": "muon_pt > 20",
    "output_path": "/tmp/root_mcp_output/muons.parquet",
    "output_format": "parquet",
    "limit": 100000
})
# → Exports 45k entries to Parquet (1.2 MB)
```

## Configuration

### Resource Configuration

Resources define accessible file collections:

```yaml
resources:
  - name: "local_data"
    uri: "file:///data/root_files"
    description: "Local analysis files"
    allowed_patterns: ["*.root"]
    excluded_patterns: ["tmp*"]
    max_file_size_gb: 10

  - name: "xrootd_data"
    uri: "root://eosuser.cern.ch//eos/user/data"
    description: "CERN EOS storage"
    requires_auth: true
    auth_type: "kerberos"
```

### Security Configuration

```yaml
security:
  # Only allow access under these paths
  allowed_roots:
    - "/data/root_files"
    - "/tmp/root_mcp_output"

  # Allow remote access
  allow_remote: true

  # Allowed protocols
  allowed_protocols:
    - "file"
    - "root"  # XRootD
    - "https"
```

### Resource Limits

```yaml
limits:
  max_rows_per_call: 1_000_000
  max_memory_mb: 512
  max_file_handles: 100
  max_histogram_bins: 10_000
  operation_timeout_sec: 60
```

## Performance

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| `inspect_file` | <100ms | Metadata only |
| `list_branches` | <500ms | Tree structure |
| `read_branches` (10k rows) | <1s | With selection |
| `compute_histogram` (1M entries) | 2-5s | Full tree scan |
| `export_branches` (100k rows) | 5-30s | Depends on format |

### Optimization Tips

1. **Use selections early**: `apply_selection()` is fast and helps estimate costs
2. **Column pruning**: Only request needed branches
3. **Paginate large reads**: Use `limit` and `offset`
4. **Prefer histograms**: For summarization over full data reads
5. **Cache-friendly**: Repeated queries on same file are fast

## Development

### Project Structure

```
root-mcp/
├── src/root_mcp/
│   ├── server.py           # Main MCP server
│   ├── config.py           # Configuration management
│   ├── io/                 # I/O layer
│   │   ├── file_manager.py
│   │   ├── readers.py
│   │   └── validators.py
│   ├── analysis/           # Analysis operations
│   │   └── operations.py
│   └── tools/              # MCP tool handlers
│       ├── discovery.py
│       ├── data_access.py
│       └── analysis.py
├── config.yaml             # Configuration
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── TOOL_SPECIFICATIONS.md
│   ├── QUICKSTART.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── CONTRIBUTING.md
└── examples/               # Usage examples
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=root_mcp --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

## Extending ROOT-MCP

### Adding Custom Tools

```python
# In your plugin module
from root_mcp.tools.discovery import DiscoveryTools

class CustomTools(DiscoveryTools):
    def find_events_with_leptons(self, path: str, min_leptons: int = 2):
        """Custom analysis operation."""
        # Implementation
        pass

# Register in server
server.register_custom_tools(CustomTools)
```

### Experiment-Specific Conventions

```python
# plugins/atlas_conventions.py
class ATLASPlugin:
    def resolve_branch_alias(self, name: str) -> str:
        """Map ATLAS-specific names."""
        aliases = {
            "pt": "el_pt",  # Electrons
            "eta": "el_eta",
        }
        return aliases.get(name, name)
```

### Custom Export Formats

```python
# plugins/custom_exporter.py
@register_exporter("hdf5")
def export_to_hdf5(data, path):
    """Export to HDF5 format."""
    import h5py
    # Implementation
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

RUN pip install root-mcp

COPY config.yaml /app/config.yaml
WORKDIR /app

CMD ["root-mcp"]
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: root-mcp-server
spec:
  containers:
  - name: root-mcp
    image: root-mcp:latest
    volumeMounts:
    - name: data
      mountPath: /data
    resources:
      limits:
        memory: "2Gi"
        cpu: "2"
```

## Monitoring

Enable Prometheus metrics:

```yaml
monitoring:
  enabled: true
  prometheus_port: 9090
  metrics_path: "/metrics"
```

Metrics include:
- Request counts and latency
- Cache hit rates
- Memory usage
- Active file handles

## Troubleshooting

### Common Issues

**File Not Found**
```
Error: file_not_found
Solution: Use list_files() to see available files, check allowed_roots in config
```

**Branch Not Found**
```
Error: branch_not_found
Solution: Use list_branches() to see available branches, check for typos
```

**Selection Syntax Error**
```
Error: invalid_selection
Solution: Use ROOT syntax: 'pt > 20 && abs(eta) < 2.4' (not Python syntax)
```

**Limit Exceeded**
```
Error: limit_exceeded
Solution: Use apply_selection() first, or increase limit in config, or paginate
```

### Debugging

Enable debug logging:

```yaml
server:
  log_level: "DEBUG"
  log_format: "json"
```

View logs:
```bash
root-mcp 2>&1 | jq .  # For JSON logs
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use ROOT-MCP in your research, please cite:

```bibtex
@software{root_mcp,
  title = {ROOT-MCP: Production-Grade MCP Server for CERN ROOT Files},
  author = {ROOT-MCP Team},
  year = {2025},
  url = {https://github.com/root-mcp/root-mcp}
}
```

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [CERN ROOT](https://root.cern/)
- [uproot](https://github.com/scikit-hep/uproot5)
- [awkward-array](https://github.com/scikit-hep/awkward)

## Support

- **Issues**: https://github.com/root-mcp/root-mcp/issues
- **Discussions**: https://github.com/root-mcp/root-mcp/discussions
- **Documentation**: https://root-mcp.readthedocs.io

---

**Status**: Production Ready | **Version**: 1.0.0 | **Last Updated**: 2025-12-12
