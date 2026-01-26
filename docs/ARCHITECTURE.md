# ROOT-MCP Architecture

## Overview

ROOT-MCP is a production-grade Model Context Protocol (MCP) server that enables AI assistants to interact with CERN `ROOT` files. It features a **dual-mode architecture** that balances simplicity and power, allowing users to choose between lightweight file operations and comprehensive physics analysis capabilities.

## Design Philosophy

1. **Configuration-Driven**: Mode selection and behavior controlled through `config.yaml`
2. **Lazy Loading**: Components loaded only when needed for memory efficiency
3. **Runtime Flexibility**: Switch between modes without server restart
4. **Security First**: All file operations validated through security checks
5. **Pure Python**: Uses `uproot` for crash-resistant `ROOT` file access

## Dual-Mode Architecture

### Core Mode
**Purpose**: Lightweight file operations and basic statistics
**Dependencies**: `uproot`, `awkward`, `numpy`, `pandas`, `mcp`
**Use Cases**: File inspection, data reading, basic statistics, data export

### Extended Mode
**Purpose**: Full physics analysis capabilities
**Dependencies**: Core dependencies + `scipy`, `matplotlib`
**Use Cases**: Histogram fitting, kinematics calculations, correlations, plotting

### Mode Selection

Controlled via `config.yaml`:
```yaml
server:
  mode: "extended"  # or "core"
```

Runtime switching available via `switch_mode` tool without restart.

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
│   └── tools/               # Extended MCP tools
│       └── analysis.py      # Analysis tool handlers
├── common/                  # Shared utilities
│   ├── cache.py            # LRU cache implementation
│   ├── errors.py           # Error types
│   └── utils.py            # Utility functions
├── config.py               # Configuration management
└── server.py               # Mode-aware MCP server
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
  - Allowed root directory enforcement
  - Path traversal prevention
  - Protocol validation
  - Write operation validation (input ≠ output)
  - Audit logging for write operations

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

### Structure

```yaml
# Server settings
server:
  name: "root-mcp"
  version: "0.1.4"
  mode: "extended"  # "core" or "extended"

# Core configuration (always loaded)
core:
  cache:
    enabled: true
    file_cache_size: 50
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

# Extended configuration (only in extended mode)
extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
  fitting_max_iterations: 10_000

# Data resources
resources:
  - name: "my_data"
    uri: "file:///path/to/data"
    allowed_patterns: ["*.root"]

# Security
security:
  allowed_roots:
    - "/path/to/data"
  allowed_protocols: ["file", "root", "http", "https"]

# Output
output:
  export_base_path: "/path/to/exports"
  allowed_formats: ["json", "csv", "parquet"]
```

## Security Model

### Path Validation
1. **Allowed Roots**: All file paths must be under configured allowed roots
2. **Protocol Validation**: Only allowed protocols can be used
3. **Path Traversal Prevention**: `..` and symlinks validated
4. **Write Protection**: Input and output paths must differ

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
- Full RDataFrame compatibility
- C++ ROOT binding support
- Modification of existing ROOT files
- GUI/web interface

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uproot Documentation](https://uproot.readthedocs.io/)
- [awkward Documentation](https://awkward-array.org/)
- [CERN ROOT](https://root.cern/)
