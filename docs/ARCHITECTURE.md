# ROOT-MCP Server Architecture

## Executive Summary

The ROOT-MCP server provides AI models with safe, high-level access to CERN ROOT files through the Model Context Protocol. It enables declarative, tool-based interaction with ROOT data structures (TFile, TDirectory, TTree, TBranch, histograms) without requiring users to write low-level PyROOT or C++ code.

## 1. Goals and Use Cases

### Primary Goals

1. **Safe Data Access**: Provide crash-resistant access to ROOT files, avoiding segfaults and undefined behavior common with C++ ROOT bindings
2. **LLM-Friendly Interface**: Expose declarative tools that AI models can compose to perform complex analyses
3. **Performance at Scale**: Handle multi-GB files and remote storage (XRootD) efficiently with streaming and pagination
4. **Analysis Flexibility**: Support interactive exploration and repeatable physics workflows

### User Stories

**US-1: Interactive Exploration**
> "An AI assistant helps a physicist explore a new ROOT file: list its structure, inspect a few branches, understand the data schema, then extract a subset for analysis."

**US-2: Physics Analysis**
> "An AI answers: 'What is the distribution of transverse momentum for muons in this TTree, with pT > 20 GeV and |η| < 2.4?' using only MCP tool calls."

**US-3: Data Discovery**
> "A researcher asks: 'Which ROOT files contain electron candidates with E_T > 100 GeV?' The AI searches across registered datasets and returns matching files with statistics."

**US-4: Comparative Analysis**
> "Compare the invariant mass distributions between two different datasets (signal vs background) and identify differences."

**US-5: Derived Outputs**
> "Extract a filtered subset of data from a 50 GB ROOT file, compute derived quantities, and export to Parquet for ML training."

## 2. Technology Stack

### Core Dependencies

- **Python 3.10+**: Runtime environment
- **uproot 5.x**: Pure Python ROOT I/O library (avoids C++ crashes)
- **awkward 2.x**: Columnar data handling for jagged arrays
- **numpy/pandas**: Numerical operations and data manipulation
- **MCP Python SDK**: Protocol implementation
- **pydantic**: Schema validation and configuration
- **aiofiles**: Async file I/O
- **fsspec**: Unified filesystem interface (local, XRootD, S3)

### Why uproot over PyROOT?

1. **Safety**: Pure Python implementation eliminates segfaults from C++ bindings
2. **Performance**: Optimized columnar reading, lazy loading
3. **Portability**: No ROOT installation required
4. **Modern APIs**: Integrates naturally with Python data ecosystem
5. **Remote I/O**: Built-in support for XRootD, HTTP, S3

### Constraints and Limitations

- **Write Operations**: Limited write support (uproot can write simple ROOT files but not complex objects)
- **Object Types**: Focus on common types (TTree, histograms); rare/exotic objects require fallback or extensions
- **Version Compatibility**: uproot supports ROOT files v4+ (covers most HEP use cases)

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client (AI Model)                │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol (JSON-RPC)
┌────────────────────┴────────────────────────────────────┐
│                  MCP Adapter Layer                      │
│  ┌──────────────┬──────────────┬────────────────────┐  │
│  │ Tool Handler │ Resource API │ Prompts/Metadata  │  │
│  │ (routing &   │ (file roots) │ (guidance for AI) │  │
│  │ validation)  │              │                    │  │
│  └──────┬───────┴──────┬───────┴─────────┬──────────┘  │
└─────────┼──────────────┼─────────────────┼─────────────┘
          │              │                 │
┌─────────┴──────────────┴─────────────────┴─────────────┐
│                  Logic Layer                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Analysis Operations                                │ │
│  │ - describe_file()      - read_branch_slice()      │ │
│  │ - list_trees()         - compute_histogram()      │ │
│  │ - list_branches()      - apply_selection()        │ │
│  │ - get_statistics()     - project_2d()             │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Query Planner & Optimizer                          │ │
│  │ - Expression parsing   - Chunk size optimization  │ │
│  │ - Column pruning       - Predicate pushdown       │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│                  Core I/O Layer                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ File Manager                                       │ │
│  │ - Open/close ROOT files (cached handles)          │ │
│  │ - Protocol support: file://, root://, http://     │ │
│  │ - Connection pooling for remote files             │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Object Reader                                      │ │
│  │ - TTree streaming (chunked iteration)             │ │
│  │ - TBranch lazy loading                            │ │
│  │ - Histogram reading (TH1, TH2, TH3, THn)          │ │
│  │ - TGraph, TProfile support                        │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Safety & Resource Management                       │ │
│  │ - Memory limits per operation                     │ │
│  │ - Timeout enforcement                             │ │
│  │ - Input validation & sanitization                 │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│         Storage Backends                                │
│  [Local Files]  [XRootD]  [HTTP]  [S3/Object Storage]  │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### MCP Adapter Layer
- **Tool Handlers**: Route MCP tool requests to logic layer, validate inputs, serialize outputs
- **Resource API**: Expose file roots and available datasets to AI models
- **Prompts**: Provide system prompts and tool usage guidance
- **Error Translation**: Convert internal exceptions to LLM-friendly error messages

#### Logic Layer
- **Analysis Operations**: High-level physics operations (histogramming, cuts, projections)
- **Query Planner**: Optimize data access patterns (column pruning, predicate pushdown)
- **Business Logic**: HEP domain knowledge (units, conventions, common patterns)

#### Core I/O Layer
- **File Manager**: Handle file lifecycle, caching, connection pooling
- **Object Reader**: Safe, efficient reading of ROOT objects
- **Resource Management**: Enforce memory/time/bandwidth limits
- **Safety Guards**: Validate all inputs, catch errors, prevent crashes

## 4. MCP Tool Design

### Design Principles

1. **Composability**: Tools should be atomic operations that can be chained
2. **Predictability**: Consistent input/output schemas across tools
3. **Self-Documenting**: Rich descriptions and examples in tool schemas
4. **Error-Guiding**: Errors should help LLMs refine their next call
5. **Safety-First**: All operations bounded, validated, and timeout-protected

### Tool Categories

#### Discovery Tools (Read-Only, Fast)
- `list_files`: Enumerate accessible ROOT files
- `inspect_file`: Get high-level metadata
- `list_trees`: List all TTrees in a file
- `list_branches`: List branches with types and stats

#### Data Access Tools (Read, Potentially Slow)
- `read_branches`: Extract branch data with filtering and pagination
- `sample_tree`: Get a small random/sequential sample
- `get_branch_stats`: Compute min/max/mean/std for branches

#### Analysis Tools (Compute, Potentially Slow)
- `compute_histogram`: 1D histogram with selection
- `compute_histogram_2d`: 2D histogram/scatter
- `compute_profile`: TProfile-like mean vs binned variable
- `apply_selection`: Count entries passing a cut

#### Export Tools (Write, Restricted)
- `export_branches`: Extract filtered data to JSON/CSV/Parquet
- `create_derived_file`: Write a new ROOT file with subset

### Tool Specifications

Each tool is specified with:
- **Name**: Clear, verb-based identifier
- **Description**: 2-3 sentence summary for LLMs
- **Input Schema**: Pydantic model with validation
- **Output Schema**: Structured response format
- **Examples**: 2-3 realistic usage scenarios
- **Error Conditions**: Common failures and how to resolve
- **Performance Hints**: Expected runtime, memory usage
- **Safety Limits**: Max rows, max memory, timeout

## 5. Safety, Robustness, and Performance

### Memory Safety

**Crash Prevention**
- ✅ Use uproot (pure Python, no C++ crashes)
- ✅ Validate all file paths and object names before access
- ✅ Wrap all I/O operations in try-except with specific error handling
- ✅ Use context managers for file handles (automatic cleanup)

**Memory Management**
```python
# Chunked iteration prevents OOM on large TTrees
for chunk in tree.iterate(step_size=10_000, filter_name=branches):
    process_chunk(chunk)  # Process 10k entries at a time
    if memory_used() > MAX_MEMORY:
        yield partial_results()
        break
```

**Resource Limits (Configurable)**
- `MAX_ROWS_PER_CALL`: 1,000,000 (default)
- `MAX_MEMORY_MB`: 512 (per operation)
- `MAX_FILE_HANDLES`: 100 (concurrent)
- `MAX_HISTOGRAM_BINS`: 10,000 (per dimension)
- `OPERATION_TIMEOUT_SEC`: 60 (default)

### Performance Optimizations

**1. Lazy Loading**
```python
# Only read requested branches, not entire tree
tree.arrays(["pt", "eta"], library="ak", how="zip")
```

**2. Predicate Pushdown**
```python
# Apply cuts during reading (uproot optimization)
tree.arrays(filter_name=branches, cut="pt > 20")
```

**3. Chunk Streaming**
```python
# For large results, stream chunks back to client
async def read_large_dataset():
    for i, chunk in enumerate(tree.iterate(step_size=50_000)):
        yield {
            "chunk": i,
            "data": chunk.to_list(),
            "more": has_more_chunks()
        }
```

**4. Connection Pooling**
```python
# Reuse remote file connections
class FileCache:
    def __init__(self, max_size=50):
        self._cache = LRU(max_size)

    def get(self, path):
        if path not in self._cache:
            self._cache[path] = uproot.open(path)
        return self._cache[path]
```

**5. Metadata Caching**
```python
# Cache file structure (trees, branches) for fast repeat access
@lru_cache(maxsize=200)
def get_tree_metadata(file_path, tree_name):
    with uproot.open(file_path) as f:
        tree = f[tree_name]
        return {
            "num_entries": tree.num_entries,
            "branches": tree.keys(),
            "types": tree.typenames()
        }
```

### Error Handling Strategy

**Error Categories**
1. **Validation Errors**: Invalid parameters → 400-style errors with guidance
2. **Not Found**: Missing file/tree/branch → 404-style with suggestions
3. **Resource Limits**: Timeout/OOM → 429-style with retry hints
4. **I/O Errors**: Network failure, corrupt file → 500-style with diagnostics
5. **Computation Errors**: Invalid expression → 400-style with syntax help

**LLM-Friendly Error Messages**
```python
# Bad (technical)
"KeyError: 'muon_pt' not found in TTree"

# Good (actionable)
{
    "error": "branch_not_found",
    "message": "Branch 'muon_pt' does not exist in tree 'events'",
    "suggestion": "Available branches: ['pt', 'eta', 'phi', 'charge']. Did you mean 'pt'?",
    "retry_with": {"branch": "pt"}
}
```

### Timeout and Cancellation

```python
async def read_with_timeout(tree, branches, timeout_sec):
    """Read with enforced timeout."""
    async with asyncio.timeout(timeout_sec):
        result = await asyncio.to_thread(
            tree.arrays,
            filter_name=branches,
            library="ak"
        )
    return result
```

## 6. File Discovery and Security

### MCP Resources (Roots)

Resources define accessible file collections:

```python
# Configuration example
resources:
  - name: "local_data"
    uri: "file:///data/root_files"
    description: "Local ROOT files from run 2024A"
    allowed_patterns: ["*.root"]
    max_file_size_gb: 10

  - name: "xrootd_atlas"
    uri: "root://eosuser.cern.ch//eos/atlas/data"
    description: "ATLAS data on EOS"
    allowed_patterns: ["user.*/*.root"]
    requires_auth: true

  - name: "public_datasets"
    uri: "https://opendata.cern.ch/record/12345/files"
    description: "Open data portal samples"
    allowed_patterns: ["*.root"]
```

### Security Model

**Path Validation**
```python
def validate_path(path: str, config: Config) -> Path:
    """Ensure path is within allowed roots."""
    resolved = Path(path).resolve()

    for root in config.allowed_roots:
        root_path = Path(root).resolve()
        try:
            resolved.relative_to(root_path)
            return resolved  # Path is under allowed root
        except ValueError:
            continue

    raise SecurityError(
        f"Path '{path}' is not under any allowed root. "
        f"Allowed roots: {config.allowed_roots}"
    )
```

**Resource Quotas**
```python
class UserQuota:
    max_concurrent_operations: int = 5
    max_memory_mb: int = 2048
    max_bandwidth_mbps: int = 100
    rate_limit_per_minute: int = 60
```

**Authentication Hooks**
```python
# For remote storage requiring credentials
class XRootDAuthenticator:
    def get_credentials(self, uri: str) -> dict:
        # Read from env vars, credential files, or OAuth
        return {
            "token": os.getenv("XROOTD_TOKEN"),
            "cert": Path.home() / ".globus" / "usercert.pem"
        }
```

### File Reference Format

Tools accept files in multiple formats:
- **Absolute path**: `/data/run_12345.root`
- **Resource-relative**: `local_data://run_12345.root`
- **Dataset alias**: `@atlas_2024/signal` (configured mapping)
- **XRootD URI**: `root://server.cern.ch//path/to/file.root`

## 7. LLM Interaction Patterns

### Multi-Step Discovery Pattern

```
[Step 1: Discover Available Files]
LLM → list_files(resource="local_data")
← ["run_12345.root", "run_12346.root"]

[Step 2: Inspect File Structure]
LLM → inspect_file(path="local_data://run_12345.root")
← {
    "trees": ["events", "metadata"],
    "histograms": ["cutflow"],
    "size_mb": 450,
    "num_entries": {"events": 1_000_000}
}

[Step 3: Understand Tree Schema]
LLM → list_branches(path="...", tree="events", limit=20)
← {
    "branches": [
        {"name": "muon_pt", "type": "float32[]", "description": "Muon pT (GeV)"},
        {"name": "muon_eta", "type": "float32[]"},
        ...
    ],
    "total_branches": 150,
    "suggestion": "Use pattern='muon_*' to see all muon variables"
}

[Step 4: Sample Data]
LLM → read_branches(
    path="...",
    tree="events",
    branches=["muon_pt", "muon_eta"],
    limit=10
)
← {
    "data": [
        {"muon_pt": [25.3, 18.9], "muon_eta": [-0.5, 1.2]},
        {"muon_pt": [102.1], "muon_eta": [0.1]},
        ...
    ],
    "entries_returned": 10,
    "entries_scanned": 10,
    "hint": "Data has variable-length arrays (jagged). Use flatten=true for flat output."
}

[Step 5: Apply Physics Cut and Histogram]
LLM → compute_histogram(
    path="...",
    tree="events",
    branch="muon_pt",
    bins=50,
    range=[0, 200],
    selection="muon_pt > 20 && abs(muon_eta) < 2.4"
)
← {
    "bin_edges": [0, 4, 8, ..., 200],
    "bin_counts": [0, 5, 120, ..., 3],
    "entries_selected": 45_000,
    "entries_total": 1_000_000,
    "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
}
```

### Error Recovery Pattern

```
LLM → read_branches(path="...", tree="events", branches=["missing_var"])
← {
    "error": "branch_not_found",
    "message": "Branch 'missing_var' not found in tree 'events'",
    "available_branches": ["muon_pt", "muon_eta", ...],
    "suggestion": "List branches with list_branches() or use pattern matching"
}

[LLM corrects request]
LLM → list_branches(path="...", tree="events", pattern="*miss*")
← {
    "branches": ["missing_et", "missing_et_phi"],
    "hint": "Found 2 branches matching '*miss*'"
}
```

### Response Metadata for Guidance

Every response includes:
```python
{
    "data": { ... },  # Primary result
    "metadata": {
        "operation": "read_branches",
        "execution_time_ms": 450,
        "entries_scanned": 100_000,
        "memory_used_mb": 45,
        "truncated": false
    },
    "next_actions": [
        "Compute histogram with compute_histogram()",
        "Apply selection with selection='pt > 30'",
        "Export data with export_branches(format='parquet')"
    ]
}
```

## 8. Extensibility

### Extension Points

**1. Custom Analysis Tools**
```python
# plugins/jet_clustering.py
@register_tool
def cluster_jets(
    path: str,
    tree: str,
    algorithm: str = "anti_kt",
    radius: float = 0.4
):
    """Run jet clustering algorithm on particle candidates."""
    # Implementation using fastjet or similar
    ...
```

**2. Experiment-Specific Conventions**
```python
# plugins/atlas_conventions.py
class ATLASPlugin(ExperimentPlugin):
    def resolve_branch_alias(self, name: str) -> str:
        """Map common ATLAS names to actual branch names."""
        aliases = {
            "pt": "el_pt",  # ATLAS uses el_pt, mu_pt, etc.
            "eta": "el_eta",
        }
        return aliases.get(name, name)

    def get_standard_selections(self) -> dict:
        """Provide common ATLAS selections."""
        return {
            "good_electron": "el_pt > 25 && abs(el_eta) < 2.47",
            "good_muon": "mu_pt > 20 && abs(mu_eta) < 2.5"
        }
```

**3. Output Format Plugins**
```python
# plugins/arrow_export.py
@register_exporter("arrow")
def export_to_arrow(data: ak.Array, path: str):
    """Export to Apache Arrow IPC format."""
    import pyarrow as pa
    table = ak.to_arrow_table(data)
    with pa.OSFile(path, 'wb') as f:
        with pa.RecordBatchFileWriter(f, table.schema) as writer:
            writer.write_table(table)
```

**4. Remote Storage Backends**
```python
# plugins/eos_backend.py
class EOSBackend(StorageBackend):
    """CERN EOS-specific optimizations."""

    def open(self, path: str):
        # Use EOS-optimized reading
        return uproot.open(
            path,
            **{"timeout": 300, "max_workers": 4}
        )
```

### Plugin Discovery

```python
# config.yaml
plugins:
  - name: "atlas_conventions"
    module: "plugins.atlas_conventions"
    enabled: true

  - name: "jet_clustering"
    module: "plugins.jet_clustering"
    enabled: false  # Enable when needed
```

## 9. Deployment Considerations

### Production Checklist

- [ ] **Logging**: Structured logging (JSON) with request IDs, timing, errors
- [ ] **Monitoring**: Prometheus metrics (request rate, latency, errors, memory)
- [ ] **Health Checks**: `/health` endpoint for orchestration
- [ ] **Configuration**: Environment-based config with validation
- [ ] **Secrets Management**: Secure credential handling (Vault, AWS Secrets Manager)
- [ ] **Rate Limiting**: Per-user quotas and global rate limits
- [ ] **Graceful Shutdown**: Close file handles, finish in-flight requests
- [ ] **Documentation**: OpenAPI/AsyncAPI spec generation from tool schemas

### Container Deployment

```dockerfile
FROM python:3.11-slim

# Install uproot and dependencies
RUN pip install uproot awkward numpy pandas mcp pydantic

COPY src/ /app/src/
COPY config.yaml /app/config.yaml

WORKDIR /app
EXPOSE 8000

CMD ["python", "-m", "root_mcp.server"]
```

### Performance Targets

- **File Inspection**: < 100ms for cached metadata
- **Branch List**: < 500ms for files with <1000 branches
- **Small Reads** (<10k rows): < 1s
- **Histograms**: < 5s for 1M entries, simple selection
- **Large Reads** (100k-1M rows): < 30s with streaming

## 10. Future Enhancements

### Planned Features

1. **Parallel Query Execution**: Distribute histogram computation across multiple workers
2. **Advanced Selections**: Support for complex expressions (ROOT RDataFrame-like)
3. **Caching Layer**: Redis/Memcached for frequent queries
4. **Incremental Processing**: Process new data as files are updated
5. **Derived Columns**: Register user-defined functions for on-the-fly computation
6. **Systematic Variations**: Tools for uncertainty propagation in HEP analyses
7. **ML Integration**: Export directly to TensorFlow/PyTorch datasets
8. **Visualization Hints**: Suggest plot types and binning based on data

### Research Directions

- **Query Optimization**: ML-based query planning from LLM intent
- **Natural Language Selections**: Parse "high momentum muons" → `pt > 50`
- **Autonomous Analysis**: Multi-step agent workflows for standard analyses
- **Collaboration**: Multi-user access with shared workspaces

---

**Document Version**: 1.0
**Last Updated**: 2025-12-12
**Authors**: Mohamed Elashri
