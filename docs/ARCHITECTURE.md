# ROOT-MCP Architecture

## Overview

ROOT-MCP is a production-grade Model Context Protocol (MCP) server that enables AI assistants to interact with CERN `ROOT` files. It features a **dual-mode architecture** that balances simplicity and power, allowing users to choose between lightweight file operations and comprehensive physics analysis capabilities.

## Design Philosophy

1. **Zero-Config First**: Start with `--data-path` or `ROOT_MCP_DATA_PATH` — no YAML file required
2. **Configuration-Driven**: Full control available through `config.yaml` for advanced use cases
3. **Lazy Loading**: Components loaded only when needed for memory efficiency
4. **Runtime Flexibility**: Switch between modes without server restart
5. **Security First**: All file operations validated through security checks; permissive-by-default for local use
6. **Pure Python Core**: Uses `uproot` for crash-resistant ROOT file access without requiring a ROOT installation
7. **Optional Native ROOT**: When a ROOT installation is available, additional tools unlock automatically

## Architecture Tiers

### Core Mode
**Purpose**: Lightweight file operations and basic statistics
**Dependencies**: `uproot`, `awkward`, `numpy`, `pandas`, `mcp`
**Use Cases**: File inspection, data reading, basic statistics, data export

### Extended Mode
**Purpose**: Full physics analysis capabilities
**Dependencies**: Core dependencies + `scipy`, `matplotlib`
**Use Cases**: Histogram fitting, kinematics calculations, correlations, plotting

### Native ROOT (Optional)
**Purpose**: Execute arbitrary PyROOT/C++ code; RDataFrame; ROOT macros
**Dependencies**: Extended mode + a working ROOT/PyROOT installation
**Use Cases**: Custom PyROOT scripts, RDataFrame event loops, C++ macro execution, RooFit
**Enable**: Set `features.enable_root: true` in `config.yaml`

### Mode Selection

Controlled via `config.yaml`:
```yaml
server:
  mode: "extended"  # or "core"

features:
  enable_root: true  # optional — unlocks ROOT native tools
```

Runtime switching available via `switch_mode` tool without restart. Native ROOT tools appear automatically when both `enable_root: true` and a ROOT installation are detected.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Assistant (Claude)                │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol (JSON-RPC)
┌────────────────────┴────────────────────────────────────┐
│                  ROOT-MCP Server                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │            Mode-Aware Dispatcher                 │  │
│  │  • Tool routing based on current mode            │  │
│  │  • Dynamic component loading/unloading           │  │
│  │  • Mode validation and switching                 │  │
│  └────────────────┬─────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────┴─────────────────────────────────┐  │
│  │         Core Components (Always Loaded)          │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ I/O Layer                                  │  │  │
│  │  │  • FileManager: File caching & lifecycle  │  │  │
│  │  │  • TreeReader: TTree data reading         │  │  │
│  │  │  • HistogramReader: Histogram reading     │  │  │
│  │  │  • PathValidator: Security checks         │  │  │
│  │  │  • DataExporter: JSON/CSV/Parquet export  │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Operations Layer                           │  │  │
│  │  │  • BasicStatistics: min/max/mean/std      │  │  │
│  │  │  • Basic histograms (no fitting)          │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Core Tools                                 │  │  │
│  │  │  • DiscoveryTools: File/tree inspection   │  │  │
│  │  │  • DataAccessTools: Branch reading        │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────┴─────────────────────────────────┐  │
│  │    Extended Components (Lazy Loaded)             │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Analysis Layer                             │  │  │
│  │  │  • HistogramOperations: 1D/2D/Profile     │  │  │
│  │  │  • KinematicsOperations: 4-vectors, mass  │  │  │
│  │  │  • CorrelationAnalysis: Stats correlations│  │  │
│  │  │  • Fitting: 1D/2D model fitting           │  │  │
│  │  │  • Plotting: Visualization generation     │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Extended Tools                             │  │  │
│  │  │  • AnalysisTools: High-level analysis     │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────┴─────────────────────────────────┐  │
│  │  Native ROOT Components (Optional, Subprocess)  │  │
│  │  Requires: ROOT installation + enable_root: true│  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ ROOT Native Layer                          │  │  │
│  │  │  • RootAvailability: version/feature probe │  │  │
│  │  │  • RootExecutor: subprocess runner        │  │  │
│  │  │  • ASTSandbox: code safety validation     │  │  │
│  │  │  • Templates: RDataFrame/RooFit boilerplat│  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Native ROOT Tools                          │  │  │
│  │  │  • run_root_code: arbitrary PyROOT code   │  │  │
│  │  │  • run_rdataframe: RDataFrame histograms  │  │  │
│  │  │  • run_root_macro: C++ macro execution    │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
│                   │                                     │
│  ┌────────────────┴─────────────────────────────────┐  │
│  │         Common Utilities                         │  │
│  │  • LRUCache: Generic caching                    │  │
│  │  • Error types: Typed exceptions                │  │
│  │  • Utils: Path handling, formatting             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                  Storage Layer                          │
│  • Local files (file://)                               │
│  • Remote files (root://, http://, https://)           │
│  • XRootD protocol support (optional)                  │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/root_mcp/
├── core/                    # Core mode components
│   ├── io/                  # File I/O operations
│   │   ├── file_manager.py  # File caching and lifecycle
│   │   ├── readers.py       # TTree and histogram readers
│   │   ├── validators.py    # Security validation
│   │   └── exporters.py     # Data export (JSON/CSV/Parquet)
│   ├── operations/          # Basic operations
│   │   └── basic_stats.py   # Statistics without scipy
│   └── tools/               # Core MCP tools
│       ├── discovery.py     # File/tree inspection
│       └── data_access.py   # Branch reading
├── extended/                # Extended mode components
│   ├── analysis/            # Advanced analysis
│   │   ├── histograms.py    # 1D/2D/Profile histograms
│   │   ├── kinematics.py    # 4-vector calculations
│   │   ├── correlations.py  # Statistical correlations
│   │   ├── fitting.py       # Model fitting (1D/2D)
│   │   ├── plotting.py      # Visualization
│   │   ├── operations.py    # High-level operations
│   │   └── expression.py    # Expression evaluation
│   ├── root_native/         # Optional native ROOT integration
│   │   ├── executor.py      # Subprocess executor with timeout
│   │   ├── sandbox.py       # AST-based code safety checks
│   │   └── templates.py     # Code templates (RDataFrame, RooFit…)
│   └── tools/               # Extended + native ROOT MCP tools
│       ├── analysis.py      # Analysis tool handlers
│       ├── plotting.py      # Plotting tool handlers
│       └── root_native.py   # run_root_code/rdataframe/macro handlers
├── common/                  # Shared utilities
│   ├── cache.py             # LRU cache implementation
│   ├── errors.py            # Error types
│   ├── root_availability.py # ROOT detection & version probing
│   └── utils.py             # Utility functions
├── config.py                # Configuration management
└── server.py                # Mode-aware MCP server + CLI
```

## Component Details

### Core Components

#### FileManager
- **Purpose**: Centralized file handle management
- **Features**:
  - LRU cache for open file handles (configurable size)
  - Protocol support: file://, root://, http://, https://
  - Connection pooling for remote files
  - Automatic cleanup and resource management
- **Security**: All paths validated through PathValidator

#### TreeReader
- **Purpose**: High-level TTree data access
- **Features**:
  - Columnar reading with awkward arrays
  - Streaming support for large files (chunked reading)
  - Selection expressions (cuts)
  - Branch sampling and statistics
- **Performance**: Lazy loading, column pruning

#### PathValidator
- **Purpose**: Security validation for all file operations
- **Features**:
  - Allowed root directory enforcement (permissive when list is empty)
  - Path traversal prevention
  - Protocol auto-elevation from resource URI declarations
  - Write operation validation (input ≠ output)
  - Audit logging for write operations

### Native ROOT Components

#### RootAvailability
- **Purpose**: Detect ROOT installation and probe version/feature flags
- **Features**: Subprocess-based detection; returns version string, RDataFrame support, RooFit, TMVA flags
- **Resilience**: Server starts and works fully if ROOT is absent

#### RootExecutor
- **Purpose**: Run PyROOT code in an isolated subprocess
- **Features**:
  - Configurable execution timeout
  - Structured stdout/stderr capture
  - Working directory isolation
  - Non-blocking process management

#### ASTSandbox
- **Purpose**: Validate Python/PyROOT code safety before execution
- **Checks**: Blocks `os`, `sys`, `subprocess`, `socket` imports; dangerous builtins (`exec`, `eval`, `__import__`); unsafe attribute access patterns
- **Policy**: Allow-list approach — only physics-relevant modules permitted

#### Templates
- **Purpose**: Pre-built code templates for common ROOT patterns
- **Available**: RDataFrame histogram, TCanvas plotting, RooFit mass fit, file writing, C++ macro wrapper, batch processing

#### DataExporter
- **Purpose**: Export data to standard formats
- **Formats**: JSON, CSV, Parquet
- **Features**: Compression support, streaming for large datasets

#### BasicStatistics
- **Purpose**: Statistics without scipy dependency
- **Operations**: min, max, mean, std, median, percentiles
- **Features**: Basic 1D histograms (no fitting)

### Extended Components

#### HistogramOperations
- **Purpose**: Advanced histogram creation
- **Features**:
  - 1D histograms with error propagation
  - 2D histograms with proper weighting
  - Profile histograms (mean of Y vs X)
  - Configurable bin limits

#### KinematicsOperations
- **Purpose**: Particle physics calculations
- **Features**:
  - Invariant mass from 4-vectors
  - Dalitz plot variables
  - Lorentz boost to CM frame

#### CorrelationAnalysis
- **Purpose**: Statistical correlation analysis
- **Features**:
  - Pearson correlation
  - Spearman rank correlation
  - Correlation/covariance matrices
  - Mutual information
  - Significance testing

#### Fitting
- **Purpose**: Model fitting to histograms
- **Models**: Gaussian, exponential, polynomial, Crystal Ball, 2D Gaussian
- **Features**:
  - Fixed parameter support
  - Bounds constraints
  - Chi-square calculation
  - Error propagation

## Tool Categories

### Core Tools (Always Available)

| Tool | Description | Mode |
|------|-------------|------|
| `list_files` | List ROOT files in resource | Core |
| `inspect_file` | Get file structure and metadata | Core |
| `list_branches` | List branches in TTree | Core |
| `validate_file` | Check file integrity | Core |
| `read_branches` | Read branch data | Core |
| `get_branch_stats` | Compute basic statistics | Core |
| `export_data` | Export to JSON/CSV/Parquet | Core |
| `switch_mode` | Switch between core/extended | Core |
| `get_server_info` | Get server capabilities | Core |

### Extended Tools (Extended Mode Only)

| Tool | Description | Requires |
|------|-------------|----------|
| `compute_histogram` | Create 1D histogram with fitting | Extended |
| `compute_histogram_2d` | Create 2D histogram | Extended |
| `fit_histogram` | Fit model to histogram | Extended |
| `compute_invariant_mass` | Calculate invariant mass | Extended |
| `compute_correlation` | Correlation analysis | Extended |
| `histogram_arithmetic` | Histogram arithmetic operations | Extended |
| `plot_histogram_1d` | Create 1D plot | Extended |
| `plot_histogram_2d` | Create 2D plot | Extended |

## Configuration

### Merge Priority

Settings are applied from four sources in ascending priority (later wins):

```
1. Built-in Pydantic defaults          (always lowest)
2. YAML config file                    (ROOT_MCP_CONFIG / --config / auto-discovery)
3. ROOT_MCP_* environment variables    (override everything from YAML)
4. CLI flags                           (always highest)
```

This means every field in `config.yaml` can be overridden in a container simply by setting an
environment variable, and a user can always override that with a CLI flag.  YAML users
see no behaviour change unless they also set conflicting env vars.

### Zero-Config Quick Start

No config file is required. Pass a data directory at invocation time:

```bash
root-mcp --data-path /path/to/data
```

Or via environment variables (fully env-driven — useful for containers):

```bash
export ROOT_MCP_DATA_PATH=/data
export ROOT_MCP_MODE=extended
export ROOT_MCP_EXPORT_PATH=/exports
export ROOT_MCP_ENABLE_ROOT=1
root-mcp
```

Generate a starter config pre-filled with the current directory:

```bash
root-mcp init --permissive
```

### `apply_env_overrides` / `apply_cli_overrides`

Two functions in `config.py` implement the merge:

```python
apply_env_overrides(config)     # reads all ROOT_MCP_* vars, mutates config in-place
apply_cli_overrides(config, args)  # applies parsed argparse.Namespace, in-place
```

Both are called in `main()` after `load_config()` and `apply_data_paths()` — env vars
first, then CLI flags, so CLI always wins.  Log level is the exception: it is applied
before `load_config()` so that config-loading messages also respect the requested verbosity.

### Full Configuration Structure

```yaml
# QUICK START
server:
  mode: "extended"  # "core" or "extended"

resources:
  - name: "my_data"
    uri: "file:///path/to/data"
    allowed_patterns: ["*.root"]

features:
  enable_root: false    # set true to unlock run_root_code / run_rdataframe / run_root_macro
  enable_export: true

# ADVANCED
core:
  cache:
    enabled: true
    file_cache_size: 50
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
  fitting_max_iterations: 10_000

security:
  allowed_roots: []   # empty = permissive (any local path); add explicit paths to restrict
  allowed_protocols: ["file", "root", "http", "https"]

output:
  export_base_path: "/path/to/exports"
  allowed_formats: ["json", "csv", "parquet"]

root_native:          # only relevant when enable_root: true
  execution_timeout: 60
  working_directory: "/tmp/root_mcp_native"
```

## Security Model

### Path Validation
1. **Allowed Roots**: When `security.allowed_roots` is non-empty, all file paths must be under those roots. An **empty list** (the default) permits access to any OS-readable path — permissive mode for local development.
2. **Protocol Validation**: Only allowed protocols can be used. Protocols are auto-elevated when a `resources[].uri` declares a remote scheme (e.g. `root://`, `https://`).
3. **Path Traversal Prevention**: `..` and symlinks validated
4. **Write Protection**: Input and output paths must differ
5. **Code Sandbox**: Native ROOT code execution validated via AST analysis before subprocess launch — blocks dangerous imports, builtins, and attribute access

### Resource Limits
1. **Row Limits**: Maximum rows per read operation
2. **Export Limits**: Maximum rows for export operations
3. **Bin Limits**: Maximum histogram bins (1D/2D)
4. **Cache Limits**: Maximum open file handles

### Audit Trail
- All write operations logged
- Mode switches logged
- Failed validation attempts logged

## Performance Considerations

### Memory Management
- **Lazy Loading**: Extended components loaded only when needed
- **File Caching**: LRU cache for file handles (configurable)
- **Streaming**: Chunked reading for large files
- **Column Pruning**: Read only requested branches

### Optimization Strategies
1. **Predicate Pushdown**: Apply selections during read
2. **Chunk Size Tuning**: Configurable chunk sizes for streaming
3. **Connection Pooling**: Reuse connections for remote files
4. **Compression**: Support for compressed exports

## Error Handling

### Error Types
- `ROOTMCPError`: Base exception
- `SecurityError`: Security constraint violations
- `ValidationError`: Input validation failures
- `FileOperationError`: File I/O errors
- `AnalysisError`: Analysis operation failures

### Graceful Degradation
- Extended mode falls back to core if dependencies missing
- Clear error messages with hints for resolution
- Mode-specific error handling

## Future Considerations

### Potential Enhancements
1. **Caching Layer**: Redis/memcached for distributed caching
2. **Parallel Processing**: Multi-file parallel operations
3. **Query Optimization**: Advanced query planning
4. **Additional Formats**: ROOT file writing (new files only)
5. **Plugin System**: Extensible analysis modules

### Non-Goals
- Modification of existing ROOT files
- GUI/web interface
- Full RooFit model library (templates cover the common cases)

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uproot Documentation](https://uproot.readthedocs.io/)
- [awkward Documentation](https://awkward-array.org/)
- [CERN ROOT](https://root.cern/)
