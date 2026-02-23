# Configuration Guide

ROOT-MCP is configured through a YAML file that controls server behavior, mode selection, resource limits, and security constraints.

## Quick Start

You do **not** need a config file to get started. Three zero-config approaches are available:

### Option 1 — Inline data path (fastest)

Pass `--data-path` directly on the command line. The server will grant access to that directory without any YAML required:

```bash
root-mcp --data-path /path/to/your/data
```

Multiple directories are supported:

```bash
root-mcp --data-path /data/run2024 --data-path /data/simulation
```

### Option 2 — Environment variable

Set `ROOT_MCP_DATA_PATH` once (colon-separated on Linux/macOS) and start the server without arguments:

```bash
export ROOT_MCP_DATA_PATH=/path/to/your/data
root-mcp
```

### Option 3 — Generate a starter config file

Use the built-in `init` command to create a ready-to-edit `config.yaml` in the current directory:

```bash
root-mcp init                    # generates config.yaml with a placeholder URI
root-mcp init --permissive       # fills the URI with the current working directory
root-mcp init --output ~/root-mcp.yaml   # custom output path
```

Open the generated file, replace the `REPLACE_WITH_YOUR_DATA_PATH` placeholder, and run:

```bash
root-mcp --config config.yaml
```

### Permissive mode

When `security.allowed_roots` is an **empty list** (the default in the generated config), the server allows access to **any** local path. This is the recommended setting for personal or local use. Restrict it by listing explicit directories when deploying in a shared environment:

```yaml
security:
  allowed_roots: []            # permissive — any local path is accessible
  # allowed_roots:             # restrictive — only these directories
  #   - /data/physics
  #   - /home/user/exports
```

---

## Configuration File Location

Settings are merged from multiple sources in the following priority order (highest wins):

```
1. Built-in Pydantic defaults          (always lowest)
2. YAML config file                    (ROOT_MCP_CONFIG / --config / auto-discovery)
3. ROOT_MCP_* environment variables    (override anything from YAML)
4. CLI flags                           (always highest — beat both YAML and env vars)
```

Every field that can appear in `config.yaml` has a corresponding env var and CLI flag (see the [Complete Env Var & CLI Reference](#complete-env-var--cli-reference) below).  YAML users are unaffected — all new sources are strictly additive.

**Recommendation**: Use `ROOT_MCP_CONFIG` or `--config` for production, `--data-path` / `ROOT_MCP_DATA_PATH` for quick or per-session access.

## Complete Configuration Reference

### Server Settings

Controls server identity and operational mode.

```yaml
server:
  name: "root-mcp"        # Server name (shown to AI)
  version: "0.1.5"        # Version (auto-detected if omitted)
  mode: "extended"        # "core" or "extended" - see Mode Selection below
```

**Mode Selection**:
- `core`: Lightweight file operations and basic statistics
- `extended`: Full physics analysis with fitting, kinematics, correlations

See the [Mode Selection Guide](modes.md) for detailed comparison.

### Core Configuration

Settings used in both core and extended modes.

```yaml
core:
  # File caching
  cache:
    enabled: true              # Enable LRU cache for file handles
    file_cache_size: 50        # Max number of open file handles

  # Resource limits
  limits:
    max_rows_per_call: 1_000_000      # Max entries per read operation
    max_export_rows: 10_000_000       # Max entries for export operations
```

**Cache Settings**:
- Higher `file_cache_size` improves performance for repeated file access
- Lower values reduce memory usage
- Recommended: 50 for most use cases, 100+ for multi-file workflows

**Limit Settings**:
- `max_rows_per_call`: Prevents memory exhaustion from large reads
- `max_export_rows`: Limits export file sizes
- Adjust based on available memory (1M rows ≈ 100-500 MB depending on data)

### Extended Configuration

Settings used only in extended mode (ignored in core mode).

```yaml
extended:
  # Histogram settings
  histogram:
    max_bins_1d: 10_000        # Maximum bins for 1D histograms
    max_bins_2d: 1_000         # Maximum bins per dimension for 2D histograms

  # Plotting settings
  plotting:
    figure_width: 10.0         # Figure width in inches
    figure_height: 6.0         # Figure height in inches
    dpi: 100                   # Resolution
    marker_size: 4.0           # Data point marker size
    line_width: 2.0            # Line width
    grid_enabled: true         # Show grid
    default_format: "png"      # Default output format
    allowed_formats:           # Allowed export formats
      - "png"
      - "pdf"
      - "svg"

  # Fitting settings
  fitting_max_iterations: 10_000  # Max iterations for fitting algorithms
```

**Histogram Limits**:
- Prevents memory issues from excessive binning
- 1D: 10,000 bins is typically sufficient
- 2D: 1,000 × 1,000 = 1M bins (reasonable for most analyses)

**Plotting Customization**:
- Adjust `dpi` for quality vs file size tradeoff
- `default_format`: "png" for quick viewing, "pdf" for publications
- Matplotlib style settings can be customized

### Data Resources

Define data sources accessible to the server.

```yaml
resources:
  - name: "my_analysis"                    # Unique identifier
    uri: "file:///path/to/data"            # Base URI
    description: "My Physics Analysis"     # Description for AI
    allowed_patterns: ["*.root"]           # File patterns to include
    max_file_size_gb: 10                   # Max file size (optional)

  - name: "remote_data"
    uri: "root://xrootd.server.edu//path"  # XRootD URI
    description: "Remote Dataset"
    allowed_patterns: ["Run*.root"]
```

**URI Protocols**:
- `file://`: Local filesystem
- `root://`: XRootD protocol (requires `pip install "root-mcp[xrootd]"`)
- `http://`, `https://`: HTTP(S) access

**Resource Naming**:
- Use descriptive names (e.g., "cms_2015_data", "simulation_ttbar")
- Names shown to AI for context
- Must be unique within configuration

### Security Settings

Critical security constraints for file access.

```yaml
security:
  # Allowed root directories
  allowed_roots:
    - "/data/physics"
    - "/home/user/analysis"
    - "/tmp/root_mcp_exports"

  # Allowed URI protocols
  allowed_protocols:
    - "file"
    - "root"
    - "http"
    - "https"

  # Path traversal limits
  max_path_depth: 10           # Max directory depth
```

**Security Best Practices**:
1. **Restrict `allowed_roots`**: Only include necessary directories
2. **Separate read/write paths**: Different roots for input data and exports
3. **Limit protocols**: Only enable protocols you need
4. **Monitor logs**: Check for security violations

**Path Validation**:
- All file paths validated against `allowed_roots`
- Path traversal (`..`) blocked
- Symlinks validated
- Write operations require separate input/output paths

### Output Settings

Configuration for data export operations.

```yaml
output:
  export_base_path: "/tmp/root_mcp_exports"  # Base directory for exports
  allowed_formats:                            # Allowed export formats
    - "json"
    - "csv"
    - "parquet"
  max_file_size_mb: 1000                      # Max export file size (optional)
```

**Export Formats**:
- **JSON**: Human-readable, good for small datasets
- **CSV**: Compatible with spreadsheets and analysis tools
- **Parquet**: Efficient columnar format, best for large datasets

**Export Path Security**:
- Must be under `allowed_roots`
- Must differ from input file path
- All exports logged for audit trail

### Project-Local Output

To save plots and exports within your project directory (e.g., `./plots`), update your configuration:

1.  Create the directory in your project root: `mkdir -p plots`
2.  Add the directory to `security.allowed_roots`
3.  Set `output.export_base_path` to this directory

```yaml
security:
  allowed_roots:
    - "/path/to/project/data"
    - "/path/to/project/plots"  # Must be explicitly allowed

output:
  export_base_path: "/path/to/project/plots"
```

**Note**: When using tools that accept output paths, you can use relative paths (e.g., `plots/output.png`) if the server is running from the project root. However, absolute paths are recommended for configuration settings.

### Feature Flags

Enable/disable experimental features.

```yaml
features:
  enable_remote_files: true      # Allow remote file access
  enable_caching: true           # Enable result caching
  enable_streaming: true         # Enable streaming for large files
```

## Complete Example Configurations

### Example 1: Local Analysis (Extended Mode)

```yaml
# Server settings
server:
  name: "root-mcp"
  mode: "extended"

# Core configuration
core:
  cache:
    enabled: true
    file_cache_size: 50
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

# Extended configuration
extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
    default_format: "png"
  fitting_max_iterations: 10_000

# Data resources
resources:
  - name: "cms_data"
    uri: "file:///data/cms/2015"
    description: "CMS 2015 Data"
    allowed_patterns: ["*.root"]

# Security
security:
  allowed_roots:
    - "/data/cms"
    - "/home/user/exports"
  allowed_protocols: ["file"]

# Output
output:
  export_base_path: "/home/user/exports"
  allowed_formats: ["json", "csv", "parquet"]
```

### Example 2: Remote Access (Core Mode)

```yaml
# Lightweight setup for remote file inspection
server:
  name: "root-mcp"
  mode: "core"

core:
  cache:
    enabled: true
    file_cache_size: 20  # Lower cache for remote files
  limits:
    max_rows_per_call: 100_000  # Smaller reads for remote

resources:
  - name: "grid_data"
    uri: "root://xrootd.grid.org//store/data"
    description: "Grid Storage"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/tmp/root_mcp_cache"
  allowed_protocols: ["root", "file"]

output:
  export_base_path: "/tmp/root_mcp_cache"
  allowed_formats: ["json", "parquet"]
```

### Example 3: High-Performance Analysis

```yaml
# Optimized for large-scale analysis
server:
  name: "root-mcp"
  mode: "extended"

core:
  cache:
    enabled: true
    file_cache_size: 100  # Large cache for multi-file analysis
  limits:
    max_rows_per_call: 5_000_000  # Large reads for performance
    max_export_rows: 50_000_000

extended:
  histogram:
    max_bins_1d: 50_000  # Fine binning
    max_bins_2d: 2_000
  plotting:
    dpi: 300  # High resolution
    default_format: "pdf"

resources:
  - name: "simulation"
    uri: "file:///data/simulation/ttbar"
    description: "ttbar Simulation"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/data/simulation"
    - "/data/results"
  allowed_protocols: ["file"]

output:
  export_base_path: "/data/results"
  allowed_formats: ["parquet"]  # Only efficient format
```

## Environment Variables

Every `config.yaml` field now has a matching `ROOT_MCP_*` environment variable. See the [Complete Env Var & CLI Reference](#complete-env-var--cli-reference) below for the full table. A few of the most commonly used variables:

```bash
# Data directory — no config file needed
export ROOT_MCP_DATA_PATH="/path/to/your/data"

# Multiple directories (colon-separated)
export ROOT_MCP_DATA_PATH="/data/run2024:/data/simulation"

# Configuration file location
export ROOT_MCP_CONFIG="/path/to/config.yaml"

# Override mode
export ROOT_MCP_MODE="core"

# Enable native ROOT
export ROOT_MCP_ENABLE_ROOT="1"

# Override log level
export ROOT_MCP_LOG_LEVEL="DEBUG"
```

---

## Complete Env Var & CLI Reference

Every field is configurable from three sources (later wins): YAML → env var → CLI flag.

### Already Shipped

| Config field | Env var | CLI flag |
|---|---|---|
| `resources[].uri` (local paths) | `ROOT_MCP_DATA_PATH` (colon-sep) | `--data-path DIR` (append) |
| `features.enable_root` | `ROOT_MCP_ENABLE_ROOT` | `--enable-root` |

### Server & Mode

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `server.mode` | `ROOT_MCP_MODE` | `--mode core\|extended` | str | `extended` |
| `server.name` | `ROOT_MCP_SERVER_NAME` | `--server-name NAME` | str | `root-mcp` |

### Security

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `security.allowed_roots` | `ROOT_MCP_ALLOWED_ROOTS` (`:` sep) | `--allowed-root DIR` (append) | list[str] | `[]` |
| `security.allow_remote` | `ROOT_MCP_ALLOW_REMOTE` (`1`/`true`/`yes`) | `--allow-remote` / `--no-allow-remote` | bool | `false` |
| `security.allowed_protocols` | `ROOT_MCP_ALLOWED_PROTOCOLS` (`,` sep) | `--allowed-protocols p1,p2` | list[str] | `["file"]` |
| `security.max_path_depth` | `ROOT_MCP_MAX_PATH_DEPTH` | `--max-path-depth N` | int | `10` |

### Output / Export

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `output.export_base_path` | `ROOT_MCP_EXPORT_PATH` | `--export-path DIR` | str | `/tmp/root_mcp_output` |
| `output.allowed_formats` | `ROOT_MCP_EXPORT_FORMATS` (`,` sep) | `--export-formats json,csv` | list[str] | `["json","csv","parquet"]` |
| `features.enable_export` | `ROOT_MCP_ENABLE_EXPORT` (`0`/`false`/`no`) | `--no-export` | bool | `true` |

### Core Limits & Cache

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `core.limits.max_rows_per_call` | `ROOT_MCP_MAX_ROWS` | `--max-rows N` | int | `1_000_000` |
| `core.limits.max_export_rows` | `ROOT_MCP_MAX_EXPORT_ROWS` | `--max-export-rows N` | int | `10_000_000` |
| `core.cache.enabled` | `ROOT_MCP_CACHE` (`0`/`false`/`no`) | `--no-cache` | bool | `true` |
| `core.cache.file_cache_size` | `ROOT_MCP_CACHE_SIZE` | `--cache-size N` | int | `50` |

### Extended Analysis

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `extended.histogram.max_bins_1d` | `ROOT_MCP_MAX_BINS_1D` | `--max-bins-1d N` | int | `10_000` |
| `extended.histogram.max_bins_2d` | `ROOT_MCP_MAX_BINS_2D` | `--max-bins-2d N` | int | `1_000` |
| `extended.fitting_max_iterations` | `ROOT_MCP_FITTING_ITERATIONS` | `--fitting-iterations N` | int | `10_000` |
| `extended.plotting.dpi` | `ROOT_MCP_PLOT_DPI` | `--plot-dpi N` | int | `100` |
| `extended.plotting.default_format` | `ROOT_MCP_PLOT_FORMAT` | `--plot-format png\|pdf\|svg` | str | `png` |
| `extended.plotting.figure_width` | `ROOT_MCP_PLOT_WIDTH` | `--plot-width N` | float | `10.0` |
| `extended.plotting.figure_height` | `ROOT_MCP_PLOT_HEIGHT` | `--plot-height N` | float | `6.0` |

### Native ROOT Execution

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `root_native.execution_timeout` | `ROOT_MCP_ROOT_TIMEOUT` | `--root-timeout N` | int (s) | `60` |
| `root_native.working_directory` | `ROOT_MCP_ROOT_WORKDIR` | `--root-workdir DIR` | str | `/tmp/root_mcp_native` |
| `root_native.max_output_size` | `ROOT_MCP_ROOT_MAX_OUTPUT` | `--root-max-output N` | int (B) | `10_000_000` |
| `root_native.max_code_length` | `ROOT_MCP_ROOT_MAX_CODE` | `--root-max-code N` | int (chars) | `100_000` |

### Remote Resources

| Mechanism | Syntax | Example |
|---|---|---|
| CLI | `--resource NAME=URI[\|DESCRIPTION]` (append) | `--resource cms=root://xrootd.cern.ch//store` |
| Env var | `ROOT_MCP_RESOURCES` — semicolon-sep list of `NAME=URI[\|DESC]` | `ROOT_MCP_RESOURCES="cms=root://…;local=file:///data"` |

Notes:
- Use `|` (pipe) to separate description from URI — colons are ambiguous inside URIs.
- YAML-declared resources take precedence: a spec whose URI already exists is silently skipped.
- Both sources are **additive**: env var resources plus CLI resources are both added.

### Log Level

| Mechanism | Env var | CLI flag | Notes |
|---|---|---|---|
| Log level | `ROOT_MCP_LOG_LEVEL` | `--log-level DEBUG\|INFO\|WARNING\|ERROR` | Applied before config loading |

## Configuration Validation

The server validates configuration on startup:

**Common Errors**:
- Invalid mode (must be "core" or "extended")
- Invalid URI format in resources
- Export path not in `allowed_roots` (add the path or set `allowed_roots: []` for permissive mode)

**Validation Messages**:
```
✓ Configuration loaded successfully
✓ Mode: extended
✓ Resources: 2 configured
✓ Security: 3 allowed roots
```

## Dynamic Configuration

Some settings can be changed at runtime:

**Mode Switching**:
```json
{
  "tool": "switch_mode",
  "arguments": {"mode": "core"}
}
```

**Cache Management**:
- Cache automatically managed by LRU policy
- Manual cache clear not currently supported

## Performance Tuning

### For Small Files (<1 GB)
```yaml
core:
  cache:
    file_cache_size: 20
  limits:
    max_rows_per_call: 1_000_000
```

### For Large Files (>10 GB)
```yaml
core:
  cache:
    file_cache_size: 5  # Fewer handles for large files
  limits:
    max_rows_per_call: 100_000  # Smaller chunks
```

### For Multi-File Analysis
```yaml
core:
  cache:
    file_cache_size: 100  # Cache many files
  limits:
    max_rows_per_call: 500_000
```

### For Remote Files
```yaml
core:
  cache:
    file_cache_size: 10  # Limited caching
  limits:
    max_rows_per_call: 50_000  # Small reads
```

## Troubleshooting

### Configuration Not Found
**Error**: `Failed to load configuration`
**Solution**: Check `ROOT_MCP_CONFIG` environment variable or place `config.yaml` in current directory

### Security Violation
**Error**: `SecurityError: Path not in allowed roots`
**Solution**: Add path to `security.allowed_roots`

### Mode Not Available
**Error**: `Failed to switch to extended mode`
**Solution**: Ensure scipy and matplotlib are installed

### Resource Limits Exceeded
**Error**: `Max rows per call exceeded`
**Solution**: Increase `core.limits.max_rows_per_call` or read in chunks

## Best Practices

1. **Start Conservative**: Begin with default limits, increase as needed
2. **Separate Environments**: Different configs for development/production
3. **Security First**: Minimal `allowed_roots`, only necessary protocols
4. **Monitor Resources**: Watch memory usage, adjust cache size
5. **Use Mode Switching**: Start in core, switch to extended when needed
6. **Document Changes**: Comment your config file with reasoning

## See Also

- [Mode Selection Guide](modes.md): Detailed mode comparison
- [Architecture](../ARCHITECTURE.md): System design details
- [Tool Reference](../api/tools.md): Available tools per mode
