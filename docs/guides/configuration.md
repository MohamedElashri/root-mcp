# Configuration Guide

ROOT-MCP is configured through a YAML file that controls server behavior, mode selection, resource limits, and security constraints.

## Configuration File Location

The server looks for configuration in the following order:
1. Path specified in `ROOT_MCP_CONFIG` environment variable
2. `./config.yaml` (current directory)
3. `~/.config/root-mcp/config.yaml` (user config directory)

**Recommendation**: Use environment variable for production, local file for development.

## Complete Configuration Reference

### Server Settings

Controls server identity and operational mode.

```yaml
server:
  name: "root-mcp"        # Server name (shown to AI)
  version: "0.1.3"        # Version (auto-detected if omitted)
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

Override configuration with environment variables:

```bash
# Configuration file location
export ROOT_MCP_CONFIG="/path/to/config.yaml"

# Override mode
export ROOT_MCP_MODE="core"

# Override log level
export ROOT_MCP_LOG_LEVEL="DEBUG"
```

## Configuration Validation

The server validates configuration on startup:

**Common Errors**:
- Invalid mode (must be "core" or "extended")
- Missing `allowed_roots` in security section
- Invalid URI format in resources
- Export path not in `allowed_roots`

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
